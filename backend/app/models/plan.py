from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import PlanType


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Abonelik paketleri (Starter / Premium / Unlimited).

    Fiyat ve haklar koda gömülü değil, burada tutulur: fiyat değişince kod değişmez.
    """

    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("monthly_price_kurus >= 0", name="ck_plans_price_non_negative"),
        CheckConstraint("guest_passes >= 0", name="ck_plans_guest_passes_non_negative"),
    )

    plan_type: Mapped[PlanType] = mapped_column(enum_column(PlanType), unique=True)
    name: Mapped[str] = mapped_column(String(50))

    # Para kuruş cinsinden tam sayı olarak saklanır (89,99 TL → 8999).
    # Ondalıklı sayılar (float) yuvarlama hatası yapar: 0.1 + 0.2 = 0.30000000000000004
    monthly_price_kurus: Mapped[int]

    # NULL = sınırsız (Unlimited paket).
    monthly_credits: Mapped[int | None]
    guest_passes: Mapped[int] = mapped_column(default=0)
    has_priority: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
