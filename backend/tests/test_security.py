"""Güvenlik önlemleri: rate limiting, güvenlik başlıkları, üretimde gizli anahtar zorunluluğu."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.rate_limit import limiter

STRONG_JWT = "j" * 48
STRONG_QR = "q" * 48


@pytest.fixture
def rate_limited(monkeypatch):
    """Testlerde kapalı olan rate limit'i bu test için düşük bir limitle aç."""
    limiter.reset()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 3)
    yield
    limiter.reset()


@pytest.mark.usefixtures("rate_limited")
def test_auth_endpoints_are_rate_limited(client: TestClient) -> None:
    for _ in range(3):
        assert client.post("/api/v1/auth/register", json={"phone_number": "5551112233"}).status_code == 200

    response = client.post("/api/v1/auth/register", json={"phone_number": "5551112233"})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert int(response.headers["Retry-After"]) > 0


@pytest.mark.usefixtures("rate_limited")
def test_rate_limit_does_not_affect_other_endpoints(client: TestClient) -> None:
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"phone_number": "5551112233"})

    assert client.get("/api/v1/health").status_code == 200


def test_security_headers_are_set(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"


def test_cors_allows_only_configured_frontend(client: TestClient) -> None:
    allowed = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    blocked = client.get("/api/v1/health", headers={"Origin": "https://kotu-site.example"})

    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in blocked.headers


@pytest.mark.parametrize(
    ("jwt_secret", "qr_secret"),
    [
        (None, None),  # varsayılan geliştirme anahtarları
        ("buraya-uzun-rastgele-bir-deger-yazin", STRONG_QR),  # .env.example yer tutucusu
        ("kisa", STRONG_QR),  # çok kısa
        (STRONG_JWT, STRONG_JWT),  # iki anahtar aynı
    ],
)
def test_production_refuses_weak_secrets(jwt_secret: str | None, qr_secret: str | None) -> None:
    overrides = {"environment": "production", "_env_file": None}
    if jwt_secret:
        overrides["jwt_secret_key"] = jwt_secret
    if qr_secret:
        overrides["qr_signing_secret"] = qr_secret

    with pytest.raises(ValidationError):
        Settings(**overrides)


def test_production_accepts_strong_secrets() -> None:
    production = Settings(
        environment="production", jwt_secret_key=STRONG_JWT, qr_signing_secret=STRONG_QR, _env_file=None
    )

    assert not production.uses_dev_secrets
