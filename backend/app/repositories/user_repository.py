from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from app.models.enums import UserRole


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_by_phone(self, phone_number: str) -> User | None:
        return self.db.scalar(select(User).where(User.phone_number == phone_number))

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def create(self, phone_number: str, role: UserRole = UserRole.CUSTOMER) -> User:
        user = User(phone_number=phone_number, role=role)
        self.db.add(user)
        self.db.flush()  # id'nin oluşması için; commit'i servis katmanı yapar
        return user

    def list(self, *, offset: int, limit: int) -> tuple[Sequence[User], int]:
        total = self.db.scalar(select(func.count()).select_from(User)) or 0
        users = self.db.scalars(
            select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        ).all()
        return users, total
