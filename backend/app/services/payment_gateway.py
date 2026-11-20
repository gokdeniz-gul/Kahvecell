"""Sahte ödeme sağlayıcısı (case bölüm 12: mobil ödeme simülasyonu).

Gerçek bir sağlayıcıya geçildiğinde sadece bu sınıfın yerine yenisi yazılır;
PaymentService ve SubscriptionService değişmez.
"""

import uuid
from dataclasses import dataclass

from app.core.exceptions import BadRequestError

TEST_CARD_SUCCESS = "4242424242424242"
TEST_CARD_DECLINED = "4000000000000002"


@dataclass(frozen=True)
class ChargeResult:
    approved: bool
    transaction_id: str
    failure_reason: str | None = None


def new_transaction_id() -> str:
    return f"TXN-{uuid.uuid4().hex[:16].upper()}"


class MockPaymentGateway:
    def charge(self, card_number: str, amount_kurus: int) -> ChargeResult:
        if card_number == TEST_CARD_SUCCESS:
            return ChargeResult(approved=True, transaction_id=new_transaction_id())
        if card_number == TEST_CARD_DECLINED:
            return ChargeResult(
                approved=False,
                transaction_id=new_transaction_id(),
                failure_reason="Kart bankası tarafından reddedildi.",
            )
        raise BadRequestError(
            "Simülasyonda sadece test kartları kullanılabilir: "
            "4242 4242 4242 4242 (başarılı) veya 4000 0000 0000 0002 (başarısız).",
            code="UNSUPPORTED_TEST_CARD",
        )
