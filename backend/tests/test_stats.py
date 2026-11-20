"""Dükkân sahibi dashboard'u: günlük sipariş analitiği (case 3.5)."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.services.shop_service import ISTANBUL_TZ
from tests.test_orders import customer, karakoy, owner, place_order, product_id, set_status  # noqa: F401
from tests.test_subscriptions import subscribe

STATS = "/api/v1/orders/stats"

pytestmark = pytest.mark.usefixtures("plans")


def at(hour: int, minute: int = 0, day: int = 15) -> datetime:
    return datetime(2026, 1, day, hour, minute, tzinfo=ISTANBUL_TZ)


def test_daily_stats(client: TestClient, customer, owner, karakoy, fixed_clock) -> None:  # noqa: F811
    subscribe(client, customer["headers"], "PREMIUM")

    fixed_clock(at(9, 0))
    first = place_order(client, customer["headers"], karakoy).json()["data"]["id"]
    fixed_clock(at(9, 30))
    place_order(client, customer["headers"], karakoy, product_id=product_id(karakoy, "Espresso"))
    fixed_clock(at(14, 0))
    cancelled = place_order(client, customer["headers"], karakoy).json()["data"]["id"]
    set_status(client, customer["headers"], cancelled, "CANCELLED")

    # İlk sipariş 12 dakikada teslim ediliyor
    for status in ("ACCEPTED", "PREPARING", "READY"):
        set_status(client, owner["headers"], first, status)
    qr_content = client.get(f"/api/v1/orders/{first}", headers=customer["headers"]).json()["data"]["qr"]["content"]
    fixed_clock(at(9, 12))
    set_status(client, owner["headers"], first, "COMPLETED", qr_content)

    fixed_clock(at(18, 0))
    stats = client.get(STATS, headers=owner["headers"]).json()["data"]

    assert stats["day"] == "2026-01-15"
    assert stats["total_orders"] == 3
    assert (stats["completed"], stats["cancelled"], stats["active"]) == (1, 1, 1)
    assert stats["by_status"]["PENDING"] == 1
    assert stats["credits_used"] == 3  # iptalde iade edilse de o gün kullanılmıştı
    assert stats["avg_prep_minutes"] == 12.0
    assert stats["top_products"][0] == {"name": "Flat White", "count": 2}
    assert stats["hourly"][9] == 2 and stats["hourly"][14] == 1 and sum(stats["hourly"]) == 3


def test_stats_only_include_selected_day(client: TestClient, customer, owner, karakoy, fixed_clock) -> None:  # noqa: F811
    subscribe(client, customer["headers"], "STARTER")
    fixed_clock(at(10, day=14))
    place_order(client, customer["headers"], karakoy)
    fixed_clock(at(10, day=15))

    today = client.get(STATS, headers=owner["headers"]).json()["data"]
    yesterday = client.get(STATS, headers=owner["headers"], params={"day": "2026-01-14"}).json()["data"]

    assert today["total_orders"] == 0
    assert today["avg_prep_minutes"] is None
    assert yesterday["total_orders"] == 1


def test_customer_cannot_see_stats(client: TestClient, customer) -> None:  # noqa: F811
    assert client.get(STATS, headers=customer["headers"]).status_code == 403
