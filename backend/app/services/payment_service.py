"""Ödeme işlemleri — case bölüm 12.

Her deneme (başarılı ya da başarısız) ödeme geçmişine kaydedilir.
Tutarı kullanıcı göndermez, sunucu hesaplar: yeni abonelikte tam fiyat, yükseltmede fark.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import PaymentRequiredError
from app.models import Payment, User
from app.models.enums import PaymentStatus, PlanType
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import CardDetails, PaymentListResponse, PaymentResponse
from app.services.payment_gateway import MockPaymentGateway
from app.services.subscription_service import SubscriptionService


class PaymentService:
    def __init__(self, db: Session, gateway: MockPaymentGateway | None = None) -> None:
        self.db = db
        self.payments = PaymentRepository(db)
        self.subscription_service = SubscriptionService(db)
        self.gateway = gateway or MockPaymentGateway()

    def process(self, user: User, plan_type: PlanType, card: CardDetails) -> PaymentResponse:
        plan = self.subscription_service.get_plan(plan_type)
        amount = self.subscription_service.amount_due(user, plan)

        result = self.gateway.charge(card.card_number, amount)
        payment = self.payments.add(
            Payment(
                user=user,
                plan=plan,
                transaction_id=result.transaction_id,
                status=PaymentStatus.SUCCESS if result.approved else PaymentStatus.FAILED,
                amount_kurus=amount,
                card_last4=card.card_number[-4:],
                failure_reason=result.failure_reason,
            )
        )
        self.db.commit()  # başarısız deneme de geçmişte kalsın diye hatadan ÖNCE kaydediyoruz

        response = PaymentResponse.from_payment(payment)
        if not result.approved:
            raise PaymentRequiredError(
                "Ödeme reddedildi. Lütfen başka bir kart deneyin.",
                code="PAYMENT_DECLINED",
                details=response.model_dump(mode="json"),
            )
        return response

    def history(self, user: User, *, offset: int, limit: int) -> PaymentListResponse:
        payments, total = self.payments.list_for_user(user.id, offset=offset, limit=limit)
        return PaymentListResponse(
            items=[PaymentResponse.from_payment(payment) for payment in payments],
            total=total,
            offset=offset,
            limit=limit,
        )
