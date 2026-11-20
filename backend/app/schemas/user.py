from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import Allergen, CoffeeType, UserRole


def _known_values(enum_cls: type[StrEnum]):
    """Eski/bilinmeyen değerleri sessizce ele: ['latte', 'xyz'] → [LATTE]. Sırayı korur, tekrarları atar."""

    def clean(values: Any) -> list[StrEnum]:
        result: list[StrEnum] = []
        for value in values or []:
            key = str(value).strip().upper()
            if key in enum_cls.__members__ and enum_cls[key] not in result:
                result.append(enum_cls[key])
        return result

    return BeforeValidator(clean)


class UserPreferences(BaseModel):
    """Cevapta: veritabanındaki eski biçimli değerler de okunabilsin diye toleranslı."""

    coffee_types: Annotated[list[CoffeeType], _known_values(CoffeeType)] = Field(default_factory=list)
    allergens: Annotated[list[Allergen], _known_values(Allergen)] = Field(default_factory=list)


class PreferencesInput(BaseModel):
    """İstekte: sadece tanımlı değerler kabul edilir, tekrarlar atılır."""

    model_config = ConfigDict(extra="forbid")

    coffee_types: list[CoffeeType] = Field(default_factory=list, max_length=len(CoffeeType), examples=[["LATTE", "TURKISH"]])
    allergens: list[Allergen] = Field(default_factory=list, max_length=len(Allergen), examples=[["LACTOSE"]])

    @field_validator("coffee_types", "allergens")
    @classmethod
    def _unique(cls, values: list) -> list:
        return list(dict.fromkeys(values))


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
    preferences: PreferencesInput | None = None


class UpdateRoleRequest(BaseModel):
    role: UserRole


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    offset: int
    limit: int
