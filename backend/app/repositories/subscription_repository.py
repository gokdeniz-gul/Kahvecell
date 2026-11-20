from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Subscription
from app.models.enums import SubscriptionStatus

# Dönem sonuna kadar kullanılabilen durumlar (iptal edilen de dönem sonuna kadar geçerli).
CURRENT_STATUSES = (
    SubscriptionStatus.ACTIVE,
    SubscriptionStatus.PAUSED,
    SubscriptionStatus.CANCELLED,
)


class SubscriptionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_current_for_user(self, user_id: str) -> Subscription | None:
        """Kullanıcının şu anki (süresi dolmuş olabilir, servis kontrol eder) aboneliği."""
        return self.db.scalar(
            select(Subscription).where(
                Subscription.user_id == user_id, Subscription.status.in_(CURRENT_STATUSES)
            )
        )

    def add(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.flush()
        return subscription
