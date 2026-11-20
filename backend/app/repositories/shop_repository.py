from collections.abc import Sequence

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models import Product, Shop
from app.models.enums import ProductCategory
from app.utils.geo import BoundingBox

# Alfabetik sıralama COLD_COFFEE'yi HOT_COFFEE'den önce koyardı; menüde sıcaklar önce gelsin.
_MENU_CATEGORY_ORDER = case(
    {
        ProductCategory.HOT_COFFEE: 0,
        ProductCategory.COLD_COFFEE: 1,
        ProductCategory.TEA: 2,
        ProductCategory.OTHER: 3,
    },
    value=Product.category,
    else_=9,
)


class ShopRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active(
        self, *, box: BoundingBox | None = None, min_rating: float | None = None
    ) -> Sequence[Shop]:
        query = select(Shop).where(Shop.is_active.is_(True))
        if box is not None:
            # ix_shops_lat_lng index'i sayesinde kutu dışındaki dükkânlar hızlıca elenir.
            query = query.where(
                Shop.latitude.between(box.min_lat, box.max_lat),
                Shop.longitude.between(box.min_lng, box.max_lng),
            )
        if min_rating is not None:
            query = query.where(Shop.rating >= min_rating)
        return self.db.scalars(query).all()

    def get_active(self, shop_id: str) -> Shop | None:
        return self.db.scalar(select(Shop).where(Shop.id == shop_id, Shop.is_active.is_(True)))

    def list_menu(self, shop_id: str) -> Sequence[Product]:
        return self.db.scalars(
            select(Product)
            .where(Product.shop_id == shop_id)
            # Önce satışta olanlar, sonra menü sırası (sıcak → soğuk → çay → diğer), sonra ad
            .order_by(Product.is_available.desc(), _MENU_CATEGORY_ORDER, Product.name)
        ).all()
