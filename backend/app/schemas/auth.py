import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.schemas.user import UserResponse

_TR_GSM_PATTERN = re.compile(r"^5\d{9}$")


def normalize_tr_gsm(value: str) -> str:
    """Türk GSM numarasını tek biçime çevirir: '0555 123 45 67', '+905551234567' → '5551234567'."""
    digits = re.sub(r"\D", "", value)
    if digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if not _TR_GSM_PATTERN.match(digits):
        raise ValueError("Geçerli bir GSM numarası girin (örn: 5551234567).")
    return digits


PhoneNumber = Annotated[
    str,
    Field(examples=["5551234567"], description="Türk GSM numarası, 5 ile başlayan 10 hane"),
    AfterValidator(normalize_tr_gsm),
]


class PhoneRequest(BaseModel):
    phone_number: PhoneNumber


class VerifyOtpRequest(BaseModel):
    phone_number: PhoneNumber
    code: str = Field(pattern=r"^\d{4}$", examples=["1234"], description="SMS ile gelen 4 haneli kod")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class OtpSentResponse(BaseModel):
    phone_number: str
    expires_in_seconds: int
    message: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int  # access token'ın ömrü


class LoginResponse(TokenResponse):
    user: UserResponse
    # True ise frontend "profil tamamlama" ekranını açar (case 7.1, adım 4).
    is_profile_complete: bool
