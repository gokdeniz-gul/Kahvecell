from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import OtpRequest


class OtpRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, phone_number: str, code_hash: str, expires_at: datetime) -> OtpRequest:
        otp = OtpRequest(phone_number=phone_number, code_hash=code_hash, expires_at=expires_at)
        self.db.add(otp)
        return otp

    def get_latest_active(self, phone_number: str) -> OtpRequest | None:
        """Bu numara için en son istenen ve henüz kullanılmamış kod."""
        return self.db.scalar(
            select(OtpRequest)
            .where(OtpRequest.phone_number == phone_number, OtpRequest.consumed_at.is_(None))
            .order_by(OtpRequest.created_at.desc())
            .limit(1)
        )

    def consume_all_active(self, phone_number: str, now: datetime) -> None:
        """Yeni kod istenince eski kodlar geçersiz olur."""
        self.db.execute(
            update(OtpRequest)
            .where(OtpRequest.phone_number == phone_number, OtpRequest.consumed_at.is_(None))
            .values(consumed_at=now)
        )
