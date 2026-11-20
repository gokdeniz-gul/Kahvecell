import re
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.models import Payment
from app.models.enums import PaymentStatus, PlanType


class CardDetails(BaseModel):
    """Kart formu. Kart numarası ASLA saklanmaz ve loglanmaz; sadece son 4 hanesi kaydedilir."""

    card_holder: str = Field(min_length=2, max_length=100, examples=["AYSE YILMAZ"])
    card_number: str = Field(
        examples=["4242 4242 4242 4242"],
        description="Test kartları: 4242 4242 4242 4242 (başarılı), 4000 0000 0000 0002 (reddedilir)",
    )
    expiry_month: int = Field(ge=1, le=12, examples=[12])
    expiry_year: int = Field(ge=2000, le=2100, examples=[2030])
    cvc: str = Field(pattern=r"^\d{3,4}$", examples=["123"])

    @field_validator("card_number")
    @classmethod
    def normalize_card_number(cls, value: str) -> str:
        digits = re.sub(r"[\s-]", "", value)
        if not re.fullmatch(r"\d{16}", digits):
            raise ValueError("Kart numarası 16 haneli olmalı.")
        return digits

    @model_validator(mode="after")
    def check_not_expired(self) -> "CardDetails":
        now = datetime.now(UTC)
        if (self.expiry_year, self.expiry_month) < (now.year, now.month):
            raise ValueError("Kartın son kullanma tarihi geçmiş.")
        return self


class ProcessPaymentRequest(BaseModel):
    """Case 12.1'deki istek. user_id gövdeden değil token'dan alınır:
    aksi halde biri başkası adına ödeme kaydı oluşturabilirdi."""

    plan_type: PlanType = Field(examples=["STARTER"])
    card: CardDetails


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    status: PaymentStatus
    plan_type: PlanType
    amount_kurus: int
    card_last4: str
    failure_reason: str | None
    subscription_id: str | None = Field(description="Bu ödemeyle başlatılan/değiştirilen abonelik")
    created_at: datetime = Field(description="İşlem zamanı (timestamp)")

    @computed_field
    def amount_tl(self) -> float:
        return self.amount_kurus / 100

    @classmethod
    def from_payment(cls, payment: Payment) -> "PaymentResponse":
        return cls.model_validate(
            {
                **{field: getattr(payment, field) for field in cls.model_fields if field != "plan_type"},
                "plan_type": payment.plan.plan_type,
            }
        )


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    offset: int
    limit: int
