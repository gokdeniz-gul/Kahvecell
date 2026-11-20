"""Sabit değer listeleri. Veritabanına bu listelerin dışında bir değer yazılamaz."""

from enum import StrEnum


class UserRole(StrEnum):
    CUSTOMER = "CUSTOMER"
    SHOP_OWNER = "SHOP_OWNER"
    ADMIN = "ADMIN"


class PlanType(StrEnum):
    STARTER = "STARTER"
    PREMIUM = "PREMIUM"
    UNLIMITED = "UNLIMITED"


class SubscriptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ProductCategory(StrEnum):
    HOT_COFFEE = "HOT_COFFEE"
    COLD_COFFEE = "COLD_COFFEE"
    TEA = "TEA"
    OTHER = "OTHER"


class OrderStatus(StrEnum):
    """Sipariş durum makinesi: PENDING → ACCEPTED → PREPARING → READY → COMPLETED.
    PENDING veya ACCEPTED iken CANCELLED olabilir. Geçiş kuralları servis katmanında uygulanır."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CupSize(StrEnum):
    S = "S"
    M = "M"
    L = "L"


class SugarLevel(StrEnum):
    NONE = "NONE"
    LESS = "LESS"
    NORMAL = "NORMAL"
    EXTRA = "EXTRA"


class MilkType(StrEnum):
    NONE = "NONE"
    WHOLE = "WHOLE"
    LACTOSE_FREE = "LACTOSE_FREE"
    OAT = "OAT"
    ALMOND = "ALMOND"


class PaymentStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
