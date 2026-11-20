"""Endpoint'lerin ortak bağımlılıkları: veritabanı oturumu, giriş yapmış kullanıcı, rol kontrolü."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
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


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> User:
    if credentials is None:
        raise UnauthorizedError()

    payload = decode_access_token(credentials.credentials)
    user = UserRepository(db).get_by_id(payload["sub"])
    if user is None or not user.is_phone_verified:
        raise UnauthorizedError("Kullanıcı bulunamadı.", code="TOKEN_INVALID")
    # Rolü token'dan değil veritabanından okuyoruz: admin rolü değiştirirse hemen geçerli olur.
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Kullanım: Depends(require_roles(UserRole.ADMIN))"""

    def checker(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError()
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
# Abonelik ve ödeme işlemleri sadece müşterilere açık.
CustomerUser = Annotated[User, Depends(require_roles(UserRole.CUSTOMER))]
