from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import PaymentStatus

if TYPE_CHECKING:
    from app.models.plan import Plan
    from app.models.subscription import Subscription
    from app.models.user import User


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Mobil ödeme simülasyonunun kayıtları (case bölüm 12: "ödeme geçmişi kaydedilmeli").

    Başarısız denemeler de saklanır; bu yüzden subscription_id boş olabilir.
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_kurus >= 0", name="ck_payments_amount_non_negative"),
        Index("ix_payments_user_created", "user_id", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    subscription_id: Mapped[str | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL")
    )

    transaction_id: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[PaymentStatus] = mapped_column(enum_column(PaymentStatus))
    amount_kurus: Mapped[int]
    # Kart numarasının tamamı ASLA saklanmaz; sadece son 4 hane.
    card_last4: Mapped[str] = mapped_column(String(4))
    failure_reason: Mapped[str | None] = mapped_column(String(255))

    user: Mapped["User"] = relationship(back_populates="payments")
    plan: Mapped["Plan"] = relationship()
    subscription: Mapped["Subscription | None"] = relationship(back_populates="payments")
