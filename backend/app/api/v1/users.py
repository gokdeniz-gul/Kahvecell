from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.schemas.common import ApiResponse, ok
from app.schemas.user import (
    UpdateProfileRequest,
    UpdateRoleRequest,
    UserListResponse,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", summary="Giriş yapmış kullanıcının profili")
def get_me(user: CurrentUser) -> ApiResponse[UserResponse]:
    return ok(UserResponse.model_validate(user))


@router.patch("/me", summary="Profil tamamlama / güncelleme (ad, e-posta, tercihler, alerjenler)")
def update_me(body: UpdateProfileRequest, user: CurrentUser, db: DbSession) -> ApiResponse[UserResponse]:
    updated = UserService(db).update_profile(user, body)
    return ok(UserResponse.model_validate(updated))


@router.get("", summary="[ADMIN] Kullanıcıları listele")
def list_users(
    _admin: AdminUser,
    db: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[UserListResponse]:
    return ok(UserService(db).list_users(offset=offset, limit=limit))


@router.patch("/{user_id}/role", summary="[ADMIN] Kullanıcının rolünü değiştir")
def change_role(
    user_id: str, body: UpdateRoleRequest, admin: AdminUser, db: DbSession
) -> ApiResponse[UserResponse]:
    updated = UserService(db).change_role(admin, user_id, body.role)
    return ok(UserResponse.model_validate(updated))
