from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import PlanType, SubscriptionStatus


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_type: PlanType
    name: str
    monthly_price_kurus: int
    monthly_credits: int | None = Field(description="null = sınırsız")
    guest_passes: int
    has_priority: bool

    @computed_field
    def monthly_price_tl(self) -> float:
        return self.monthly_price_kurus / 100

    @computed_field
    def is_unlimited(self) -> bool:
        return self.monthly_credits is None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: SubscriptionStatus
    plan: PlanResponse
    remaining_credits: int | None = Field(description="null = sınırsız")
    remaining_guest_passes: int
    started_at: datetime
    expires_at: datetime = Field(description="Dönem sonu: haklar yenilenir ya da iptal edildiyse biter")
    cancelled_at: datetime | None
    pending_plan: PlanResponse | None = Field(
        description="Düşürme talebi varsa bir sonraki dönem geçilecek paket"
    )


class StartSubscriptionRequest(BaseModel):
    plan_type: PlanType = Field(examples=["STARTER"])
    transaction_id: str = Field(
        min_length=1, description="POST /payments/process'ten dönen başarılı ödemenin numarası"
    )


class ChangePlanRequest(BaseModel):
    plan_type: PlanType = Field(examples=["PREMIUM"])
    transaction_id: str | None = Field(
        default=None,
        description="Sadece YÜKSELTMEDE gerekir (fark ödemesi). Düşürmede boş bırakın.",
    )
