from fastapi import APIRouter, status

from app.api.deps import CurrentUser, CustomerUser, DbSession
from app.schemas.common import ApiResponse, ok
from app.schemas.subscription import (
    ChangePlanRequest,
    PlanResponse,
    StartSubscriptionRequest,
    SubscriptionResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/plans", summary="Paketleri listele (giriş gerekmez)")
def list_plans(db: DbSession) -> ApiResponse[list[PlanResponse]]:
    plans = SubscriptionService(db).list_plans()
    return ok([PlanResponse.model_validate(plan) for plan in plans])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Abonelik başlat (önce POST /payments/process ile ödeme yapın)",
)
def start_subscription(
    body: StartSubscriptionRequest, user: CustomerUser, db: DbSession
) -> ApiResponse[SubscriptionResponse]:
    subscription = SubscriptionService(db).start(user, body.plan_type, body.transaction_id)
    return ok(SubscriptionResponse.model_validate(subscription))


@router.get("/me", summary="Aktif aboneliğim (yoksa data: null)")
def get_my_subscription(user: CurrentUser, db: DbSession) -> ApiResponse[SubscriptionResponse | None]:
    subscription = SubscriptionService(db).get_current(user)
    return ok(SubscriptionResponse.model_validate(subscription) if subscription else None)


@router.patch(
    "/me",
    summary="Paket yükselt (hemen, fark ödenir) / düşür (gelecek dönem, ücretsiz)",
)
def change_plan(
    body: ChangePlanRequest, user: CustomerUser, db: DbSession
) -> ApiResponse[SubscriptionResponse]:
    subscription = SubscriptionService(db).change_plan(user, body.plan_type, body.transaction_id)
    return ok(SubscriptionResponse.model_validate(subscription))


@router.delete("/me", summary="Aboneliği iptal et (dönem sonuna kadar geçerli kalır)")
def cancel_subscription(user: CustomerUser, db: DbSession) -> ApiResponse[SubscriptionResponse]:
    subscription = SubscriptionService(db).cancel(user)
    return ok(SubscriptionResponse.model_validate(subscription))
