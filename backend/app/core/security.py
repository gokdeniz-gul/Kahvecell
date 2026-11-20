"""Token üretme/doğrulama ve özet (hash) yardımcıları."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

ACCESS_TOKEN_TYPE = "access"


def create_access_token(user_id: str, role: str, expires_delta: timedelta | None = None) -> str:
    """Kısa ömürlü JWT. İçinde kim olduğu (sub) ve rolü yazar, gizli anahtarla imzalanır."""
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": user_id, "role": role, "type": ACCESS_TOKEN_TYPE, "iat": now, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Oturum süresi doldu.", code="TOKEN_EXPIRED") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Geçersiz token.", code="TOKEN_INVALID") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE or not payload.get("sub"):
        raise UnauthorizedError("Geçersiz token.", code="TOKEN_INVALID")
    return payload


def generate_refresh_token() -> str:
    """Refresh token JWT değil, tahmin edilemez rastgele bir metin. Veritabanında takip edilir."""
    return secrets.token_urlsafe(48)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hashes_match(plain: str, expected_hash: str) -> bool:
    # compare_digest: karşılaştırma süresinden bilgi sızmasını (timing attack) engeller.
    return hmac.compare_digest(sha256_hex(plain), expected_hash)
