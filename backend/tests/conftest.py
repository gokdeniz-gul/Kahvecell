"""Test ayarları: her test boş, bellekte çalışan ayrı bir veritabanıyla başlar.

Gerçek kahvecell.db dosyasına asla dokunulmaz.
"""

import os

# app içe aktarılmadan ÖNCE ayarlanmalı: ayarlar import anında okunuyor.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-en-az-32-karakter-uzunlukta"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Plan, User  # noqa: E402
from app.models.enums import PlanType, UserRole  # noqa: E402

# StaticPool: bellekteki veritabanı tek bağlantıda yaşar, böylece tüm istekler aynı veriyi görür.
test_engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db() -> Iterator[Session]:
    Base.metadata.create_all(test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(test_engine)


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def _get_test_db() -> Iterator[Session]:
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_and_login(client: TestClient, phone: str = "5551112233") -> dict:
    """Kayıt + OTP doğrulama yapar, verify-otp cevabının data kısmını döner."""
    assert client.post("/api/v1/auth/register", json={"phone_number": phone}).status_code == 200
    response = client.post("/api/v1/auth/verify-otp", json={"phone_number": phone, "code": "1234"})
    assert response.status_code == 200, response.json()
    return response.json()["data"]


def auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def set_role(db: Session):
    """Bir kullanıcının rolünü doğrudan veritabanında değiştirir (API'den admin olunamaz)."""

    def _set_role(user_id: str, role: UserRole) -> None:
        user = db.get(User, user_id)
        user.role = role
        db.commit()

    return _set_role


@pytest.fixture
def make_admin(set_role):
    return lambda user_id: set_role(user_id, UserRole.ADMIN)


@pytest.fixture
def plans(db: Session) -> None:
    """Case 3.2'deki üç paket."""
    db.add_all(
        [
            Plan(plan_type=PlanType.STARTER, name="Starter", monthly_price_kurus=8999,
                 monthly_credits=10, guest_passes=0, has_priority=False),
            Plan(plan_type=PlanType.PREMIUM, name="Premium", monthly_price_kurus=14999,
                 monthly_credits=20, guest_passes=2, has_priority=False),
            Plan(plan_type=PlanType.UNLIMITED, name="Unlimited", monthly_price_kurus=24999,
                 monthly_credits=None, guest_passes=5, has_priority=True),
        ]
    )
    db.commit()
