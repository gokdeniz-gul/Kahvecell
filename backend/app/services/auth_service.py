"""Kayıt, OTP doğrulama ve oturum (token) yönetimi — case 3.1 ve 7.1.

Akış:
  1. register (yeni numara) veya login (kayıtlı numara) → SMS kodu "gönderilir"
  2. verify-otp → kod doğruysa access + refresh token döner
  3. access token süresi dolunca refresh ile yenisi alınır (kullanıcıya tekrar OTP sorulmaz)
  4. logout → refresh token iptal edilir
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hashes_match,
    sha256_hex,
)
from app.models import User
from app.repositories.otp_repository import OtpRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginResponse, OtpSentResponse, TokenResponse
from app.schemas.user import UserResponse
from app.services.sms_service import SimulatedSmsSender


class AuthService:
    def __init__(self, db: Session, sms_sender: SimulatedSmsSender | None = None) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.otps = OtpRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.sms = sms_sender or SimulatedSmsSender()

    # ---------- 1. Kod isteme ----------

    def request_registration_otp(self, phone_number: str) -> OtpSentResponse:
        user = self.users.get_by_phone(phone_number)
        if user is not None and user.is_phone_verified:
            raise ConflictError(
                "Bu numara zaten kayıtlı. Lütfen giriş yapın.", code="PHONE_ALREADY_REGISTERED"
            )
        if user is None:
            # Numara doğrulanana kadar kullanıcı "doğrulanmamış" kalır ve giriş yapamaz.
            self.users.create(phone_number)
        return self._send_otp(phone_number)

    def request_login_otp(self, phone_number: str) -> OtpSentResponse:
        user = self.users.get_by_phone(phone_number)
        if user is None or not user.is_phone_verified:
            raise NotFoundError(
                "Bu numarayla kayıtlı kullanıcı yok. Önce kayıt olun.", code="USER_NOT_FOUND"
            )
        return self._send_otp(phone_number)

    def _send_otp(self, phone_number: str) -> OtpSentResponse:
        now = datetime.now(UTC)
        # Yeni kod istenince eski kodlar geçersiz olur.
        self.otps.consume_all_active(phone_number, now)

        code = settings.otp_simulation_code  # Gerçek sistemde burada rastgele kod üretilir.
        expires_in = settings.otp_expire_minutes * 60
        self.otps.create(phone_number, sha256_hex(code), now + timedelta(seconds=expires_in))
        self.db.commit()

        self.sms.send_otp(phone_number, code)
        return OtpSentResponse(
            phone_number=phone_number,
            expires_in_seconds=expires_in,
            message=f"Doğrulama kodu SMS ile gönderildi. (Simülasyon: kod {code})",
        )

    # ---------- 2. Kodu doğrulama ----------

    def verify_otp(self, phone_number: str, code: str) -> LoginResponse:
        now = datetime.now(UTC)
        otp = self.otps.get_latest_active(phone_number)

        if otp is None or otp.expires_at <= now:
            raise BadRequestError(
                "Kodun süresi dolmuş ya da kod istenmemiş. Yeni kod isteyin.", code="OTP_EXPIRED"
            )
        if otp.attempts >= settings.otp_max_attempts:
            raise TooManyRequestsError(
                "Çok fazla hatalı deneme. Yeni kod isteyin.", code="OTP_TOO_MANY_ATTEMPTS"
            )
        if not hashes_match(code, otp.code_hash):
            otp.attempts += 1
            self.db.commit()
            raise BadRequestError(
                "Doğrulama kodu hatalı.",
                code="OTP_INVALID",
                details={"remaining_attempts": settings.otp_max_attempts - otp.attempts},
            )

        user = self.users.get_by_phone(phone_number)
        if user is None:  # register/login adımı atlanmış olamaz ama yine de koruyalım
            raise NotFoundError("Kullanıcı bulunamadı.", code="USER_NOT_FOUND")

        otp.consumed_at = now  # Kod bir kez kullanılır.
        user.is_phone_verified = True
        tokens = self._issue_tokens(user, now)
        self.db.commit()

        return LoginResponse(
            **tokens.model_dump(),
            user=UserResponse.model_validate(user),
            is_profile_complete=user.is_profile_complete,
        )

    # ---------- 3. Oturumu yenileme / kapatma ----------

    def refresh(self, refresh_token: str) -> TokenResponse:
        now = datetime.now(UTC)
        record = self.refresh_tokens.get_by_hash(sha256_hex(refresh_token))

        if record is None:
            raise UnauthorizedError("Geçersiz oturum. Tekrar giriş yapın.", code="REFRESH_TOKEN_INVALID")
        if record.revoked_at is not None:
            # Zaten kullanılmış bir token tekrar geldi: çalınmış olabilir.
            # Güvenlik için kullanıcının tüm oturumlarını kapatıyoruz.
            self.refresh_tokens.revoke_all_for_user(record.user_id, now)
            self.db.commit()
            raise UnauthorizedError("Oturum geçersiz. Tekrar giriş yapın.", code="REFRESH_TOKEN_REVOKED")
        if record.expires_at <= now:
            raise UnauthorizedError("Oturum süresi doldu. Tekrar giriş yapın.", code="REFRESH_TOKEN_EXPIRED")

        # Rotation: her refresh token tek kullanımlık; eskisini kapatıp yenisini veriyoruz.
        record.revoked_at = now
        tokens = self._issue_tokens(record.user, now)
        self.db.commit()
        return tokens

    def logout(self, refresh_token: str) -> None:
        record = self.refresh_tokens.get_by_hash(sha256_hex(refresh_token))
        if record is not None and record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
            self.db.commit()

    def _issue_tokens(self, user: User, now: datetime) -> TokenResponse:
        refresh_token = generate_refresh_token()
        self.refresh_tokens.create(
            user_id=user.id,
            token_hash=sha256_hex(refresh_token),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
        return TokenResponse(
            access_token=create_access_token(user.id, user.role.value),
            refresh_token=refresh_token,
            expires_in_seconds=settings.access_token_expire_minutes * 60,
        )
