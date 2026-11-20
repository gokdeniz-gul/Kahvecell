"""Tüm endpoint'lerin ortak cevap zarfı: { success, data, error } (case bölüm 4.4)."""

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str  # Frontend'in kontrol edeceği sabit kod, örn: "OTP_INVALID"
    message: str  # Kullanıcıya gösterilebilecek Türkçe açıklama
    details: Any | None = None  # Örn: hangi form alanı hatalı


class ApiResponse[T](BaseModel):
    success: bool
    data: T | None = None
    error: ErrorDetail | None = None


class MessageData(BaseModel):
    message: str


def ok[T](data: T) -> ApiResponse[T]:
    return ApiResponse[T](success=True, data=data)
