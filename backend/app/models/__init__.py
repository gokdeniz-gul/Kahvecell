"""Tüm modelleri tek yerden içe aktarır.

create_all() sadece "tanıdığı" tabloları oluşturur; buraya eklenmeyen bir model
için tablo oluşmaz.
"""

from app.models.order import Order, OrderItem
from app.models.otp_request import OtpRequest
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.product import Product
from app.models.refresh_token import RefreshToken
from app.models.shop import Shop
from app.models.shop_photo import ShopPhoto
from app.models.subscription import Subscription
from app.models.user import User

__all__ = [
    "Order",
    "OrderItem",
    "OtpRequest",
    "Payment",
    "Plan",
    "Product",
    "RefreshToken",
    "Shop",
    "ShopPhoto",
    "Subscription",
    "User",
]
