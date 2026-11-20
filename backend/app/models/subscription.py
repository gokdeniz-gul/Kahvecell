from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import SubscriptionStatus

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.payment import Payment
    from app.models.plan import Plan
    from app.models.user import User


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "remaining_credits IS NULL OR remaining_credits >= 0",
            name="ck_subscriptions_credits_non_negative",
        ),
        CheckConstraint(
            "remaining_guest_passes >= 0", name="ck_subscriptions_guest_passes_non_negative"
        ),
        # "Bu kullanıcının aktif aboneliği hangisi?" sorgusu sık çalışacak.
        Index("ix_subscriptions_user_status", "user_id", "status"),
        # Bir kullanıcının aynı anda yalnızca BİR geçerli aboneliği olabilir (veritabanı garantisi).
        # İptal edilen abonelik dönem sonuna kadar geçerli olduğu için CANCELLED da sayılır.
        Index(
            "uq_subscriptions_one_current_per_user",
            "user_id",
            unique=True,
            sqlite_where=text("status IN ('ACTIVE', 'PAUSED', 'CANCELLED')"),
            postgresql_where=text("status IN ('ACTIVE', 'PAUSED', 'CANCELLED')"),
        ),
    )

    # RESTRICT: aboneliği olan kullanıcı yanlışlıkla silinemez (geçmiş kayıtlar korunur).
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    # Paket düşürme bir sonraki dönemde geçerli olur; o zamana kadar burada bekler.
    pending_plan_id: Mapped[str | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL")
    )

    status: Mapped[SubscriptionStatus] = mapped_column(
        enum_column(SubscriptionStatus), default=SubscriptionStatus.ACTIVE
    )
    # NULL = sınırsız (Unlimited paket). Her ay yenilemede paketin hakkına geri doldurulur.
    remaining_credits: Mapped[int | None]
    remaining_guest_passes: Mapped[int] = mapped_column(default=0)

    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    # İki ayrı kolon plans tablosuna bağlı; hangisinin hangi ilişki olduğunu belirtmemiz gerekiyor.
    plan: Mapped["Plan"] = relationship(foreign_keys=[plan_id])
    pending_plan: Mapped["Plan | None"] = relationship(foreign_keys=[pending_plan_id])
    orders: Mapped[list["Order"]] = relationship(back_populates="subscription")
    payments: Mapped[list["Payment"]] = relationship(back_populates="subscription")
