"""Case 3.4 (sipariş), 7.2 (sipariş akışı), 7.3 (dükkân akışı), 13.2 (imzalı QR)."""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core import qr
from app.models import Product, Shop, Subscription
from app.models.enums import UserRole
from app.services.shop_service import ISTANBUL_TZ
from tests.conftest import auth_header, register_and_login
from tests.test_subscriptions import subscribe

ORDERS = "/api/v1/orders"
MY_SUB = "/api/v1/subscriptions/me"

pytestmark = pytest.mark.usefixtures("plans", "fixed_clock")


# ---------- Hazırlık ----------


@pytest.fixture
def customer(client: TestClient) -> dict:
    data = register_and_login(client, "5551112233")
    return {"id": data["user"]["id"], "headers": auth_header(data["access_token"])}


@pytest.fixture
def owner(client: TestClient, db: Session, shops: dict[str, Shop], set_role) -> dict:
    """Tüm test dükkânlarının sahibi."""
    data = register_and_login(client, "5559876543")
    set_role(data["user"]["id"], UserRole.SHOP_OWNER)
    db.execute(update(Shop).values(owner_id=data["user"]["id"]))
    db.commit()
    return {"id": data["user"]["id"], "headers": auth_header(data["access_token"])}


@pytest.fixture
def karakoy(shops: dict[str, Shop]) -> Shop:
    return shops["Karaköy Liman Kahve"]


def product_id(shop: Shop, name: str = "Flat White") -> str:
    return next(p.id for p in shop.products if p.name == name)


def order_body(shop: Shop, **overrides) -> dict:
    if "product_id" not in overrides:
        overrides["product_id"] = product_id(shop)
    return {"shop_id": shop.id, **overrides}


def place_order(client: TestClient, headers: dict, shop: Shop, **overrides):
    return client.post(ORDERS, headers=headers, json=order_body(shop, **overrides))


def set_status(client: TestClient, headers: dict, order_id: str, status: str, qr_content: str | None = None):
    body = {"status": status} | ({"qr_content": qr_content} if qr_content else {})
    return client.patch(f"{ORDERS}/{order_id}/status", headers=headers, json=body)


def remaining_credits(client: TestClient, headers: dict) -> int | None:
    return client.get(MY_SUB, headers=headers).json()["data"]["remaining_credits"]


# ---------- Sipariş verme ----------


def test_order_without_subscription_is_rejected(client: TestClient, customer: dict, karakoy: Shop) -> None:
    response = place_order(client, customer["headers"], karakoy)

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "NO_ACTIVE_SUBSCRIPTION"
    assert "aktif bir aboneliğiniz" in error["message"]


def test_order_consumes_one_credit(client: TestClient, customer: dict, karakoy: Shop) -> None:
    subscribe(client, customer["headers"], "STARTER")

    response = place_order(
        client, customer["headers"], karakoy,
        size="L", sugar="LESS", milk="OAT", extra_shots=1, note="Az köpüklü",
    )

    assert response.status_code == 201
    order = response.json()["data"]
    assert order["status"] == "PENDING"
    assert order["credits_used"] == 1
    assert order["shop"]["name"] == "Karaköy Liman Kahve"
    item = order["items"][0]
    assert (item["product_name"], item["size"], item["sugar"], item["milk"], item["extra_shots"]) == (
        "Flat White", "L", "LESS", "OAT", 1
    )
    assert item["unit_price_tl"] == 195.0
    assert remaining_credits(client, customer["headers"]) == 9


def test_unlimited_plan_does_not_consume_credits(client: TestClient, customer: dict, karakoy: Shop) -> None:
    subscribe(client, customer["headers"], "UNLIMITED")

    order = place_order(client, customer["headers"], karakoy).json()["data"]

    assert order["credits_used"] == 0
    assert order["is_priority"] is True
    assert remaining_credits(client, customer["headers"]) is None


