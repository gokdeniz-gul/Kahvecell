"""Uygulama ayarları: değerler .env dosyasından (yoksa varsayılanlardan) okunur."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "KahveCell API"
    environment: str = "development"
    database_url: str = "sqlite:///./kahvecell.db"

    # İzin verilen frontend adresleri (CORS). Virgülle ayrılır.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- JWT ---
    # Üretimde mutlaka uzun ve rastgele bir değerle .env'den verilmeli.
    jwt_secret_key: str = "dev-secret-sadece-gelistirme-icin-degistir"
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
    qr_signing_secret: str = "dev-qr-secret-sadece-gelistirme-icin-degistir"

    # --- Abonelik ---
    subscription_period_days: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
