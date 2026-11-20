from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UpdateProfileRequest, UserListResponse, UserResponse


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def update_profile(self, user: User, request: UpdateProfileRequest) -> User:
        changes = request.model_dump(exclude_unset=True)  # sadece gönderilen alanlar

        if "full_name" in changes:
            if changes["full_name"] is None:
                raise BadRequestError("Ad soyad boş bırakılamaz.", code="FULL_NAME_REQUIRED")
            user.full_name = changes["full_name"].strip()

        if "email" in changes:
            email = changes["email"]
            if email is not None:
                owner = self.users.get_by_email(email)
                if owner is not None and owner.id != user.id:
                    raise ConflictError(
                        "Bu e-posta başka bir hesapta kullanılıyor.", code="EMAIL_ALREADY_IN_USE"
                    )
                email = email.lower()
            user.email = email

        if "preferences" in changes:
            user.preferences = (
                request.preferences.model_dump() if request.preferences is not None else None
            )

        self.db.commit()
        return user

    def list_users(self, *, offset: int, limit: int) -> UserListResponse:
        users, total = self.users.list(offset=offset, limit=limit)
        return UserListResponse(
            items=[UserResponse.model_validate(user) for user in users],
            total=total,
            offset=offset,
            limit=limit,
        )

    def change_role(self, admin: User, user_id: str, role: UserRole) -> User:
        if admin.id == user_id:
            # Tek admin kendi yetkisini yanlışlıkla düşürürse sistemde admin kalmaz.
            raise BadRequestError("Kendi rolünüzü değiştiremezsiniz.", code="CANNOT_CHANGE_OWN_ROLE")
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Kullanıcı bulunamadı.", code="USER_NOT_FOUND")
        user.role = role
        self.db.commit()
        return user
