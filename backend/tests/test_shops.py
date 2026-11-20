"""Case 3.3: dükkân listeleme, yakındakiler (Haversine), arama, filtre, detay ve menü."""

from datetime import datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Product, Shop
from app.schemas.shop import ShopSort
from app.services.shop_service import ISTANBUL_TZ, ShopService, is_open_at
from app.utils.geo import bounding_box, haversine_km
from app.utils.text import normalize_for_search
from scripts.seed import SHOPS

SHOPS_URL = "/api/v1/shops"
TAKSIM = {"lat": 41.0370, "lng": 28.9850}


@pytest.fixture
def shops(db: Session) -> dict[str, Shop]:
    """Seed betiğindeki gerçek İstanbul dükkânları ve menüleri."""
    created = {}
    for data in SHOPS:
        shop = Shop(**{k: v for k, v in data.items() if k != "products"})
        shop.products = [
            Product(name=name, description=desc, category=cat, price_kurus=round(price * 100))
            for name, desc, cat, price in data["products"]
        ]
        db.add(shop)
        created[shop.name] = shop
    db.commit()
    return created


def names(response) -> list[str]:
    return [shop["name"] for shop in response.json()["data"]["items"]]


# ---------- Yardımcı fonksiyonlar (unit) ----------


def test_haversine_one_degree_latitude_is_about_111_km() -> None:
    assert haversine_km(41.0, 29.0, 42.0, 29.0) == pytest.approx(111.2, abs=0.1)


def test_haversine_taksim_to_kadikoy() -> None:
    # Taksim Meydanı → Kadıköy İskelesi: kuş uçuşu yaklaşık 6 km
    assert haversine_km(41.0370, 28.9850, 40.9910, 29.0233) == pytest.approx(6.0, abs=0.5)


def test_bounding_box_contains_radius() -> None:
    box = bounding_box(41.0, 29.0, 2)
    # Kutunun kenarları merkezden en az 2 km uzakta olmalı
    assert haversine_km(41.0, 29.0, box.max_lat, 29.0) == pytest.approx(2, abs=0.01)
    assert haversine_km(41.0, 29.0, 41.0, box.max_lng) == pytest.approx(2, abs=0.01)


@pytest.mark.parametrize("text", ["KADIKÖY", "Kadıköy", "kadikoy", "  kadıköy "])
def test_turkish_search_normalization(text: str) -> None:
    assert normalize_for_search(text) == "kadikoy"


def test_normalization_handles_dotted_capital_i() -> None:
    assert normalize_for_search("İSTANBUL") == normalize_for_search("istanbul")


@pytest.mark.parametrize(
    ("opens", "closes", "now", "expected"),
    [
        (time(8), time(23), time(12), True),
        (time(8), time(23), time(7, 59), False),
        (time(8), time(23), time(23), False),  # kapanış saatinde kapalı
        (time(18), time(2), time(1), True),  # gece yarısını geçen dükkân
        (time(18), time(2), time(3), False),
    ],
)
def test_is_open_at(opens: time, closes: time, now: time, expected: bool) -> None:
    assert is_open_at(opens, closes, now) is expected


# ---------- Listeleme ----------


@pytest.mark.usefixtures("shops")
def test_list_all_shops_sorted_by_rating(client: TestClient) -> None:
    response = client.get(SHOPS_URL)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == len(SHOPS)
    ratings = [shop["rating"] for shop in data["items"]]
    assert ratings == sorted(ratings, reverse=True)
    assert all(shop["distance_km"] is None for shop in data["items"])


@pytest.mark.usefixtures("shops")
def test_nearby_shops_sorted_by_distance(client: TestClient) -> None:
    response = client.get(SHOPS_URL, params=TAKSIM)

    items = response.json()["data"]["items"]
    distances = [shop["distance_km"] for shop in items]
    assert distances == sorted(distances)
    assert items[0]["name"] == "Cihangir Köşe"  # Taksim'e en yakın
    assert items[-1]["name"] == "Moda Kavurma Evi"  # karşı yakada, en uzak


@pytest.mark.usefixtures("shops")
def test_radius_filters_far_shops(client: TestClient) -> None:
    response = client.get(SHOPS_URL, params={**TAKSIM, "radius_km": 2})

    items = response.json()["data"]["items"]
    assert items  # Cihangir ve Karaköy 2 km içinde
    assert all(shop["distance_km"] <= 2 for shop in items)
    assert "Moda Kavurma Evi" not in names(response)


@pytest.mark.usefixtures("shops")
def test_search_by_name_is_case_and_turkish_insensitive(client: TestClient) -> None:
    assert names(client.get(SHOPS_URL, params={"q": "carsi"})) == ["Çarşı Kahvecisi"]
    assert names(client.get(SHOPS_URL, params={"q": "LİMAN"})) == ["Karaköy Liman Kahve"]


@pytest.mark.usefixtures("shops")
def test_search_by_address(client: TestClient) -> None:
    assert names(client.get(SHOPS_URL, params={"q": "uskudar"})) == ["Kuzguncuk Bostan Kahve"]


@pytest.mark.usefixtures("shops")
def test_search_without_match_returns_empty_list(client: TestClient) -> None:
    response = client.get(SHOPS_URL, params={"q": "ankara"})

    assert response.status_code == 200
    assert response.json()["data"] == {"items": [], "total": 0, "offset": 0, "limit": 20}


