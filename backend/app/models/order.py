from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import CupSize, MilkType, OrderStatus, SugarLevel

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.shop import Shop
    from app.models.subscription import Subscription
    from app.models.user import User


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Siparişin "fişi": kim, hangi dükkândan, hangi abonelikle, hangi durumda."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("credits_used >= 0", name="ck_orders_credits_non_negative"),
        # Dükkân paneli: "bekleyen siparişlerim" → shop_id + status
        Index("ix_orders_shop_status", "shop_id", "status"),
        # Müşteri: "sipariş geçmişim (yeniden eskiye)" → user_id + created_at
        Index("ix_orders_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id", ondelete="RESTRICT"))
    # Hak hangi abonelikten düşüldü? İade/iptalde hakkı doğru yere geri vermek için gerekli.
    subscription_id: Mapped[str] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="RESTRICT"), index=True
    )

    status: Mapped[OrderStatus] = mapped_column(
        enum_column(OrderStatus), default=OrderStatus.PENDING
    )
    credits_used: Mapped[int] = mapped_column(default=0)
    # QR kodun HMAC-SHA256 imzası; teslimde dükkân bu imzayı doğrular.
    qr_signature: Mapped[str | None]
    note: Mapped[str | None]

    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    user: Mapped["User"] = relationship(back_populates="orders")
    shop: Mapped["Shop"] = relationship(back_populates="orders")
    subscription: Mapped["Subscription"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(UUIDPrimaryKeyMixin, Base):
    """Siparişteki tek bir kahve ve özelleştirmeleri (boy, şeker, süt, ek shot)."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("extra_shots BETWEEN 0 AND 3", name="ck_order_items_extra_shots_range"),
        CheckConstraint("unit_price_kurus >= 0", name="ck_order_items_price_non_negative"),
    )

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    # RESTRICT: geçmiş siparişlerde kullanılmış bir ürün silinemez (menüden "kaldırılabilir" ama).
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))

    quantity: Mapped[int] = mapped_column(default=1)
    size: Mapped[CupSize] = mapped_column(enum_column(CupSize), default=CupSize.M)
    sugar: Mapped[SugarLevel] = mapped_column(enum_column(SugarLevel), default=SugarLevel.NONE)
    milk: Mapped[MilkType] = mapped_column(enum_column(MilkType), default=MilkType.NONE)
    extra_shots: Mapped[int] = mapped_column(default=0)

    # Sipariş anındaki fiyatın kopyası: ürünün fiyatı sonradan değişse de eski fiş değişmez.
    unit_price_kurus: Mapped[int]

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
