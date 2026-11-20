from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.product import Product
    from app.models.user import User


class Shop(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shops"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_shops_latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_shops_longitude_range"),
        CheckConstraint("rating BETWEEN 0 AND 5", name="ck_shops_rating_range"),
        # SQLite'ta spatial index yok. Yakın dükkân aramasında önce bu index ile kaba bir
        # "kutu" içindeki dükkânları alıp, sonra Haversine ile gerçek mesafeyi hesaplayacağız.
        Index("ix_shops_lat_lng", "latitude", "longitude"),
    )

    # Dükkân sahibi kullanıcı silinirse dükkân kalır, sadece sahibi boşalır.
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(50), index=True)
    phone: Mapped[str | None] = mapped_column(String(15))
    image_url: Mapped[str | None] = mapped_column(String(500))

    # Konum: enlem ve boylam ayrı ondalıklı kolonlarda (case'in kabul ettiği yöntem).
    latitude: Mapped[float]
    longitude: Mapped[float]

    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)

    rating: Mapped[float] = mapped_column(default=0)
    rating_count: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    owner: Mapped["User | None"] = relationship(back_populates="owned_shops")
    products: Mapped[list["Product"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="shop")
