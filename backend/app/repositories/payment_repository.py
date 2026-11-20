from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Payment
from app.models.enums import PaymentStatus


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        return payment

    def get_by_transaction_id(self, transaction_id: str) -> Payment | None:
        return self.db.scalar(select(Payment).where(Payment.transaction_id == transaction_id))

    def get_last_successful(self, user_id: str) -> Payment | None:
        """Otomatik yenilemede "kayıtlı kart" olarak son başarılı ödemenin kartını kullanıyoruz."""
        return self.db.scalar(
            select(Payment)
            .where(Payment.user_id == user_id, Payment.status == PaymentStatus.SUCCESS)
            .order_by(Payment.created_at.desc())
            .limit(1)
        )

    def list_for_user(self, user_id: str, *, offset: int, limit: int) -> tuple[Sequence[Payment], int]:
        total = self.db.scalar(
            select(func.count()).select_from(Payment).where(Payment.user_id == user_id)
        ) or 0
        payments = self.db.scalars(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return payments, total
