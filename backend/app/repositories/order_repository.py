from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Order, Plan, Product, Shop, Subscription
from app.models.enums import OrderStatus


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return order

    def get(self, order_id: str) -> Order | None:
        return self.db.get(Order, order_id)

    def get_product_in_shop(self, shop_id: str, product_id: str) -> Product | None:
        return self.db.scalar(
            select(Product).where(Product.id == product_id, Product.shop_id == shop_id)
        )

    def consume_credit(self, subscription_id: str) -> bool:
        """Kahve hakkını TEK bir SQL komutuyla düşürür: "hak > 0 ise 1 azalt".

        Kontrol ve düşürme aynı anda yapıldığı için, kullanıcı aynı anda iki kez
        "sipariş ver"e bassa bile son hakkı iki kez harcanamaz (race condition yok).
        """
        result = self.db.execute(
            update(Subscription)
            .where(Subscription.id == subscription_id, Subscription.remaining_credits > 0)
            .values(remaining_credits=Subscription.remaining_credits - 1)
        )
        return result.rowcount == 1

    def refund_credit(self, subscription_id: str) -> None:
        self.db.execute(
            update(Subscription)
            .where(Subscription.id == subscription_id, Subscription.remaining_credits.is_not(None))
            .values(remaining_credits=Subscription.remaining_credits + 1)
        )

    def list_for_user(self, user_id: str, *, offset: int, limit: int) -> tuple[Sequence[Order], int]:
        total = self.db.scalar(
            select(func.count()).select_from(Order).where(Order.user_id == user_id)
        ) or 0
        orders = self.db.scalars(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return orders, total

    def list_for_shops(
        self, shop_ids: list[str] | None, statuses: list[OrderStatus], *, offset: int, limit: int
    ) -> tuple[Sequence[Order], int]:
        """shop_ids=None → tüm dükkânlar (admin)."""
        conditions = [Order.status.in_(statuses)]
        if shop_ids is not None:
            conditions.append(Order.shop_id.in_(shop_ids))
        total = self.db.scalar(select(func.count()).select_from(Order).where(*conditions)) or 0
        orders = self.db.scalars(
            select(Order)
            .join(Subscription, Order.subscription_id == Subscription.id)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(*conditions)
            # Unlimited (öncelikli) aboneler önce, sonra ilk gelen ilk hazırlanır.
            .order_by(Plan.has_priority.desc(), Order.created_at)
            .offset(offset)
            .limit(limit)
        ).all()
        return orders, total

    def shop_ids_owned_by(self, owner_id: str) -> list[str]:
        return list(self.db.scalars(select(Shop.id).where(Shop.owner_id == owner_id)).all())
