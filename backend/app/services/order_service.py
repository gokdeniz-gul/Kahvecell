"""Sipariş yönetimi — case 3.4, 7.2, 7.3 ve 13.2.

Durum makinesi (state machine):

    PENDING ──► ACCEPTED ──► PREPARING ──► READY ──► COMPLETED
       │            │                                  ▲
       └──► CANCELLED ◄┘                    sadece QR okutularak

  • Dükkân sahibi: kabul eder, hazırlar, hazır der; teslimi QR okutarak yapar.
  • Müşteri: sadece henüz kabul edilmemiş (PENDING) siparişini iptal edebilir.
  • İptal edilen siparişin kahve hakkı iade edilir.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core import qr
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.models import Order, OrderItem, User
from app.models.enums import OrderStatus, SubscriptionStatus, UserRole
from app.repositories.order_repository import OrderRepository
from app.repositories.shop_repository import ShopRepository
from app.schemas.order import (
    CreateOrderRequest,
    OrderItemResponse,
    OrderListResponse,
    OrderResponse,
    OrderShopInfo,
    QrCodeResponse,
    VerifyQrResponse,
)
from app.services.shop_service import ISTANBUL_TZ, is_open_at
from app.services.sms_service import mask_phone
from app.services.subscription_service import SubscriptionService

# Dükkânın yapabileceği geçişler. COMPLETED'a geçiş ayrıca QR doğrulaması ister.
SHOP_TRANSITIONS: dict[OrderStatus, tuple[OrderStatus, ...]] = {
    OrderStatus.PENDING: (OrderStatus.ACCEPTED, OrderStatus.CANCELLED),
    OrderStatus.ACCEPTED: (OrderStatus.PREPARING, OrderStatus.CANCELLED),
    OrderStatus.PREPARING: (OrderStatus.READY,),
    OrderStatus.READY: (OrderStatus.COMPLETED,),
    OrderStatus.COMPLETED: (),
    OrderStatus.CANCELLED: (),
}
CUSTOMER_TRANSITIONS: dict[OrderStatus, tuple[OrderStatus, ...]] = {
    OrderStatus.PENDING: (OrderStatus.CANCELLED,),
}
ACTIVE_ORDER_STATUSES = [
    OrderStatus.PENDING,
    OrderStatus.ACCEPTED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
]
# Abonelik bu durumlardayken sipariş verilebilir (iptal edilen, dönem sonuna kadar geçerli).
ORDERABLE_SUBSCRIPTION_STATUSES = (SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED)


class OrderService:
    def __init__(self, db: Session, clock: Callable[[], datetime] | None = None) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.shops = ShopRepository(db)
        self.subscriptions = SubscriptionService(db)
        self.clock = clock or (lambda: datetime.now(UTC))

    # ---------- Sipariş verme ----------

    def create(self, user: User, request: CreateOrderRequest) -> OrderResponse:
        now = self.clock()

        # 1) Dükkân ve ürün geçerli mi? (Hak düşmeden önce kontrol ediyoruz.)
        shop = self.shops.get_active(request.shop_id)
        if shop is None:
            raise NotFoundError("Dükkân bulunamadı.", code="SHOP_NOT_FOUND")
        if not is_open_at(shop.opens_at, shop.closes_at, now.astimezone(ISTANBUL_TZ).time()):
            raise ConflictError(
                f"{shop.name} şu an kapalı. Çalışma saatleri: "
                f"{shop.opens_at:%H:%M}–{shop.closes_at:%H:%M}.",
                code="SHOP_CLOSED",
            )
        product = self.orders.get_product_in_shop(shop.id, request.product_id)
        if product is None:
            raise NotFoundError("Ürün bu dükkânın menüsünde yok.", code="PRODUCT_NOT_FOUND")
        if not product.is_available:
            raise ConflictError(f"{product.name} şu an satışta değil.", code="PRODUCT_UNAVAILABLE")

        # 2) Aktif abonelik ve kahve hakkı var mı?
        subscription = self.subscriptions.get_current(user)
        if subscription is None or subscription.status not in ORDERABLE_SUBSCRIPTION_STATUSES:
            raise ForbiddenError(
                "Sipariş verebilmek için aktif bir aboneliğiniz olmalı. "
                "Paketleri GET /subscriptions/plans ile inceleyebilirsiniz.",
                code="NO_ACTIVE_SUBSCRIPTION",
            )

        # 3) Hakkı düş (Unlimited'da düşmez).
        credits_used = 0
        if subscription.remaining_credits is not None:
            if not self.orders.consume_credit(subscription.id):
                raise ForbiddenError(
                    f"Bu ayki kahve hakkınız bitti. {subscription.expires_at:%d.%m.%Y} tarihinde "
                    "yenilenecek; beklemek istemezseniz paketinizi yükseltebilirsiniz.",
                    code="NO_CREDITS_LEFT",
                    details={"renews_at": subscription.expires_at.isoformat()},
                )
            self.db.refresh(subscription)
            credits_used = 1

        # 4) Siparişi oluştur ve QR'ı imzala.
        order = self.orders.add(
            Order(
                user=user,
                shop=shop,
                subscription=subscription,
                status=OrderStatus.PENDING,
                credits_used=credits_used,
                note=request.note,
                created_at=now,
                updated_at=now,
                items=[
                    OrderItem(
                        product=product,
                        size=request.size,
                        sugar=request.sugar,
                        milk=request.milk,
                        extra_shots=request.extra_shots,
                        unit_price_kurus=product.price_kurus,  # fiyatın o anki kopyası
                    )
                ],
            )
        )
        order.qr_signature = self._qr_payload(order)["signature"]
        self.db.commit()
        return self._to_response(order, viewer=user)

    def reorder(self, user: User, order_id: str) -> OrderResponse:
        """Favori sipariş tekrarı: geçmişteki bir siparişi aynı özelleştirmelerle yeniden ver."""
        previous = self._get_visible(user, order_id)
        if previous.user_id != user.id:
            raise NotFoundError("Sipariş bulunamadı.", code="ORDER_NOT_FOUND")
        item = previous.items[0]
        return self.create(
            user,
            CreateOrderRequest(
                shop_id=previous.shop_id,
                product_id=item.product_id,
                size=item.size,
                sugar=item.sugar,
                milk=item.milk,
                extra_shots=item.extra_shots,
                note=previous.note,
            ),
        )

    # ---------- Takip ----------

    def get(self, user: User, order_id: str) -> OrderResponse:
        return self._to_response(self._get_visible(user, order_id), viewer=user)

    def history(self, user: User, *, offset: int, limit: int) -> OrderListResponse:
        orders, total = self.orders.list_for_user(user.id, offset=offset, limit=limit)
        return OrderListResponse(
            items=[self._to_response(o, viewer=user) for o in orders],
            total=total,
            offset=offset,
            limit=limit,
        )

    def incoming(
        self,
        user: User,
        *,
        shop_id: str | None,
        statuses: list[OrderStatus] | None,
        offset: int,
        limit: int,
    ) -> OrderListResponse:
        """Dükkân paneli: sahibi olduğum dükkânlara gelen siparişler (öncelikliler önce)."""
        is_admin = user.role == UserRole.ADMIN
        shop_ids = None if is_admin else self.orders.shop_ids_owned_by(user.id)  # None = hepsi
        if shop_id is not None:
            if not is_admin and shop_id not in shop_ids:
                raise ForbiddenError("Bu dükkânın sahibi değilsiniz.", code="NOT_SHOP_OWNER")
            shop_ids = [shop_id]
        orders, total = self.orders.list_for_shops(
            shop_ids, statuses or ACTIVE_ORDER_STATUSES, offset=offset, limit=limit
        )
        return OrderListResponse(
            items=[self._to_response(o, viewer=user) for o in orders],
            total=total,
            offset=offset,
            limit=limit,
        )

    # ---------- Durum güncelleme ----------

    def update_status(
        self, user: User, order_id: str, new_status: OrderStatus, qr_content: str | None
    ) -> OrderResponse:
        order = self._get_visible(user, order_id)
        is_staff = self._is_shop_staff(user, order)
        allowed = (SHOP_TRANSITIONS if is_staff else CUSTOMER_TRANSITIONS).get(order.status, ())

        if new_status not in allowed:
            raise ConflictError(
                f"Sipariş {order.status} durumundan {new_status} durumuna geçemez.",
                code="INVALID_STATUS_TRANSITION",
                details={"current_status": order.status, "allowed": list(allowed)},
            )

        if new_status == OrderStatus.COMPLETED:
            # Teslim ancak müşterinin QR'ı okutulursa yapılır (case 7.3).
            if not qr_content:
                raise BadRequestError(
                    "Teslim için müşterinin QR kodunu okutun (qr_content).", code="QR_REQUIRED"
                )
            scanned = self._verify_qr_content(user, qr_content)
            if scanned.id != order.id:
                raise BadRequestError("Okutulan QR bu siparişe ait değil.", code="QR_ORDER_MISMATCH")

        now = self.clock()
        order.status = new_status
        order.updated_at = now
        if new_status == OrderStatus.COMPLETED:
            order.completed_at = now
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = now
            if order.credits_used:
                self.orders.refund_credit(order.subscription_id)  # hakkı iade et
        self.db.commit()
        return self._to_response(order, viewer=user)

    # ---------- QR doğrulama ----------

    def verify_qr(self, user: User, qr_content: str) -> VerifyQrResponse:
        order = self._verify_qr_content(user, qr_content)
        if order.status == OrderStatus.COMPLETED:
            raise ConflictError("Bu QR ile sipariş zaten teslim edilmiş.", code="QR_ALREADY_USED")
        if order.status == OrderStatus.CANCELLED:
            raise ConflictError("Bu sipariş iptal edilmiş.", code="ORDER_CANCELLED")

        can_complete = order.status == OrderStatus.READY
        return VerifyQrResponse(
            valid=True,
            message="QR kod gerçek ve bu dükkâna ait."
            + ("" if can_complete else f" Sipariş henüz hazır değil (durum: {order.status})."),
            can_complete=can_complete,
            order=self._to_response(order, viewer=user),
        )

    def _verify_qr_content(self, user: User, qr_content: str) -> Order:
        try:
            payload = json.loads(qr_content)
        except (json.JSONDecodeError, TypeError):
            raise BadRequestError("QR içeriği okunamadı.", code="QR_INVALID_FORMAT") from None
        if not isinstance(payload, dict):
            raise BadRequestError("QR içeriği okunamadı.", code="QR_INVALID_FORMAT")

        if not qr.is_signature_valid(payload):
            raise BadRequestError(
                "QR kod sahte veya değiştirilmiş! İmza doğrulanamadı.", code="QR_SIGNATURE_INVALID"
            )

        order = self.orders.get(payload["order_id"])
        # İmza doğru olsa bile bilgiler veritabanıyla birebir tutmalı.
        if order is None or self._qr_payload(order) != payload:
            raise BadRequestError("QR kod bu sistemdeki bir siparişle eşleşmiyor.", code="QR_SIGNATURE_INVALID")
        if not self._is_shop_staff(user, order):
            raise ForbiddenError("Bu sipariş başka bir dükkâna ait.", code="QR_WRONG_SHOP")
        return order

    # ---------- Yardımcılar ----------

    def _get_visible(self, user: User, order_id: str) -> Order:
        """Siparişi sadece sahibi, dükkânın sahibi ve admin görebilir.
        Başkasınınsa "yok" diyoruz (403 deseydik siparişin var olduğunu sızdırmış olurduk)."""
        order = self.orders.get(order_id)
        if order is None or not (order.user_id == user.id or self._is_shop_staff(user, order)):
            raise NotFoundError("Sipariş bulunamadı.", code="ORDER_NOT_FOUND")
        return order

    @staticmethod
    def _is_shop_staff(user: User, order: Order) -> bool:
        return user.role == UserRole.ADMIN or (
            user.role == UserRole.SHOP_OWNER and order.shop.owner_id == user.id
        )

    @staticmethod
    def _qr_payload(order: Order) -> dict[str, str]:
        return qr.build_payload(order.id, order.user_id, order.shop_id, order.created_at)

    def _to_response(self, order: Order, *, viewer: User) -> OrderResponse:
        is_staff = self._is_shop_staff(viewer, order)
        allowed = (SHOP_TRANSITIONS if is_staff else CUSTOMER_TRANSITIONS).get(order.status, ())

        qr_code = None
        if order.user_id == viewer.id and order.status in ACTIVE_ORDER_STATUSES:
            payload = self._qr_payload(order)
            content = qr.to_content(payload)
            qr_code = QrCodeResponse(
                payload=payload, content=content, image_data_url=qr.to_image_data_url(content)
            )

        customer = order.user
        return OrderResponse(
            id=order.id,
            status=order.status,
            shop=OrderShopInfo(id=order.shop.id, name=order.shop.name, address=order.shop.address),
            customer_name=customer.full_name or mask_phone(customer.phone_number),
            items=[
                OrderItemResponse(
                    product_id=item.product_id,
                    product_name=item.product.name,
                    size=item.size,
                    sugar=item.sugar,
                    milk=item.milk,
                    extra_shots=item.extra_shots,
                    unit_price_kurus=item.unit_price_kurus,
                )
                for item in order.items
            ],
            credits_used=order.credits_used,
            is_priority=order.subscription.plan.has_priority,
            note=order.note,
            allowed_next_statuses=list(allowed),
            created_at=order.created_at,
            updated_at=order.updated_at,
            completed_at=order.completed_at,
            cancelled_at=order.cancelled_at,
            qr=qr_code,
        )