@pytest.mark.usefixtures("shops")
def test_search_and_location_together(client: TestClient) -> None:
    response = client.get(SHOPS_URL, params={**TAKSIM, "q": "kahve"})

    distances = [shop["distance_km"] for shop in response.json()["data"]["items"]]
    assert len(distances) >= 2
    assert distances == sorted(distances)


@pytest.mark.usefixtures("shops")
def test_min_rating_filter(client: TestClient) -> None:
    response = client.get(SHOPS_URL, params={"min_rating": 4.6})

    assert all(shop["rating"] >= 4.6 for shop in response.json()["data"]["items"])
    assert "Kuzguncuk Bostan Kahve" not in names(response)  # 4.3


@pytest.mark.usefixtures("shops")
def test_sort_by_name(client: TestClient) -> None:
    result = names(client.get(SHOPS_URL, params={"sort": "name"}))

    assert result == sorted(result, key=normalize_for_search)


@pytest.mark.usefixtures("shops")
def test_pagination(client: TestClient) -> None:
    first = client.get(SHOPS_URL, params={"limit": 2}).json()["data"]
    second = client.get(SHOPS_URL, params={"limit": 2, "offset": 2}).json()["data"]

    assert first["total"] == len(SHOPS)
    assert len(first["items"]) == 2
    assert {s["id"] for s in first["items"]}.isdisjoint({s["id"] for s in second["items"]})


@pytest.mark.usefixtures("shops")
def test_inactive_shops_are_hidden(client: TestClient, db: Session) -> None:
    db.execute(update(Shop).where(Shop.name == "Cihangir Köşe").values(is_active=False))
    db.commit()

    assert "Cihangir Köşe" not in names(client.get(SHOPS_URL))


@pytest.mark.usefixtures("shops")
def test_open_now_filter(db: Session) -> None:
    # Saat 19:00: Kuzguncuk (10–18) kapalı, Karaköy (08–20) açık olmalı.
    at_19 = lambda: datetime(2026, 1, 15, 19, 0, tzinfo=ISTANBUL_TZ)  # noqa: E731
    service = ShopService(db, clock=at_19)

    result = service.list_shops(
        lat=None, lng=None, radius_km=None, search=None, min_rating=None,
        open_now=True, sort=ShopSort.NAME, offset=0, limit=20,
    )

    result_names = [shop.name for shop in result.items]
    assert "Kuzguncuk Bostan Kahve" not in result_names
    assert "Karaköy Liman Kahve" in result_names
    assert all(shop.is_open_now for shop in result.items)


# ---------- Hatalı parametreler ----------


@pytest.mark.parametrize(
    ("params", "code"),
    [
        ({"lat": 41.0}, "LOCATION_INCOMPLETE"),
        ({"radius_km": 2}, "LOCATION_REQUIRED"),
        ({"sort": "distance"}, "LOCATION_REQUIRED"),
    ],
)
def test_invalid_location_params(client: TestClient, params: dict, code: str) -> None:
    response = client.get(SHOPS_URL, params=params)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == code


def test_out_of_range_coordinates_fail_validation(client: TestClient) -> None:
    assert client.get(SHOPS_URL, params={"lat": 100, "lng": 29}).status_code == 422


# ---------- Detay ve menü ----------


def test_shop_detail_with_menu_and_distance(client: TestClient, shops: dict[str, Shop]) -> None:
    shop = shops["Karaköy Liman Kahve"]

    response = client.get(f"{SHOPS_URL}/{shop.id}", params=TAKSIM)

    assert response.status_code == 200
    detail = response.json()["data"]
    assert detail["name"] == "Karaköy Liman Kahve"
    assert detail["distance_km"] > 0
    assert len(detail["menu"]) == 5
    espresso = next(p for p in detail["menu"] if p["name"] == "Espresso")
    assert espresso["price_tl"] == 125.0


def test_menu_endpoint(client: TestClient, shops: dict[str, Shop]) -> None:
    response = client.get(f"{SHOPS_URL}/{shops['Çarşı Kahvecisi'].id}/menu")

    assert response.status_code == 200
    assert "Türk Kahvesi" in [p["name"] for p in response.json()["data"]]


def test_menu_lists_hot_coffee_before_cold_and_tea(
    client: TestClient, shops: dict[str, Shop]
) -> None:
    menu = client.get(f"{SHOPS_URL}/{shops['Karaköy Liman Kahve'].id}/menu").json()["data"]

    categories = [p["category"] for p in menu]
    assert categories == ["HOT_COFFEE"] * 3 + ["COLD_COFFEE"] * 2


def test_unavailable_products_listed_last(
    client: TestClient, shops: dict[str, Shop], db: Session
) -> None:
    shop = shops["Moda Kavurma Evi"]
    db.execute(update(Product).where(Product.name == "Cappuccino", Product.shop_id == shop.id)
               .values(is_available=False))
    db.commit()

    menu = client.get(f"{SHOPS_URL}/{shop.id}/menu").json()["data"]

    assert menu[-1]["name"] == "Cappuccino"
    assert menu[-1]["is_available"] is False


def test_unknown_shop_returns_404(client: TestClient) -> None:
    for url in (f"{SHOPS_URL}/olmayan-id", f"{SHOPS_URL}/olmayan-id/menu"):
        response = client.get(url)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SHOP_NOT_FOUND"
