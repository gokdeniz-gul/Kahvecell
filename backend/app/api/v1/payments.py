from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, CustomerUser, DbSession
from app.schemas.common import ApiResponse, ok
from app.schemas.payment import PaymentListResponse, PaymentResponse, ProcessPaymentRequest
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/process",
    summary="Mobil ödeme simülasyonu (4242… başarılı, 4000…0002 reddedilir)",
    description=(
        "Tutarı sunucu hesaplar: aboneliğiniz yoksa paketin tam fiyatı, "
        "daha pahalı bir pakete yükseltiyorsanız aradaki fark. "
        "Başarılı ödemenin `transaction_id` değeriyle POST /subscriptions veya "
        "PATCH /subscriptions/me çağrılır. Reddedilen ödeme 402 döner ve geçmişe kaydedilir."
    ),
)
def process_payment(
    body: ProcessPaymentRequest, user: CustomerUser, db: DbSession
) -> ApiResponse[PaymentResponse]:
    return ok(PaymentService(db).process(user, body.plan_type, body.card))


@router.get("/me", summary="Ödeme geçmişim (en yeni en üstte)")
def payment_history(
    user: CurrentUser,
    db: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[PaymentListResponse]:
    return ok(PaymentService(db).history(user, offset=offset, limit=limit))
