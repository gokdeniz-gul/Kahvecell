from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.shop import Shop


class ShopPhoto(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Dükkân detay sayfasındaki fotoğraf galerisi (case 3.3).

    Bir dükkânın birden çok fotoğrafı olabileceği için ayrı tablo (3NF);
    `position` galerideki sırayı belirler, 0 numaralı fotoğraf kapak görselidir.
    """

    __tablename__ = "shop_photos"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_shop_photos_position_non_negative"),
        Index("ix_shop_photos_shop_position", "shop_id", "position"),
    )

    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(500))
    alt_text: Mapped[str] = mapped_column(String(150))  # ekran okuyucular için açıklama
    position: Mapped[int] = mapped_column(default=0)

    shop: Mapped["Shop"] = relationship(back_populates="photos")
