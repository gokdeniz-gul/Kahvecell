"""Uygulamanın giriş noktası. Çalıştırmak için (backend klasöründe):

    uvicorn app.main:app --reload

Swagger dokümantasyonu: http://127.0.0.1:8000/docs
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (modeller Base'e kaydolsun diye içe aktarılıyor)
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import request_context_middleware, setup_logging
from app.core.migrations import upgrade_database

setup_logging(settings.log_format, settings.log_level)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Uygulama açılırken veritabanı şemasını Alembic migration'larıyla en son sürüme getir.
    if settings.auto_migrate:
        upgrade_database()
    if settings.uses_dev_secrets:
        logger.warning("Varsayılan geliştirme anahtarları kullanılıyor; üretimde .env ile değiştirin.")
    yield


app = FastAPI(
    title=settings.app_name,
    description="KahveCell — dijital kahve abonelik platformu API'si.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,  # Sadece bizim frontend adreslerimiz
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",  # tarayıcı dosya türünü tahmin etmesin
    "X-Frame-Options": "DENY",  # sayfa başka sitede iframe içine gömülemesin (clickjacking)
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    if request.url.path.startswith("/api/"):
        # Token ve kişisel veri içeren API cevapları tarayıcı/proxy önbelleğinde kalmasın.
        response.headers["Cache-Control"] = "no-store"
    return response


# En son eklenen middleware en dışta çalışır: istek kimliği her şeyi (hatalar dahil) kapsasın.
app.middleware("http")(request_context_middleware)

register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
