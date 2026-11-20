"""Uygulama ayarları: değerler .env dosyasından (yoksa varsayılanlardan) okunur."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Bu değerler herkese açık repoda yazılı; sadece geliştirmede kullanılabilir.
_DEV_JWT_SECRET = "dev-secret-sadece-gelistirme-icin-degistir"
_DEV_QR_SECRET = "dev-qr-secret-sadece-gelistirme-icin-degistir"
_MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "KahveCell API"
    environment: str = "development"  # development | production
    database_url: str = "sqlite:///./kahvecell.db"

    # İzin verilen frontend adresleri (CORS). Virgülle ayrılır.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- JWT ---
    # Üretimde mutlaka uzun ve rastgele bir değerle .env'den verilmeli.
    jwt_secret_key: str = _DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    # Access token kısa ömürlü: çalınırsa zarar süresi kısa olsun.
    access_token_expire_minutes: int = 15
    # Refresh token uzun ömürlü: kullanıcı her seferinde OTP girmesin.
    refresh_token_expire_days: int = 30

    # --- SMS OTP simülasyonu ---
    otp_simulation_code: str = "1234"
    otp_expire_minutes: int = 5
    otp_max_attempts: int = 5

    # --- QR kod imzası (HMAC-SHA256) ---
    # JWT anahtarından ayrı: biri sızarsa diğeri güvende kalır.
    qr_signing_secret: str = _DEV_QR_SECRET

    # --- Rate limiting (aynı IP'den dakikada en fazla istek) ---
    rate_limit_enabled: bool = True
    auth_rate_limit_per_minute: int = 10  # SMS kodu / token istekleri
    payment_rate_limit_per_minute: int = 10

    # --- Abonelik ---
    subscription_period_days: int = 30

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def uses_dev_secrets(self) -> bool:
        """Varsayılan anahtar ya da .env.example'daki "buraya-..." yer tutucusu mu kullanılıyor?"""
        return any(
            secret in (_DEV_JWT_SECRET, _DEV_QR_SECRET) or secret.startswith("buraya-")
            for secret in (self.jwt_secret_key, self.qr_signing_secret)
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _require_real_secrets_outside_development(self) -> "Settings":
        """Repo herkese açık: varsayılan anahtarlarla üretimde açılırsa herkes sahte token/QR üretebilir."""
        if self.is_development:
            return self
        if self.uses_dev_secrets:
            raise ValueError(
                "Üretim ortamında JWT_SECRET_KEY ve QR_SIGNING_SECRET .env üzerinden verilmeli."
            )
        if min(len(self.jwt_secret_key), len(self.qr_signing_secret)) < _MIN_SECRET_LENGTH:
            raise ValueError(f"Gizli anahtarlar en az {_MIN_SECRET_LENGTH} karakter olmalı.")
        if self.jwt_secret_key == self.qr_signing_secret:
            raise ValueError("JWT_SECRET_KEY ve QR_SIGNING_SECRET farklı olmalı.")
        return self


settings = Settings()
