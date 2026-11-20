"""Uygulamanın kendi hata sınıfları ve hepsini { success: false, error } formatına çeviren handler'lar.

Servis katmanı HTTP bilmez; sadece "NotFoundError" gibi anlamlı bir hata fırlatır.
Burada o hata, doğru HTTP durum koduna ve standart cevap formatına çevrilir.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ApiResponse, ErrorDetail

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "BAD_REQUEST"
    message: str = "İstek işlenemedi."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class BadRequestError(AppError):
    pass


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"
    message = "Bu işlem için giriş yapmalısınız."


class PaymentRequiredError(AppError):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    code = "PAYMENT_REQUIRED"
    message = "Ödeme gerekli."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    message = "Bu işlem için yetkiniz yok."


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    message = "Kayıt bulunamadı."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "Kayıt zaten mevcut."


class TooManyRequestsError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "TOO_MANY_REQUESTS"
    message = "Çok fazla deneme yapıldı."


def _error_response(
    status_code: int, code: str, message: str, details: Any = None, headers: dict | None = None
) -> JSONResponse:
    body = ApiResponse[None](
        success=False, error=ErrorDetail(code=code, message=message, details=details)
    )
    return JSONResponse(
        status_code=status_code, content=jsonable_encoder(body), headers=headers
    )


async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    headers = dict(exc.headers or {})
    if isinstance(exc, UnauthorizedError):
        headers["WWW-Authenticate"] = "Bearer"
    return _error_response(exc.status_code, exc.code, exc.message, exc.details, headers or None)


async def _validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic hatalarını sade bir listeye çeviriyoruz: [{ field, message }]
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "VALIDATION_ERROR",
        "Gönderilen bilgiler geçersiz.",
        details,
    )


async def _http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Örn: olmayan bir adres (404) veya yanlış HTTP metodu (405)
    return _error_response(exc.status_code, f"HTTP_{exc.status_code}", str(exc.detail))


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Beklenmeyen hata: detay (stack trace) istek kimliğiyle birlikte loglara yazılır
    # (logging.py'deki middleware); kullanıcıya iç bilgi sızdırılmaz, sadece destek için kimlik verilir.
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:  # middleware dışında kalan nadir durumlar
        logger.exception("Beklenmeyen hata: %s %s", request.method, request.url.path)
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR",
        "Beklenmeyen bir hata oluştu.",
        {"request_id": request_id} if request_id else None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
