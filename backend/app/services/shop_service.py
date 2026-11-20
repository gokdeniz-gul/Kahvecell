"""Dükkân keşfi — case 3.3: listeleme, yakındakiler, arama, filtre, detay ve menü.

Mesafe nasıl hesaplanıyor?
  1. Yarıçap verildiyse veritabanı, konumun etrafındaki bir "kare" dışındaki dükkânları eler
     (enlem/boylam index'i ile hızlı).
  2. Kalan dükkânlar için gerçek mesafe Haversine formülüyle hesaplanır; kare köşelerinde
     kalıp yarıçap dışında olanlar da burada elenir.
SQLite'ta spatial index olmadığı için bu iki adımlı yöntemi seçtik. PostgreSQL'e geçilirse
PostGIS ile tek sorguda yapılabilir.
"""

from collections.abc import Callable
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models import Shop
from app.repositories.shop_repository import ShopRepository
from app.schemas.shop import ProductResponse, ShopDetail, ShopListResponse, ShopSort, ShopSummary
from app.utils.geo import bounding_box, haversine_km
from app.utils.text import normalize_for_search

# Türkiye 2016'dan beri yaz/kış saati uygulamıyor: her zaman UTC+3.
# (Windows'ta zoneinfo veritabanı olmadığı için sabit ofset daha güvenli.)
ISTANBUL_TZ = timezone(timedelta(hours=3), "Europe/Istanbul")


def is_open_at(opens_at: time, closes_at: time, now: time) -> bool:
    if opens_at <= closes_at:  # normal gün: 08:00–23:00
        return opens_at <= now < closes_at
    return now >= opens_at or now < closes_at  # gece yarısını geçen: 18:00–02:00


class ShopService:
    def __init__(self, db: Session, clock: Callable[[], datetime] | None = None) -> None:
        self.shops = ShopRepository(db)
        # Testlerde "saat şu an 07:00" diyebilmek için saat dışarıdan verilebiliyor.
        self.clock = clock or (lambda: datetime.now(ISTANBUL_TZ))

    def list_shops(
        self,
        *,
        lat: float | None,
        lng: float | None,
        radius_km: float | None,
        search: str | None,
        min_rating: float | None,
        open_now: bool,
        sort: ShopSort | None,
        offset: int,
        limit: int,
    ) -> ShopListResponse:
        has_location = self._validate_location(lat, lng, radius_km, sort)
        box = bounding_box(lat, lng, radius_km) if has_location and radius_km else None

        now = self.clock().astimezone(ISTANBUL_TZ).time()
        needle = normalize_for_search(search) if search and search.strip() else None

        results: list[ShopSummary] = []
        for shop in self.shops.list_active(box=box, min_rating=min_rating):
            if needle and needle not in normalize_for_search(f"{shop.name} {shop.address} {shop.city}"):
                continue
            distance = haversine_km(lat, lng, shop.latitude, shop.longitude) if has_location else None
            if radius_km is not None and distance is not None and distance > radius_km:
                continue
            summary = self._to_summary(shop, now, distance)
            if open_now and not summary.is_open_now:
                continue
            results.append(summary)

        self._sort(results, sort or (ShopSort.DISTANCE if has_location else ShopSort.RATING))
        return ShopListResponse(
            items=results[offset : offset + limit], total=len(results), offset=offset, limit=limit
        )

    def get_detail(self, shop_id: str, *, lat: float | None, lng: float | None) -> ShopDetail:
        has_location = self._validate_location(lat, lng, None, None)
        shop = self._get_shop(shop_id)
        distance = haversine_km(lat, lng, shop.latitude, shop.longitude) if has_location else None
        summary = self._to_summary(shop, self.clock().astimezone(ISTANBUL_TZ).time(), distance)
        return ShopDetail(**summary.model_dump(), phone=shop.phone, menu=self.get_menu(shop_id))

    def get_menu(self, shop_id: str) -> list[ProductResponse]:
        self._get_shop(shop_id)  # dükkân yoksa 404
        return [ProductResponse.model_validate(p) for p in self.shops.list_menu(shop_id)]

    # ---------- Yardımcılar ----------

    def _get_shop(self, shop_id: str) -> Shop:
        shop = self.shops.get_active(shop_id)
        if shop is None:
            raise NotFoundError("Dükkân bulunamadı.", code="SHOP_NOT_FOUND")
        return shop

    @staticmethod
    def _validate_location(
        lat: float | None, lng: float | None, radius_km: float | None, sort: ShopSort | None
    ) -> bool:
        if (lat is None) != (lng is None):
            raise BadRequestError("Konum için lat ve lng birlikte gönderilmeli.", code="LOCATION_INCOMPLETE")
        has_location = lat is not None
        if not has_location and radius_km is not None:
            raise BadRequestError("radius_km için konum (lat, lng) gerekli.", code="LOCATION_REQUIRED")
        if not has_location and sort == ShopSort.DISTANCE:
            raise BadRequestError("Mesafeye göre sıralama için konum gerekli.", code="LOCATION_REQUIRED")
        return has_location

    @staticmethod
    def _to_summary(shop: Shop, now: time, distance_km: float | None) -> ShopSummary:
        return ShopSummary.model_validate(
            {
                **{field: getattr(shop, field) for field in ShopSummary.model_fields
                   if field not in ("is_open_now", "distance_km")},
                "is_open_now": is_open_at(shop.opens_at, shop.closes_at, now),
                "distance_km": round(distance_km, 2) if distance_km is not None else None,
            }
        )

    @staticmethod
    def _sort(shops: list[ShopSummary], sort: ShopSort) -> None:
        if sort == ShopSort.DISTANCE:
            shops.sort(key=lambda s: s.distance_km)
        elif sort == ShopSort.RATING:
            shops.sort(key=lambda s: (-s.rating, -s.rating_count))
        else:
            shops.sort(key=lambda s: normalize_for_search(s.name))
