"""Case 3.2 (abonelik) + 12 (ödeme simülasyonu)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Payment, Subscription
from app.models.enums import UserRole
from tests.conftest import auth_header, register_and_login

PLANS = "/api/v1/subscriptions/plans"
SUBS = "/api/v1/subscriptions"
MY_SUB = "/api/v1/subscriptions/me"
PAY = "/api/v1/payments/process"
MY_PAYMENTS = "/api/v1/payments/me"

SUCCESS_CARD = "4242 4242 4242 4242"
DECLINED_CARD = "4000-0000-0000-0002"

pytestmark = pytest.mark.usefixtures("plans")


def card(number: str = SUCCESS_CARD, **overrides) -> dict:
    return {
        "card_holder": "AYSE YILMAZ",
        "card_number": number,
        "expiry_month": 12,
        "expiry_year": datetime.now(UTC).year + 3,
        "cvc": "123",
        **overrides,
    }


@pytest.fixture
def customer(client: TestClient) -> dict:
    return auth_header(register_and_login(client)["access_token"])


def pay(client: TestClient, headers: dict, plan_type: str, number: str = SUCCESS_CARD):
    return client.post(PAY, headers=headers, json={"plan_type": plan_type, "card": card(number)})


def subscribe(client: TestClient, headers: dict, plan_type: str = "STARTER") -> dict:
    tx = pay(client, headers, plan_type).json()["data"]["transaction_id"]
    response = client.post(SUBS, headers=headers, json={"plan_type": plan_type, "transaction_id": tx})
    assert response.status_code == 201, response.json()
    return response.json()["data"]


def expire_current_period(db: Session) -> None:
    db.execute(update(Subscription).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    db.commit()


# ---------- Paketler ----------


def test_plans_are_public_and_sorted_by_price(client: TestClient) -> None:
    response = client.get(PLANS)

    assert response.status_code == 200
    plans = response.json()["data"]
    assert [p["plan_type"] for p in plans] == ["STARTER", "PREMIUM", "UNLIMITED"]
    assert plans[0]["monthly_price_tl"] == 89.99
    assert plans[0]["monthly_credits"] == 10
    assert plans[2]["is_unlimited"] is True
    assert plans[1]["guest_passes"] == 2


# ---------- Ödeme simülasyonu ----------


def test_successful_payment(client: TestClient, customer: dict) -> None:
    response = pay(client, customer, "STARTER")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "SUCCESS"
    assert data["transaction_id"].startswith("TXN-")
    assert data["amount_kurus"] == 8999
    assert data["amount_tl"] == 89.99
    assert data["card_last4"] == "4242"
    assert data["subscription_id"] is None  # henüz aboneliğe bağlanmadı


def test_declined_payment_returns_402_and_is_recorded(client: TestClient, customer: dict) -> None:
    response = pay(client, customer, "STARTER", DECLINED_CARD)

    assert response.status_code == 402
    error = response.json()["error"]
    assert error["code"] == "PAYMENT_DECLINED"
    assert error["details"]["status"] == "FAILED"

    history = client.get(MY_PAYMENTS, headers=customer).json()["data"]
    assert history["total"] == 1
    assert history["items"][0]["status"] == "FAILED"
    assert history["items"][0]["card_last4"] == "0002"


def test_unknown_card_is_rejected(client: TestClient, customer: dict) -> None:
    response = pay(client, customer, "STARTER", "5555 5555 5555 4444")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_TEST_CARD"


def test_expired_card_fails_validation(client: TestClient, customer: dict) -> None:
    response = client.post(
        PAY, headers=customer, json={"plan_type": "STARTER", "card": card(expiry_year=2020)}
    )

    assert response.status_code == 422


def test_full_card_number_is_never_stored(client: TestClient, customer: dict, db: Session) -> None:
    pay(client, customer, "STARTER")

    payment = db.scalar(select(Payment))
    stored_values = " ".join(str(value) for value in vars(payment).values())
    assert "4242424242424242" not in stored_values


def test_only_customers_can_pay(client: TestClient, set_role) -> None:
    data = register_and_login(client)
    set_role(data["user"]["id"], UserRole.SHOP_OWNER)

    response = pay(client, auth_header(data["access_token"]), "STARTER")

    assert response.status_code == 403


# ---------- Abonelik başlatma ----------


def test_no_subscription_returns_null(client: TestClient, customer: dict) -> None:
    response = client.get(MY_SUB, headers=customer)

    assert response.status_code == 200
    assert response.json()["data"] is None


def test_start_subscription_with_successful_payment(client: TestClient, customer: dict) -> None:
    sub = subscribe(client, customer, "STARTER")

    assert sub["status"] == "ACTIVE"
    assert sub["plan"]["plan_type"] == "STARTER"
    assert sub["remaining_credits"] == 10
    period = datetime.fromisoformat(sub["expires_at"]) - datetime.fromisoformat(sub["started_at"])
    assert period == timedelta(days=30)

    # Transaction ID ↔ abonelik eşleşmesi
    payment = client.get(MY_PAYMENTS, headers=customer).json()["data"]["items"][0]
    assert payment["subscription_id"] == sub["id"]


def test_unlimited_has_no_credit_limit(client: TestClient, customer: dict) -> None:
    sub = subscribe(client, customer, "UNLIMITED")

    assert sub["remaining_credits"] is None
    assert sub["remaining_guest_passes"] == 5


def test_cannot_start_with_failed_payment(client: TestClient, customer: dict) -> None:
    tx = pay(client, customer, "STARTER", DECLINED_CARD).json()["error"]["details"]["transaction_id"]

    response = client.post(SUBS, headers=customer, json={"plan_type": "STARTER", "transaction_id": tx})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PAYMENT_NOT_SUCCESSFUL"


def test_cannot_use_payment_for_another_plan(client: TestClient, customer: dict) -> None:
    tx = pay(client, customer, "STARTER").json()["data"]["transaction_id"]

    response = client.post(SUBS, headers=customer, json={"plan_type": "PREMIUM", "transaction_id": tx})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PAYMENT_MISMATCH"


def test_cannot_use_someone_elses_payment(client: TestClient, customer: dict) -> None:
    tx = pay(client, customer, "STARTER").json()["data"]["transaction_id"]
    other = auth_header(register_and_login(client, "5554445566")["access_token"])

    response = client.post(SUBS, headers=other, json={"plan_type": "STARTER", "transaction_id": tx})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PAYMENT_NOT_FOUND"


def test_cannot_have_two_subscriptions(client: TestClient, customer: dict) -> None:
    subscribe(client, customer, "STARTER")

    # Zaten aboneyken aynı paket için ödeme bile alınmaz.
    response = pay(client, customer, "STARTER")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ALREADY_ON_PLAN"


# ---------- Yükseltme ----------


def test_upgrade_charges_difference_and_adds_credits(
    client: TestClient, customer: dict, db: Session
) -> None:
    subscribe(client, customer, "STARTER")
    db.execute(update(Subscription).values(remaining_credits=7))  # 3 kahve içilmiş
    db.commit()

    payment = pay(client, customer, "PREMIUM").json()["data"]
    assert payment["amount_kurus"] == 14999 - 8999  # sadece fark

    response = client.patch(
        MY_SUB, headers=customer,
        json={"plan_type": "PREMIUM", "transaction_id": payment["transaction_id"]},
    )

    assert response.status_code == 200
    sub = response.json()["data"]
    assert sub["plan"]["plan_type"] == "PREMIUM"
    assert sub["remaining_credits"] == 17  # 7 + (20 - 10)
    assert sub["remaining_guest_passes"] == 2


def test_upgrade_to_unlimited(client: TestClient, customer: dict) -> None:
    subscribe(client, customer, "STARTER")
    tx = pay(client, customer, "UNLIMITED").json()["data"]["transaction_id"]

    sub = client.patch(
        MY_SUB, headers=customer, json={"plan_type": "UNLIMITED", "transaction_id": tx}
    ).json()["data"]

    assert sub["remaining_credits"] is None


def test_upgrade_without_payment_tells_amount(client: TestClient, customer: dict) -> None:
    subscribe(client, customer, "STARTER")

    response = client.patch(MY_SUB, headers=customer, json={"plan_type": "PREMIUM"})

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "PAYMENT_REQUIRED_FOR_UPGRADE"
    assert error["details"]["amount_kurus"] == 6000


def test_full_price_payment_cannot_be_used_for_upgrade(client: TestClient, customer: dict) -> None:
    # Aboneliği yokken Premium'a tam fiyat ödendi, sonra Starter'a abone oldu...
    premium_tx = pay(client, customer, "PREMIUM").json()["data"]["transaction_id"]
    subscribe(client, customer, "STARTER")

    response = client.patch(
        MY_SUB, headers=customer, json={"plan_type": "PREMIUM", "transaction_id": premium_tx}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PAYMENT_MISMATCH"


# ---------- Düşürme ----------


def test_downgrade_is_free_and_applies_next_period(client: TestClient, customer: dict) -> None:
    subscribe(client, customer, "PREMIUM")

    response = client.patch(MY_SUB, headers=customer, json={"plan_type": "STARTER"})

    assert response.status_code == 200
    sub = response.json()["data"]
    assert sub["plan"]["plan_type"] == "PREMIUM"  # bu ay hâlâ Premium
    assert sub["remaining_credits"] == 20
    assert sub["pending_plan"]["plan_type"] == "STARTER"


def test_payment_is_refused_for_downgrade(client: TestClient, customer: dict) -> None:
    subscribe(client, customer, "PREMIUM")

    response = pay(client, customer, "STARTER")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DOWNGRADE_NEEDS_NO_PAYMENT"


def test_choosing_current_plan_cancels_pending_downgrade(client: TestClient, customer: dict) -> None:
    subscribe(client, customer, "PREMIUM")
    client.patch(MY_SUB, headers=customer, json={"plan_type": "STARTER"})

    sub = client.patch(MY_SUB, headers=customer, json={"plan_type": "PREMIUM"}).json()["data"]

    assert sub["pending_plan"] is None


# ---------- İptal ----------


def test_cancel_keeps_credits_until_period_end(client: TestClient, customer: dict) -> None:
    subscribe(client, customer, "STARTER")

    response = client.delete(MY_SUB, headers=customer)

    assert response.status_code == 200
    sub = response.json()["data"]
    assert sub["status"] == "CANCELLED"
    assert sub["cancelled_at"] is not None
    assert sub["remaining_credits"] == 10
    # Hâlâ "aboneliğim" ekranında görünür.
    assert client.get(MY_SUB, headers=customer).json()["data"]["status"] == "CANCELLED"


def test_cannot_cancel_twice_or_change_cancelled(client: TestClient, customer: dict) -> None:
    subscribe(client, customer, "PREMIUM")
    client.delete(MY_SUB, headers=customer)

    assert client.delete(MY_SUB, headers=customer).json()["error"]["code"] == "ALREADY_CANCELLED"
    patch = client.patch(MY_SUB, headers=customer, json={"plan_type": "STARTER"})
    assert patch.json()["error"]["code"] == "SUBSCRIPTION_CANCELLED"


def test_cancel_without_subscription(client: TestClient, customer: dict) -> None:
    response = client.delete(MY_SUB, headers=customer)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NO_ACTIVE_SUBSCRIPTION"


# ---------- Aylık yenileme ----------


def test_monthly_renewal_refills_credits_and_charges(
    client: TestClient, customer: dict, db: Session
) -> None:
    subscribe(client, customer, "STARTER")
    db.execute(update(Subscription).values(remaining_credits=2))
    db.commit()
    expire_current_period(db)

    sub = client.get(MY_SUB, headers=customer).json()["data"]

    assert sub["status"] == "ACTIVE"
    assert sub["remaining_credits"] == 10
    assert datetime.fromisoformat(sub["expires_at"]) > datetime.now(UTC)
    history = client.get(MY_PAYMENTS, headers=customer).json()["data"]
    assert history["total"] == 2  # ilk ödeme + otomatik yenileme


def test_renewal_applies_pending_downgrade(client: TestClient, customer: dict, db: Session) -> None:
    subscribe(client, customer, "PREMIUM")
    client.patch(MY_SUB, headers=customer, json={"plan_type": "STARTER"})
    expire_current_period(db)

    sub = client.get(MY_SUB, headers=customer).json()["data"]

    assert sub["plan"]["plan_type"] == "STARTER"
    assert sub["remaining_credits"] == 10
    assert sub["pending_plan"] is None
    renewal = client.get(MY_PAYMENTS, headers=customer).json()["data"]["items"][0]
    assert renewal["amount_kurus"] == 8999


def test_cancelled_subscription_ends_at_period_end(
    client: TestClient, customer: dict, db: Session
) -> None:
    subscribe(client, customer, "STARTER")
    client.delete(MY_SUB, headers=customer)
    expire_current_period(db)

    assert client.get(MY_SUB, headers=customer).json()["data"] is None
    # Süresi biten aboneliğin yerine yenisi alınabilir.
    assert subscribe(client, customer, "PREMIUM")["plan"]["plan_type"] == "PREMIUM"
