from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.core.rate_limit import auth_rate_limit
from app.schemas.auth import (
    LoginResponse,
    OtpSentResponse,
    PhoneRequest,
    RefreshRequest,
    TokenResponse,
    VerifyOtpRequest,
)
from app.schemas.common import ApiResponse, MessageData, ok
from app.services.auth_service import AuthService

# Tüm auth endpoint'leri IP başına dakikada sınırlı (SMS bombardımanı ve kaba kuvvet denemesine karşı).
router = APIRouter(prefix="/auth", tags=["Auth"], dependencies=[Depends(auth_rate_limit)])


@router.post("/register", summary="1a. Yeni kullanıcı: GSM ile kayıt, SMS kodu gönder")
def register(body: PhoneRequest, db: DbSession) -> ApiResponse[OtpSentResponse]:
    return ok(AuthService(db).request_registration_otp(body.phone_number))


@router.post("/login", summary="1b. Kayıtlı kullanıcı: giriş için SMS kodu gönder")
def login(body: PhoneRequest, db: DbSession) -> ApiResponse[OtpSentResponse]:
    return ok(AuthService(db).request_login_otp(body.phone_number))


@router.post("/verify-otp", summary="2. SMS kodunu doğrula, token'ları al")
def verify_otp(body: VerifyOtpRequest, db: DbSession) -> ApiResponse[LoginResponse]:
    return ok(AuthService(db).verify_otp(body.phone_number, body.code))


@router.post("/refresh", summary="3. Access token süresi dolunca yenisini al")
def refresh(body: RefreshRequest, db: DbSession) -> ApiResponse[TokenResponse]:
    return ok(AuthService(db).refresh(body.refresh_token))


@router.post("/logout", summary="4. Çıkış: refresh token'ı iptal et")
def logout(body: RefreshRequest, db: DbSession) -> ApiResponse[MessageData]:
    AuthService(db).logout(body.refresh_token)
    return ok(MessageData(message="Çıkış yapıldı."))
