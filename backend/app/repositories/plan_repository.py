from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Plan
from app.models.enums import PlanType


class PlanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active(self) -> Sequence[Plan]:
        return self.db.scalars(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.monthly_price_kurus)
        ).all()

    def get_active_by_type(self, plan_type: PlanType) -> Plan | None:
        return self.db.scalar(
            select(Plan).where(Plan.plan_type == plan_type, Plan.is_active.is_(True))
        )
