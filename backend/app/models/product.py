from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import ProductCategory

if TYPE_CHECKING:
    from app.models.shop import Shop


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Bir dükkânın menüsündeki ürün. Her dükkânın menüsü kendine aittir."""

    __tablename__ = "products"
    __table_args__ = (
        # Aynı dükkânda aynı isimde iki ürün olamaz.
        UniqueConstraint("shop_id", "name", name="uq_products_shop_name"),
        CheckConstraint("price_kurus >= 0", name="ck_products_price_non_negative"),
    )

    # CASCADE: dükkân silinirse menüsü de silinir.
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500))
    category: Mapped[ProductCategory] = mapped_column(enum_column(ProductCategory))
    # Abonelikle ödenmese bile menüde fiyat gösterilir (indirim oranını göstermek için de lazım).
    price_kurus: Mapped[int]
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_available: Mapped[bool] = mapped_column(default=True)

    shop: Mapped["Shop"] = relationship(back_populates="products")
