from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserPreferences(BaseModel):
    coffee_types: list[str] = Field(default_factory=list, examples=[["latte", "turk_kahvesi"]])
    allergens: list[str] = Field(default_factory=list, examples=[["laktoz"]])


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone_number: str
    full_name: str | None
    email: str | None
    role: UserRole
    preferences: UserPreferences | None
    is_profile_complete: bool
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    """Sadece gönderilen alanlar güncellenir (PATCH)."""

    model_config = ConfigDict(extra="forbid")  # role gibi alanları kullanıcı kendisi değiştiremez

    full_name: str | None = Field(default=None, min_length=2, max_length=100, examples=["Ayşe Yılmaz"])
    email: EmailStr | None = Field(default=None, examples=["ayse@example.com"])
    preferences: UserPreferences | None = None


class UpdateRoleRequest(BaseModel):
    role: UserRole


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    offset: int
    limit: int
