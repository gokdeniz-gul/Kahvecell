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
from app.core.database import Base, engine
from app.core.exceptions import register_exception_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)


logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Uygulama açılırken: eksik tabloları oluştur. Var olan tablolara dokunmaz.
    Base.metadata.create_all(bind=engine)
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


register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