def test_order_rejected_when_credits_run_out(
    client: TestClient, customer: dict, karakoy: Shop, db: Session
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    db.execute(update(Subscription).values(remaining_credits=1))
    db.commit()

    assert place_order(client, customer["headers"], karakoy).status_code == 201  # son hak
    response = place_order(client, customer["headers"], karakoy)

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "NO_CREDITS_LEFT"
    assert "kahve hakkınız bitti" in error["message"]
    assert "renews_at" in error["details"]
    assert remaining_credits(client, customer["headers"]) == 0  # eksiye düşmedi


def test_cancelled_subscription_can_still_order_until_period_end(
    client: TestClient, customer: dict, karakoy: Shop
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    client.delete(MY_SUB, headers=customer["headers"])

    assert place_order(client, customer["headers"], karakoy).status_code == 201


def test_cannot_order_from_closed_shop(
    client: TestClient, customer: dict, shops: dict[str, Shop], fixed_clock
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    fixed_clock(datetime(2026, 1, 15, 19, 0, tzinfo=ISTANBUL_TZ))  # Kuzguncuk 10–18

    response = place_order(client, customer["headers"], shops["Kuzguncuk Bostan Kahve"],
                           product_id=product_id(shops["Kuzguncuk Bostan Kahve"], "Türk Kahvesi"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SHOP_CLOSED"
    assert remaining_credits(client, customer["headers"]) == 10  # hak düşmedi


def test_cannot_order_product_from_another_shop(
    client: TestClient, customer: dict, shops: dict[str, Shop]
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    other_shop_product = product_id(shops["Moda Kavurma Evi"], "Espresso")

    response = place_order(client, customer["headers"], shops["Karaköy Liman Kahve"],
                           product_id=other_shop_product)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_cannot_order_unavailable_product(
    client: TestClient, customer: dict, karakoy: Shop, db: Session
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    db.execute(update(Product).where(Product.id == product_id(karakoy)).values(is_available=False))
    db.commit()

    response = place_order(client, customer["headers"], karakoy)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PRODUCT_UNAVAILABLE"


def test_customization_is_validated(client: TestClient, customer: dict, karakoy: Shop) -> None:
    subscribe(client, customer["headers"], "STARTER")

    assert place_order(client, customer["headers"], karakoy, size="XL").status_code == 422
    assert place_order(client, customer["headers"], karakoy, extra_shots=5).status_code == 422


def test_shop_owner_cannot_place_orders(client: TestClient, owner: dict, karakoy: Shop) -> None:
    assert place_order(client, owner["headers"], karakoy).status_code == 403


# ---------- QR kod (13.2) ----------


def test_order_has_signed_qr_in_case_format(client: TestClient, customer: dict, karakoy: Shop) -> None:
    subscribe(client, customer["headers"], "STARTER")

    order = place_order(client, customer["headers"], karakoy).json()["data"]

    code = order["qr"]
    assert set(code["payload"]) == {"order_id", "user_id", "shop_id", "created_at", "signature"}
    assert code["payload"]["order_id"] == order["id"]
    assert code["payload"]["user_id"] == customer["id"]
    assert code["payload"]["shop_id"] == karakoy.id
    assert code["payload"]["created_at"].endswith("Z")  # ISO 8601, UTC
    assert len(code["payload"]["signature"]) == 64  # HMAC-SHA256 hex
    assert json.loads(code["content"]) == code["payload"]
    assert code["image_data_url"].startswith("data:image/png;base64,")


def test_signature_changes_if_any_field_changes() -> None:
    payload = qr.build_payload("o1", "u1", "s1", datetime(2026, 1, 1, tzinfo=ISTANBUL_TZ))

    assert qr.is_signature_valid(payload)
    for field in ("order_id", "user_id", "shop_id", "created_at"):
        assert not qr.is_signature_valid({**payload, field: payload[field] + "x"})
    assert not qr.is_signature_valid({**payload, "signature": "0" * 64})


# ---------- Takip ----------


def test_customer_and_owner_can_track_order(
    client: TestClient, customer: dict, owner: dict, karakoy: Shop
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]

    as_customer = client.get(f"{ORDERS}/{order_id}", headers=customer["headers"]).json()["data"]
    as_owner = client.get(f"{ORDERS}/{order_id}", headers=owner["headers"]).json()["data"]

    assert as_customer["qr"] is not None
    assert as_owner["qr"] is None  # QR sadece müşteride; dükkân okutarak alır
    assert as_owner["allowed_next_statuses"] == ["ACCEPTED", "CANCELLED"]
    assert as_customer["allowed_next_statuses"] == ["CANCELLED"]


def test_other_users_cannot_see_order(client: TestClient, customer: dict, karakoy: Shop) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]
    stranger = auth_header(register_and_login(client, "5554445566")["access_token"])

    response = client.get(f"{ORDERS}/{order_id}", headers=stranger)

    assert response.status_code == 404


def test_order_history_newest_first(
    client: TestClient, customer: dict, karakoy: Shop, fixed_clock
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    fixed_clock(datetime(2026, 1, 15, 10, 0, tzinfo=ISTANBUL_TZ))
    first = place_order(client, customer["headers"], karakoy).json()["data"]["id"]
    fixed_clock(datetime(2026, 1, 15, 11, 0, tzinfo=ISTANBUL_TZ))
    second = place_order(client, customer["headers"], karakoy).json()["data"]["id"]

    history = client.get(f"{ORDERS}/history", headers=customer["headers"]).json()["data"]

    assert history["total"] == 2
    assert [o["id"] for o in history["items"]] == [second, first]


def test_incoming_orders_put_priority_customers_first(
    client: TestClient, customer: dict, owner: dict, karakoy: Shop, fixed_clock
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    fixed_clock(datetime(2026, 1, 15, 10, 0, tzinfo=ISTANBUL_TZ))
    normal = place_order(client, customer["headers"], karakoy).json()["data"]["id"]

    vip = auth_header(register_and_login(client, "5557778899")["access_token"])
    subscribe(client, vip, "UNLIMITED")
    fixed_clock(datetime(2026, 1, 15, 10, 5, tzinfo=ISTANBUL_TZ))  # daha sonra geldi
    priority = place_order(client, vip, karakoy).json()["data"]["id"]

    incoming = client.get(f"{ORDERS}/incoming", headers=owner["headers"]).json()["data"]

    assert [o["id"] for o in incoming["items"]] == [priority, normal]


def test_customer_cannot_see_incoming_orders(client: TestClient, customer: dict) -> None:
    assert client.get(f"{ORDERS}/incoming", headers=customer["headers"]).status_code == 403


# ---------- Durum güncelleme (dükkân akışı) ----------


def test_full_shop_flow_until_delivery_with_qr(
    client: TestClient, customer: dict, owner: dict, karakoy: Shop
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order = place_order(client, customer["headers"], karakoy).json()["data"]
    order_id, qr_content = order["id"], order["qr"]["content"]

    for status in ("ACCEPTED", "PREPARING", "READY"):
        response = set_status(client, owner["headers"], order_id, status)
        assert response.status_code == 200, response.json()
        assert response.json()["data"]["status"] == status

    verified = client.post(f"{ORDERS}/verify-qr", headers=owner["headers"], json={"qr_content": qr_content})
    assert verified.status_code == 200
    assert verified.json()["data"]["valid"] is True
    assert verified.json()["data"]["can_complete"] is True

    done = set_status(client, owner["headers"], order_id, "COMPLETED", qr_content)
    assert done.status_code == 200
    assert done.json()["data"]["status"] == "COMPLETED"
    assert done.json()["data"]["completed_at"] is not None

    # Müşteri teslim edilen siparişte artık QR görmez; QR ikinci kez kullanılamaz.
    assert client.get(f"{ORDERS}/{order_id}", headers=customer["headers"]).json()["data"]["qr"] is None
    again = client.post(f"{ORDERS}/verify-qr", headers=owner["headers"], json={"qr_content": qr_content})
    assert again.json()["error"]["code"] == "QR_ALREADY_USED"


def test_status_cannot_skip_steps(client: TestClient, customer: dict, owner: dict, karakoy: Shop) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]

    response = set_status(client, owner["headers"], order_id, "READY")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INVALID_STATUS_TRANSITION"
    assert error["details"]["allowed"] == ["ACCEPTED", "CANCELLED"]


def test_completion_requires_qr(client: TestClient, customer: dict, owner: dict, karakoy: Shop) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]
    for status in ("ACCEPTED", "PREPARING", "READY"):
        set_status(client, owner["headers"], order_id, status)

    response = set_status(client, owner["headers"], order_id, "COMPLETED")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "QR_REQUIRED"


def test_completion_with_qr_of_another_order(
    client: TestClient, customer: dict, owner: dict, karakoy: Shop
) -> None:
    subscribe(client, customer["headers"], "PREMIUM")
    first = place_order(client, customer["headers"], karakoy).json()["data"]
    second = place_order(client, customer["headers"], karakoy).json()["data"]
    for status in ("ACCEPTED", "PREPARING", "READY"):
        set_status(client, owner["headers"], first["id"], status)

    response = set_status(client, owner["headers"], first["id"], "COMPLETED", second["qr"]["content"])

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "QR_ORDER_MISMATCH"


def test_customer_cannot_advance_status(client: TestClient, customer: dict, karakoy: Shop) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]

    response = set_status(client, customer["headers"], order_id, "ACCEPTED")

    assert response.status_code == 409


def test_owner_of_other_shop_cannot_update(
    client: TestClient, customer: dict, owner: dict, karakoy: Shop, set_role
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]
    other = register_and_login(client, "5553334455")
    set_role(other["user"]["id"], UserRole.SHOP_OWNER)

    response = set_status(client, auth_header(other["access_token"]), order_id, "ACCEPTED")

    assert response.status_code == 404


# ---------- İptal ve hak iadesi ----------


def test_customer_cancel_refunds_credit(client: TestClient, customer: dict, karakoy: Shop) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]
    assert remaining_credits(client, customer["headers"]) == 9

    response = set_status(client, customer["headers"], order_id, "CANCELLED")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "CANCELLED"
    assert remaining_credits(client, customer["headers"]) == 10


def test_customer_cannot_cancel_after_shop_accepts(
    client: TestClient, customer: dict, owner: dict, karakoy: Shop
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]
    set_status(client, owner["headers"], order_id, "ACCEPTED")

    assert set_status(client, customer["headers"], order_id, "CANCELLED").status_code == 409


def test_shop_can_reject_order_and_credit_is_refunded(
    client: TestClient, customer: dict, owner: dict, karakoy: Shop
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order_id = place_order(client, customer["headers"], karakoy).json()["data"]["id"]

    assert set_status(client, owner["headers"], order_id, "CANCELLED").status_code == 200
    assert remaining_credits(client, customer["headers"]) == 10


# ---------- Sahte QR ----------


def _ready_order(client: TestClient, customer: dict, owner: dict, shop: Shop) -> dict:
    subscribe(client, customer["headers"], "STARTER")
    order = place_order(client, customer["headers"], shop).json()["data"]
    for status in ("ACCEPTED", "PREPARING", "READY"):
        set_status(client, owner["headers"], order["id"], status)
    return order


def test_tampered_qr_is_rejected(client: TestClient, customer: dict, owner: dict, karakoy: Shop) -> None:
    order = _ready_order(client, customer, owner, karakoy)
    tampered = {**order["qr"]["payload"], "user_id": "baska-biri"}

    response = client.post(
        f"{ORDERS}/verify-qr", headers=owner["headers"], json={"qr_content": json.dumps(tampered)}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "QR_SIGNATURE_INVALID"
    assert "sahte" in response.json()["error"]["message"]


def test_forged_signature_is_rejected(client: TestClient, customer: dict, owner: dict, karakoy: Shop) -> None:
    order = _ready_order(client, customer, owner, karakoy)
    forged = {**order["qr"]["payload"], "signature": "a" * 64}

    response = set_status(client, owner["headers"], order["id"], "COMPLETED", json.dumps(forged))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "QR_SIGNATURE_INVALID"


def test_qr_payload_object_is_accepted_too(
    client: TestClient, customer: dict, owner: dict, karakoy: Shop
) -> None:
    """Swagger'da test kolaylığı: metin yerine payload nesnesi de gönderilebilir."""
    order = _ready_order(client, customer, owner, karakoy)

    response = set_status(client, owner["headers"], order["id"], "COMPLETED")  # QR yok → hata
    assert response.json()["error"]["code"] == "QR_REQUIRED"
    response = client.patch(
        f"{ORDERS}/{order['id']}/status",
        headers=owner["headers"],
        json={"status": "COMPLETED", "qr_content": order["qr"]["payload"]},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "COMPLETED"


def test_garbage_qr_content(client: TestClient, owner: dict) -> None:
    response = client.post(f"{ORDERS}/verify-qr", headers=owner["headers"], json={"qr_content": "merhaba"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "QR_INVALID_FORMAT"


def test_qr_scanned_at_wrong_shop(
    client: TestClient, customer: dict, owner: dict, karakoy: Shop, set_role, db: Session
) -> None:
    order = _ready_order(client, customer, owner, karakoy)
    other = register_and_login(client, "5553334455")
    set_role(other["user"]["id"], UserRole.SHOP_OWNER)

    response = client.post(
        f"{ORDERS}/verify-qr",
        headers=auth_header(other["access_token"]),
        json={"qr_content": order["qr"]["content"]},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "QR_WRONG_SHOP"


def test_verify_before_ready_is_valid_but_not_completable(
    client: TestClient, customer: dict, owner: dict, karakoy: Shop
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    order = place_order(client, customer["headers"], karakoy).json()["data"]

    data = client.post(
        f"{ORDERS}/verify-qr", headers=owner["headers"], json={"qr_content": order["qr"]["content"]}
    ).json()["data"]

    assert data["valid"] is True
    assert data["can_complete"] is False


# ---------- Favori sipariş tekrarı ----------


def test_reorder_copies_customizations_and_consumes_credit(
    client: TestClient, customer: dict, karakoy: Shop
) -> None:
    subscribe(client, customer["headers"], "STARTER")
    original = place_order(client, customer["headers"], karakoy, size="S", milk="ALMOND").json()["data"]

    response = client.post(f"{ORDERS}/{original['id']}/reorder", headers=customer["headers"])

    assert response.status_code == 201
    again = response.json()["data"]
    assert again["id"] != original["id"]
    assert (again["items"][0]["size"], again["items"][0]["milk"]) == ("S", "ALMOND")
    assert remaining_credits(client, customer["headers"]) == 8
