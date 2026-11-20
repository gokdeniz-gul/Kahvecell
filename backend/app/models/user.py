from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.payment import Payment
    from app.models.refresh_token import RefreshToken
    from app.models.shop import Shop
    from app.models.subscription import Subscription


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    # unique=True otomatik olarak index de oluşturur; girişte telefonla arama hızlı olur.
    phone_number: Mapped[str] = mapped_column(String(15), unique=True)
    is_phone_verified: Mapped[bool] = mapped_column(default=False)

    # Kayıt sadece GSM ile başlıyor; ad ve e-posta "profil tamamlama" adımında dolduruluyor.
    full_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole), default=UserRole.CUSTOMER)

    # Örnek: {"coffee_types": ["latte", "americano"], "allergens": ["lactose"]}
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")
    owned_shops: Mapped[list["Shop"]] = relationship(back_populates="owner")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def is_profile_complete(self) -> bool:
        """Case 7.1: ilk girişte profil tamamlama ekranı gösterilsin mi?"""
        return bool(self.full_name)
