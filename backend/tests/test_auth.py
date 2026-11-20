"""Case 3.1 + 7.1: GSM ile kayıt, OTP doğrulama, token yenileme, çıkış."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import OtpRequest
from app.schemas.auth import normalize_tr_gsm
from tests.conftest import auth_header, register_and_login

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
VERIFY = "/api/v1/auth/verify-otp"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/users/me"


# ---------- Telefon numarası (unit) ----------


@pytest.mark.parametrize(
    "raw",
    ["5551234567", "05551234567", "+905551234567", "+90 555 123 45 67", "0555-123-45-67"],
)
def test_phone_formats_are_normalized(raw: str) -> None:
    assert normalize_tr_gsm(raw) == "5551234567"


@pytest.mark.parametrize("raw", ["123", "4551234567", "55512345678", "abc"])
def test_invalid_phone_is_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_tr_gsm(raw)


# ---------- Kayıt ve doğrulama ----------


def test_register_sends_otp_in_standard_format(client: TestClient) -> None:
    response = client.post(REGISTER, json={"phone_number": "0555 111 22 33"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["phone_number"] == "5551112233"
    assert body["data"]["expires_in_seconds"] == 300


def test_invalid_phone_returns_validation_error(client: TestClient) -> None:
    response = client.post(REGISTER, json={"phone_number": "123"})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["field"] == "phone_number"


def test_full_registration_flow_returns_tokens(client: TestClient) -> None:
    data = register_and_login(client)

    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "CUSTOMER"
    # İlk girişte profil boş → frontend profil tamamlama ekranını açacak.
    assert data["is_profile_complete"] is False


def test_wrong_otp_is_rejected_and_attempts_are_counted(client: TestClient) -> None:
    client.post(REGISTER, json={"phone_number": "5551112233"})

    response = client.post(VERIFY, json={"phone_number": "5551112233", "code": "0000"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OTP_INVALID"
    assert response.json()["error"]["details"]["remaining_attempts"] == 4


def test_otp_is_locked_after_max_attempts(client: TestClient) -> None:
    client.post(REGISTER, json={"phone_number": "5551112233"})
    for _ in range(5):
        client.post(VERIFY, json={"phone_number": "5551112233", "code": "0000"})

    # 5 hatadan sonra doğru kod bile kabul edilmez.
    response = client.post(VERIFY, json={"phone_number": "5551112233", "code": "1234"})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "OTP_TOO_MANY_ATTEMPTS"


def test_otp_can_be_used_only_once(client: TestClient) -> None:
    register_and_login(client)

    response = client.post(VERIFY, json={"phone_number": "5551112233", "code": "1234"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OTP_EXPIRED"


def test_expired_otp_is_rejected(client: TestClient, db: Session) -> None:
    client.post(REGISTER, json={"phone_number": "5551112233"})
    db.execute(update(OtpRequest).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    db.commit()

    response = client.post(VERIFY, json={"phone_number": "5551112233", "code": "1234"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OTP_EXPIRED"


def test_verify_without_requesting_code_fails(client: TestClient) -> None:
    response = client.post(VERIFY, json={"phone_number": "5559998877", "code": "1234"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OTP_EXPIRED"


def test_cannot_register_same_phone_twice(client: TestClient) -> None:
    register_and_login(client)

    response = client.post(REGISTER, json={"phone_number": "5551112233"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PHONE_ALREADY_REGISTERED"


def test_unverified_user_can_request_register_again(client: TestClient) -> None:
    # Kod gelmedi / süresi doldu senaryosu: aynı numarayla tekrar kayıt denenebilmeli.
    client.post(REGISTER, json={"phone_number": "5551112233"})

    response = client.post(REGISTER, json={"phone_number": "5551112233"})

    assert response.status_code == 200


# ---------- Giriş (kayıtlı kullanıcı) ----------


def test_login_for_registered_user(client: TestClient) -> None:
    register_and_login(client)

    assert client.post(LOGIN, json={"phone_number": "5551112233"}).status_code == 200
    response = client.post(VERIFY, json={"phone_number": "5551112233", "code": "1234"})

    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


def test_login_for_unknown_phone_fails(client: TestClient) -> None:
    response = client.post(LOGIN, json={"phone_number": "5559998877"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


def test_login_for_unverified_user_fails(client: TestClient) -> None:
    client.post(REGISTER, json={"phone_number": "5551112233"})  # kod girilmedi

    response = client.post(LOGIN, json={"phone_number": "5551112233"})

    assert response.status_code == 404


# ---------- Refresh ve çıkış ----------


def test_refresh_returns_new_working_tokens(client: TestClient) -> None:
    tokens = register_and_login(client)

    response = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    new_tokens = response.json()["data"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert client.get(ME, headers=auth_header(new_tokens["access_token"])).status_code == 200


def test_refresh_token_cannot_be_reused(client: TestClient) -> None:
    tokens = register_and_login(client)
    new_tokens = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]}).json()["data"]

    # Eski token tekrar kullanılırsa (çalınma şüphesi) reddedilir...
    reuse = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "REFRESH_TOKEN_REVOKED"

    # ...ve güvenlik için o kullanıcının tüm oturumları kapanır.
    after = client.post(REFRESH, json={"refresh_token": new_tokens["refresh_token"]})
    assert after.status_code == 401


def test_unknown_refresh_token_is_rejected(client: TestClient) -> None:
    response = client.post(REFRESH, json={"refresh_token": "uydurma-token"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    tokens = register_and_login(client)

    assert client.post(LOGOUT, json={"refresh_token": tokens["refresh_token"]}).status_code == 200
    response = client.post(REFRESH, json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401
