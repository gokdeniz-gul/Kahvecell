"""Endpoint'lerin ortak bağımlılıkları: veritabanı oturumu, giriş yapmış kullanıcı, rol kontrolü."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models import User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository

# auto_error=False: token yoksa FastAPI'nin kendi hatası yerine bizim standart hatamız dönsün.
# Swagger'daki "Authorize" düğmesi de bu tanım sayesinde çıkar.
_bearer_scheme = HTTPBearer(auto_error=False, description="verify-otp'den dönen access_token")

DbSession = Annotated[Session, Depends(get_db)]


def _user_from_token(db: Session, token: str) -> User:
    payload = decode_access_token(token)
    user = UserRepository(db).get_by_id(payload["sub"])
    if user is None or not user.is_phone_verified:
        raise UnauthorizedError("Kullanıcı bulunamadı.", code="TOKEN_INVALID")
    # Rolü token'dan değil veritabanından okuyoruz: admin rolü değiştirirse hemen geçerli olur.
    return user


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> User:
    if credentials is None:
        raise UnauthorizedError()
    return _user_from_token(db, credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_user_from_query_token(
    db: DbSession,
    token: Annotated[str, Query(description="Access token (EventSource başlık gönderemediği için adreste)")],
) -> User:
    """SSE bağlantıları için: tarayıcının EventSource'u Authorization başlığı ekleyemiyor."""
    return _user_from_token(db, token)


StreamUser = Annotated[User, Depends(get_user_from_query_token)]


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Kullanım: Depends(require_roles(UserRole.ADMIN))"""

    def checker(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError()
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
ShopStaffUser = Annotated[User, Depends(require_roles(UserRole.SHOP_OWNER, UserRole.ADMIN))]
# Abonelik ve ödeme işlemleri sadece müşterilere açık.
CustomerUser = Annotated[User, Depends(require_roles(UserRole.CUSTOMER))]


def get_clock() -> Callable[[], datetime]:
    """Şu anki zaman. Testlerde "saat 12:00" gibi sabit bir saatle değiştirilebiliyor."""
    return lambda: datetime.now(UTC)


Clock = Annotated[Callable[[], datetime], Depends(get_clock)]
