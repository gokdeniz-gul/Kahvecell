from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import Clock, CurrentUser, CustomerUser, DbSession, ShopStaffUser, StreamUser
from app.core.config import settings
from app.core.events import sse_stream
from app.core.exceptions import ForbiddenError
from app.models.enums import UserRole
from app.repositories.order_repository import OrderRepository
from app.models.enums import OrderStatus
from app.schemas.common import ApiResponse, ok
from app.schemas.order import (
    CreateOrderRequest,
    OrderListResponse,
    OrderResponse,
    ShopDailyStats,
    UpdateOrderStatusRequest,
    VerifyQrRequest,
    VerifyQrResponse,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])

Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="[Müşteri] Sipariş ver: abonelik hakkından 1 düşer, imzalı QR üretilir",
)
def create_order(
    body: CreateOrderRequest, user: CustomerUser, db: DbSession, clock: Clock
) -> ApiResponse[OrderResponse]:
    return ok(OrderService(db, clock).create(user, body))


@router.get("/history", summary="[Müşteri] Sipariş geçmişim (en yeni en üstte)")
def order_history(
    user: CurrentUser, db: DbSession, offset: Offset = 0, limit: Limit = 20
) -> ApiResponse[OrderListResponse]:
    return ok(OrderService(db).history(user, offset=offset, limit=limit))


@router.get(
    "/incoming",
    summary="[Dükkân] Dükkânıma gelen siparişler (öncelikli aboneler önce)",
    description="`status` boş bırakılırsa teslim edilmemiş tüm aktif siparişler gelir.",
)
def incoming_orders(
    user: ShopStaffUser,
    db: DbSession,
    shop_id: Annotated[str | None, Query(description="Birden çok dükkânınız varsa filtre")] = None,
    status_filter: Annotated[list[OrderStatus] | None, Query(alias="status")] = None,
    offset: Offset = 0,
    limit: Limit = 20,
) -> ApiResponse[OrderListResponse]:
    return ok(
        OrderService(db).incoming(
            user, shop_id=shop_id, statuses=status_filter, offset=offset, limit=limit
        )
    )


@router.get("/stats", summary="[Dükkân] Günlük sipariş analitiği (dashboard)")
def daily_stats(
    user: ShopStaffUser,
    db: DbSession,
    clock: Clock,
    shop_id: Annotated[str | None, Query(description="Birden çok dükkânınız varsa filtre")] = None,
    day: Annotated[date | None, Query(description="YYYY-AA-GG; boşsa bugün (İstanbul)")] = None,
) -> ApiResponse[ShopDailyStats]:
    return ok(OrderService(db, clock).daily_stats(user, shop_id=shop_id, day=day))


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}  # proxy'ler tamponlamasın


def _event_stream(request: Request, channels: list[str]) -> StreamingResponse:
    return StreamingResponse(
        sse_stream(channels, request.is_disconnected, keepalive_seconds=settings.sse_keepalive_seconds),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get(
    "/incoming/events",
    summary="[Dükkân] Canlı bildirim (SSE): yeni sipariş ve durum değişiklikleri",
    description="Tarayıcıda: `new EventSource('/api/v1/orders/incoming/events?token=<access_token>')`",
)
def incoming_events(request: Request, user: StreamUser, db: DbSession) -> StreamingResponse:
    if user.role not in (UserRole.SHOP_OWNER, UserRole.ADMIN):
        raise ForbiddenError()
    orders = OrderRepository(db)
    shop_ids = orders.all_shop_ids() if user.role == UserRole.ADMIN else orders.shop_ids_owned_by(user.id)
    db.close()  # yetki kontrolü bitti; uzun süren bağlantı boyunca veritabanı oturumu tutulmasın
    return _event_stream(request, [f"shop:{shop_id}" for shop_id in shop_ids])


@router.post(
    "/verify-qr",
    summary="[Dükkân] QR kodu doğrula: gerçek mi, bu dükkânın mı?",
    description="Sadece kontrol eder, durumu değiştirmez. Teslim için PATCH /orders/{id}/status → COMPLETED.",
)
def verify_qr(body: VerifyQrRequest, user: ShopStaffUser, db: DbSession) -> ApiResponse[VerifyQrResponse]:
    return ok(OrderService(db).verify_qr(user, body.qr_content))


@router.get("/{order_id}", summary="Sipariş detayı ve QR kod (sipariş sahibi veya dükkân)")
def get_order(order_id: str, user: CurrentUser, db: DbSession) -> ApiResponse[OrderResponse]:
    return ok(OrderService(db).get(user, order_id))


@router.get(
    "/{order_id}/events",
    summary="Siparişin canlı durum akışı (SSE) — müşteri ve dükkân",
    description="Tarayıcıda: `new EventSource('/api/v1/orders/{id}/events?token=<access_token>')`",
)
def order_events(order_id: str, request: Request, user: StreamUser, db: DbSession) -> StreamingResponse:
    OrderService(db).get(user, order_id)  # siparişi görme yetkisi yoksa 404
    db.close()
    return _event_stream(request, [f"order:{order_id}"])


@router.patch(
    "/{order_id}/status",
    summary="Durum güncelle — Dükkân: ACCEPTED → PREPARING → READY → COMPLETED (QR ile) / CANCELLED",
    description=(
        "- **Dükkân sahibi:** PENDING→ACCEPTED, ACCEPTED→PREPARING, PREPARING→READY, "
        "READY→COMPLETED (`qr_content` zorunlu). PENDING/ACCEPTED iken CANCELLED.\n"
        "- **Müşteri:** sadece PENDING iken CANCELLED.\n"
        "- İptalde kahve hakkı iade edilir."
    ),
)
def update_status(
    order_id: str, body: UpdateOrderStatusRequest, user: CurrentUser, db: DbSession, clock: Clock
) -> ApiResponse[OrderResponse]:
    return ok(OrderService(db, clock).update_status(user, order_id, body.status, body.qr_content))


@router.post(
    "/{order_id}/reorder",
    status_code=status.HTTP_201_CREATED,
    summary="[Müşteri] Favori siparişi tekrarla (aynı özelleştirmelerle)",
)
def reorder(order_id: str, user: CustomerUser, db: DbSession, clock: Clock) -> ApiResponse[OrderResponse]:
    return ok(OrderService(db, clock).reorder(user, order_id))
