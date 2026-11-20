"""Abonelik iş kuralları — case 3.2.

Kurallar (sunumda savunulacak kararlar):
  • Başlatma: önce ödeme (POST /payments/process), sonra o ödemenin transaction_id'si ile aktivasyon.
  • Yükseltme: HEMEN geçerli. Fiyat farkı ödenir, kahve/misafir hakkı farkı mevcut hakka eklenir.
  • Düşürme: BİR SONRAKİ dönem geçerli (bu ayın parası ödendi, hak geri alınmaz). Ücretsiz.
  • İptal: dönem sonuna kadar haklar kullanılabilir, sonra yenilenmez.
  • Aylık yenileme: dönem bitince (sorgulandığı anda) haklar sıfırlanıp yeniden doldurulur,
    bekleyen düşürme uygulanır ve simülasyonda kayıtlı karttan otomatik ödeme alınır.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Payment, Plan, Subscription, User
from app.models.enums import PaymentStatus, PlanType, SubscriptionStatus
from app.repositories.payment_repository import PaymentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.payment_gateway import new_transaction_id


class SubscriptionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.plans = PlanRepository(db)
        self.subscriptions = SubscriptionRepository(db)
        self.payments = PaymentRepository(db)

    # ---------- Okuma ----------

    def list_plans(self) -> list[Plan]:
        return list(self.plans.list_active())

    def get_plan(self, plan_type: PlanType) -> Plan:
        plan = self.plans.get_active_by_type(plan_type)
        if plan is None:
            raise NotFoundError("Paket bulunamadı.", code="PLAN_NOT_FOUND")
        return plan

    def get_current(self, user: User) -> Subscription | None:
        """Kullanıcının geçerli aboneliği. Dönemi bittiyse önce yenileme/sonlandırma yapılır."""
        subscription = self.subscriptions.get_current_for_user(user.id)
        if subscription is None:
            return None

        now = datetime.now(UTC)
        if subscription.expires_at <= now:
            self._roll_over(subscription, now)
            self.db.commit()
        return subscription if subscription.status != SubscriptionStatus.EXPIRED else None

    def _require_changeable(self, user: User) -> Subscription:
        subscription = self.get_current(user)
        if subscription is None:
            raise NotFoundError("Aktif aboneliğiniz yok.", code="NO_ACTIVE_SUBSCRIPTION")
        if subscription.status == SubscriptionStatus.CANCELLED:
            raise ConflictError(
                "İptal edilmiş abonelik değiştirilemez; dönem sonuna kadar kullanabilirsiniz.",
                code="SUBSCRIPTION_CANCELLED",
            )
        return subscription

    # ---------- Fiyat: ödeme ekranında ne kadar çekilecek? ----------

    def amount_due(self, user: User, plan: Plan) -> int:
        """Bu kullanıcının bu pakete geçmek için ödemesi gereken tutar (kuruş)."""
        current = self.get_current(user)
        if current is None:
            return plan.monthly_price_kurus  # yeni abonelik: tam fiyat

        if current.status == SubscriptionStatus.CANCELLED:
            raise ConflictError(
                "İptal edilmiş aboneliğiniz dönem sonuna kadar geçerli. "
                "Dönem bitince yeni paket alabilirsiniz.",
                code="SUBSCRIPTION_CANCELLED",
            )
        if plan.id == current.plan_id:
            raise BadRequestError("Zaten bu pakettesiniz.", code="ALREADY_ON_PLAN")
        if plan.monthly_price_kurus <= current.plan.monthly_price_kurus:
            raise BadRequestError(
                "Paket düşürme ücretsizdir; ödeme yapmadan PATCH /subscriptions/me kullanın.",
                code="DOWNGRADE_NEEDS_NO_PAYMENT",
            )
        return plan.monthly_price_kurus - current.plan.monthly_price_kurus  # yükseltme: fark

    # ---------- Başlatma ----------

    def start(self, user: User, plan_type: PlanType, transaction_id: str) -> Subscription:
        plan = self.get_plan(plan_type)
        current = self.get_current(user)
        if current is not None:
            raise ConflictError(
                f"Zaten bir aboneliğiniz var ({current.plan.name}, "
                f"{current.expires_at:%d.%m.%Y} tarihine kadar geçerli). "
                "Paket değiştirmek için PATCH /subscriptions/me kullanın.",
                code="SUBSCRIPTION_EXISTS",
            )

        payment = self._claim_payment(user, transaction_id, plan, plan.monthly_price_kurus)
        now = datetime.now(UTC)
        subscription = self.subscriptions.add(
            Subscription(
                user=user,
                plan=plan,
                status=SubscriptionStatus.ACTIVE,
                remaining_credits=plan.monthly_credits,
                remaining_guest_passes=plan.guest_passes,
                started_at=now,
                expires_at=now + timedelta(days=settings.subscription_period_days),
            )
        )
        payment.subscription = subscription  # Transaction ID ↔ abonelik eşleşmesi (case 12.2)
        self.db.commit()
        return subscription

    # ---------- Yükseltme / düşürme ----------

    def change_plan(
        self, user: User, plan_type: PlanType, transaction_id: str | None
    ) -> Subscription:
        subscription = self._require_changeable(user)
        target = self.get_plan(plan_type)
        current_plan = subscription.plan

        if target.id == current_plan.id:
            if subscription.pending_plan_id is None:
                raise BadRequestError("Zaten bu pakettesiniz.", code="ALREADY_ON_PLAN")
            # Mevcut pakete "geri dönmek" = bekleyen düşürmeyi iptal etmek.
            subscription.pending_plan = None
            self.db.commit()
            return subscription

        if target.monthly_price_kurus > current_plan.monthly_price_kurus:
            self._upgrade(user, subscription, target, transaction_id)
        else:
            if transaction_id is not None:
                raise BadRequestError(
                    "Paket düşürme ücretsizdir; transaction_id göndermeyin.",
                    code="DOWNGRADE_NEEDS_NO_PAYMENT",
                )
            subscription.pending_plan = target  # bir sonraki dönem uygulanacak

        self.db.commit()
        return subscription

    def _upgrade(
        self, user: User, subscription: Subscription, target: Plan, transaction_id: str | None
    ) -> None:
        current_plan = subscription.plan
        difference = target.monthly_price_kurus - current_plan.monthly_price_kurus
        if transaction_id is None:
            raise BadRequestError(
                "Yükseltme için fark ödemesi gerekli. Önce POST /payments/process ile ödeyin.",
                code="PAYMENT_REQUIRED_FOR_UPGRADE",
                details={"amount_kurus": difference},
            )
        payment = self._claim_payment(user, transaction_id, target, difference)

        # Kullanılan hak korunur, aradaki fark eklenir. Örn: Starter'da 3 kahve içtiyse (7 kaldı)
        # Premium'a geçince 7 + (20 - 10) = 17 hakkı olur.
        if target.monthly_credits is None or subscription.remaining_credits is None:
            subscription.remaining_credits = target.monthly_credits
        else:
            subscription.remaining_credits += target.monthly_credits - (current_plan.monthly_credits or 0)
        subscription.remaining_guest_passes += max(0, target.guest_passes - current_plan.guest_passes)

        subscription.plan = target
        subscription.pending_plan = None
        payment.subscription = subscription

    # ---------- İptal ----------

    def cancel(self, user: User) -> Subscription:
        subscription = self.get_current(user)
        if subscription is None:
            raise NotFoundError("Aktif aboneliğiniz yok.", code="NO_ACTIVE_SUBSCRIPTION")
        if subscription.status == SubscriptionStatus.CANCELLED:
            raise ConflictError("Abonelik zaten iptal edilmiş.", code="ALREADY_CANCELLED")

        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.now(UTC)
        subscription.pending_plan = None
        self.db.commit()
        return subscription

    # ---------- Yardımcılar ----------

    def _claim_payment(
        self, user: User, transaction_id: str, plan: Plan, expected_amount: int
    ) -> Payment:
        """Ödemenin bu kullanıcıya ait, başarılı, kullanılmamış ve bu işlem için olduğunu doğrular."""
        payment = self.payments.get_by_transaction_id(transaction_id)
        if payment is None or payment.user_id != user.id:
            raise NotFoundError("Ödeme bulunamadı.", code="PAYMENT_NOT_FOUND")
        if payment.status != PaymentStatus.SUCCESS:
            raise BadRequestError("Bu ödeme başarısız olmuş.", code="PAYMENT_NOT_SUCCESSFUL")
        if payment.subscription_id is not None:
            raise ConflictError("Bu ödeme zaten kullanılmış.", code="PAYMENT_ALREADY_USED")
        if payment.plan_id != plan.id or payment.amount_kurus != expected_amount:
            raise BadRequestError(
                "Ödeme bu işlemle eşleşmiyor (paket ya da tutar farklı).",
                code="PAYMENT_MISMATCH",
                details={"expected_amount_kurus": expected_amount},
            )
        return payment

    def _roll_over(self, subscription: Subscription, now: datetime) -> None:
        """Dönem bitti: iptal edildiyse sonlandır, değilse yeni dönemi başlat (aylık yenileme)."""
        while subscription.expires_at <= now:
            if subscription.status == SubscriptionStatus.CANCELLED:
                subscription.status = SubscriptionStatus.EXPIRED
                return

            if subscription.pending_plan is not None:
                subscription.plan = subscription.pending_plan
                subscription.pending_plan = None
            plan = subscription.plan

            # Simülasyon: kayıtlı karttan otomatik çekim her zaman başarılı.
            last_payment = self.payments.get_last_successful(subscription.user_id)
            self.payments.add(
                Payment(
                    user_id=subscription.user_id,
                    plan=plan,
                    subscription=subscription,
                    transaction_id=new_transaction_id(),
                    status=PaymentStatus.SUCCESS,
                    amount_kurus=plan.monthly_price_kurus,
                    card_last4=last_payment.card_last4 if last_payment else "0000",
                )
            )

            subscription.started_at = subscription.expires_at
            subscription.expires_at += timedelta(days=settings.subscription_period_days)
            subscription.remaining_credits = plan.monthly_credits
            subscription.remaining_guest_passes = plan.guest_passes
