"""/api/v1 altındaki tüm endpoint grupları burada toplanır."""

from fastapi import APIRouter

from app.api.v1 import auth, users
from app.schemas.common import ApiResponse, MessageData, ok

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)


@api_router.get("/health", tags=["Health"], summary="Sunucu ayakta mı?")
def health() -> ApiResponse[MessageData]:
    return ok(MessageData(message="KahveCell API çalışıyor."))
