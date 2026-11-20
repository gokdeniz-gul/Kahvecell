import logging

logger = logging.getLogger(__name__)


def mask_phone(phone_number: str) -> str:
    """Loglarda numaranın tamamı görünmesin: 5551234567 → 555***4567"""
    return f"{phone_number[:3]}***{phone_number[-4:]}"


class SimulatedSmsSender:
    """Gerçek SMS yerine kodu log'a yazar (case 11.2: SMS OTP simülasyonu kabul edilir).

    Gerçek bir SMS sağlayıcısına geçilecekse sadece bu sınıfın yerine yenisi yazılır;
    AuthService değişmez.
    """

    def send_otp(self, phone_number: str, code: str) -> None:
        logger.info(
            "[SMS SİMÜLASYONU] %s numarasına doğrulama kodu gönderildi: %s",
            mask_phone(phone_number),
            code,
        )
