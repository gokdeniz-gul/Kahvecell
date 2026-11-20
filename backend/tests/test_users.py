"""Profil yönetimi ve rol bazlı erişim (Müşteri / Dükkân Sahibi / Admin)."""

from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from tests.conftest import auth_header, register_and_login

ME = "/api/v1/users/me"
USERS = "/api/v1/users"


# ---------- Kimlik doğrulama ----------


def test_me_requires_token(client: TestClient) -> None:
    response = client.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(ME, headers=auth_header("bozuk.token.degeri"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_INVALID"


def test_me_rejects_expired_token(client: TestClient) -> None:
    user_id = register_and_login(client)["user"]["id"]
    expired = create_access_token(user_id, "CUSTOMER", expires_delta=timedelta(seconds=-1))

    response = client.get(ME, headers=auth_header(expired))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_me_returns_current_user(client: TestClient) -> None:
    tokens = register_and_login(client)

    response = client.get(ME, headers=auth_header(tokens["access_token"]))

    assert response.status_code == 200
    assert response.json()["data"]["phone_number"] == "5551112233"


# ---------- Profil tamamlama ----------


def test_complete_profile(client: TestClient) -> None:
    tokens = register_and_login(client)

    response = client.patch(
        ME,
        headers=auth_header(tokens["access_token"]),
        json={
            "full_name": "Ayşe Yılmaz",
            "email": "Ayse@Example.com",
            "preferences": {"coffee_types": ["latte"], "allergens": ["laktoz"]},
        },
    )

    assert response.status_code == 200
    user = response.json()["data"]
    assert user["full_name"] == "Ayşe Yılmaz"
    assert user["email"] == "ayse@example.com"
    assert user["preferences"] == {"coffee_types": ["latte"], "allergens": ["laktoz"]}
    assert user["is_profile_complete"] is True


def test_profile_rejects_invalid_email(client: TestClient) -> None:
    tokens = register_and_login(client)

    response = client.patch(ME, headers=auth_header(tokens["access_token"]), json={"email": "bozuk"})

    assert response.status_code == 422


def test_user_cannot_change_own_role_via_profile(client: TestClient) -> None:
    tokens = register_and_login(client)

    response = client.patch(ME, headers=auth_header(tokens["access_token"]), json={"role": "ADMIN"})

    assert response.status_code == 422


def test_email_must_be_unique(client: TestClient) -> None:
    first = register_and_login(client, "5551112233")
    second = register_and_login(client, "5554445566")
    client.patch(ME, headers=auth_header(first["access_token"]), json={"email": "ortak@example.com"})

    response = client.patch(
        ME, headers=auth_header(second["access_token"]), json={"email": "ORTAK@example.com"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_IN_USE"


# ---------- Rol bazlı erişim ----------


def test_customer_cannot_access_admin_endpoints(client: TestClient) -> None:
    tokens = register_and_login(client)

    response = client.get(USERS, headers=auth_header(tokens["access_token"]))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_list_users_and_change_roles(client: TestClient, make_admin) -> None:
    admin = register_and_login(client, "5550000000")
    customer = register_and_login(client, "5551112233")
    make_admin(admin["user"]["id"])
    headers = auth_header(admin["access_token"])

    listing = client.get(USERS, headers=headers)
    assert listing.status_code == 200
    assert listing.json()["data"]["total"] == 2

    response = client.patch(
        f"{USERS}/{customer['user']['id']}/role", headers=headers, json={"role": "SHOP_OWNER"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "SHOP_OWNER"

    # Rol veritabanından okunduğu için müşterinin eski token'ı da yeni rolü görür.
    me = client.get(ME, headers=auth_header(customer["access_token"]))
    assert me.json()["data"]["role"] == "SHOP_OWNER"


def test_admin_cannot_change_own_role(client: TestClient, make_admin) -> None:
    admin = register_and_login(client, "5550000000")
    make_admin(admin["user"]["id"])

    response = client.patch(
        f"{USERS}/{admin['user']['id']}/role",
        headers=auth_header(admin["access_token"]),
        json={"role": "CUSTOMER"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CANNOT_CHANGE_OWN_ROLE"


def test_change_role_of_unknown_user(client: TestClient, make_admin) -> None:
    admin = register_and_login(client, "5550000000")
    make_admin(admin["user"]["id"])

    response = client.patch(
        f"{USERS}/olmayan-id/role",
        headers=auth_header(admin["access_token"]),
        json={"role": "CUSTOMER"},
    )

    assert response.status_code == 404


def test_unknown_route_uses_standard_error_format(client: TestClient) -> None:
    response = client.get("/api/v1/olmayan-adres")

    assert response.status_code == 404
    assert response.json()["success"] is False
