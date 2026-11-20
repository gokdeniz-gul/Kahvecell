from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.common import ApiResponse, ok
from app.schemas.shop import ProductResponse, ShopDetail, ShopListResponse, ShopSort
from app.services.shop_service import ShopService

router = APIRouter(prefix="/shops", tags=["Shops"])

Latitude = Annotated[float | None, Query(ge=-90, le=90, description="Enlem, örn: 41.0370")]
Longitude = Annotated[float | None, Query(ge=-180, le=180, description="Boylam, örn: 28.9850")]


@router.get(
    "",
    summary="Dükkânları listele / yakındakileri bul / ara / filtrele (giriş gerekmez)",
    description=(
        "- Hiç parametre yoksa: tüm dükkânlar, puana göre.\n"
        "- `lat` + `lng` verilirse: her dükkânın `distance_km` değeri hesaplanır, en yakın en üstte.\n"
        "- `radius_km` ile sadece o yarıçaptaki dükkânlar.\n"
        "- `q`: ad, adres veya semtte arama. Türkçe karakter duyarsız (`kadikoy` → Kadıköy)."
    ),
)
def list_shops(
    db: DbSession,
    lat: Latitude = None,
    lng: Longitude = None,
    radius_km: Annotated[float | None, Query(gt=0, le=50, description="Yarıçap (km)")] = None,
    q: Annotated[str | None, Query(max_length=100, description="Ad / adres / semt araması")] = None,
    min_rating: Annotated[float | None, Query(ge=0, le=5, description="En düşük puan")] = None,
    open_now: Annotated[bool, Query(description="Sadece şu an açık olanlar")] = False,
    sort: Annotated[ShopSort | None, Query(description="Boş bırakılırsa: konum varsa distance, yoksa rating")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[ShopListResponse]:
    return ok(
        ShopService(db).list_shops(
            lat=lat, lng=lng, radius_km=radius_km, search=q, min_rating=min_rating,
            open_now=open_now, sort=sort, offset=offset, limit=limit,
        )
    )


@router.get("/{shop_id}", summary="Dükkân detayı + menü (konum verilirse mesafe de gelir)")
def get_shop(
    shop_id: str, db: DbSession, lat: Latitude = None, lng: Longitude = None
) -> ApiResponse[ShopDetail]:
    return ok(ShopService(db).get_detail(shop_id, lat=lat, lng=lng))


@router.get("/{shop_id}/menu", summary="Sadece dükkânın menüsü")
def get_menu(shop_id: str, db: DbSession) -> ApiResponse[list[ProductResponse]]:
    return ok(ShopService(db).get_menu(shop_id))
