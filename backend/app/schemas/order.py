import json
from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field, computed_field

from app.models.enums import CupSize, MilkType, OrderStatus, SugarLevel


class CreateOrderRequest(BaseModel):
    """Bir sipariş = bir kahve = bir kahve hakkı."""

    shop_id: str
    product_id: str
    size: CupSize = CupSize.M
    sugar: SugarLevel = SugarLevel.NONE
    milk: MilkType = MilkType.NONE
    extra_shots: int = Field(default=0, ge=0, le=3, description="Ek espresso shot (0-3)")
    note: str | None = Field(default=None, max_length=200, examples=["Az köpüklü lütfen"])


def _qr_to_text(value: Any) -> Any:
    """QR okuyucu metin verir; Swagger'da elle test ederken payload nesnesini yapıştırmak da olur."""
    return json.dumps(value, separators=(",", ":")) if isinstance(value, dict) else value


QrContent = Annotated[
    str,
    BeforeValidator(_qr_to_text),
    Field(
        description="QR'dan okunan metin (qr.content) ya da doğrudan qr.payload nesnesi",
        examples=[{"order_id": "...", "user_id": "...", "shop_id": "...",
                   "created_at": "2026-11-20T14:30:00Z", "signature": "..."}],
    ),
]


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus = Field(examples=["ACCEPTED"])
    qr_content: QrContent | None = Field(
        default=None, description="Sadece COMPLETED (teslim) için zorunlu: müşterinin QR'ı"
    )


class VerifyQrRequest(BaseModel):
    qr_content: QrContent


class OrderItemResponse(BaseModel):
    product_id: str
    product_name: str
    size: CupSize
    sugar: SugarLevel
    milk: MilkType
    extra_shots: int
    unit_price_kurus: int

    @computed_field
    def unit_price_tl(self) -> float:
        return self.unit_price_kurus / 100


class OrderShopInfo(BaseModel):
    id: str
    name: str
    address: str


class QrCodeResponse(BaseModel):
    payload: dict[str, str] = Field(description="Case 13.2 formatındaki QR içeriği")
    content: str = Field(description="QR'a gömülen metin; dükkân bu metni okutur")
    image_data_url: str = Field(description="QR görseli; tarayıcı adres çubuğuna yapıştırıp açın")


class OrderResponse(BaseModel):
    id: str
    status: OrderStatus
    shop: OrderShopInfo
    customer_name: str = Field(description="Dükkân ekranında gösterilecek müşteri adı")
    items: list[OrderItemResponse]
    credits_used: int = Field(description="Bu siparişte düşülen kahve hakkı (Unlimited'da 0)")
    is_priority: bool = Field(description="Unlimited aboneler öncelikli (dükkân listesinde üstte)")
    note: str | None
    allowed_next_statuses: list[OrderStatus] = Field(
        description="Bu siparişin geçebileceği durumlar (dükkân paneli düğmeleri için)"
    )
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None
    qr: QrCodeResponse | None = Field(
        default=None, description="Sadece siparişin sahibine ve teslim edilmemiş siparişte gösterilir"
    )


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    offset: int
    limit: int


class VerifyQrResponse(BaseModel):
    valid: bool
    message: str
    can_complete: bool = Field(description="Sipariş READY durumundaysa teslim edilebilir")
    order: OrderResponse


class TopProduct(BaseModel):
    name: str
    count: int


class ShopDailyStats(BaseModel):
    """Dükkân sahibi dashboard'u: bir günün sipariş analitiği (case 3.5)."""

    day: date
    total_orders: int
    by_status: dict[OrderStatus, int]
    completed: int
    cancelled: int
    active: int = Field(description="Henüz teslim edilmemiş/iptal edilmemiş siparişler")
    credits_used: int
    avg_prep_minutes: float | None = Field(description="Siparişten teslime ortalama süre (dk)")
    top_products: list[TopProduct]
    hourly: list[int] = Field(description="İstanbul saatine göre 0-23 arası saatlik sipariş sayısı")
