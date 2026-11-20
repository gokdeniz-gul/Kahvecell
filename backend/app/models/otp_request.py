from datetime import datetime

from sqlalchemy import CheckConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin


class OtpRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Gönderilen her SMS kodu için bir kayıt.

    Simülasyonda kod hep aynı (1234) olsa da süre, deneme hakkı ve "bir kez kullanılır"
    kuralları gerçek sistemdeki gibi uygulanır. Gerçek SMS'e geçince sadece kod üretimi değişir.
    """

    __tablename__ = "otp_requests"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="ck_otp_requests_attempts_non_negative"),
        # "Bu numaranın en son istenen kodu" sorgusu için.
        Index("ix_otp_requests_phone_created", "phone_number", "created_at"),
    )

    phone_number: Mapped[str] = mapped_column(String(15))
    # Kodun kendisi değil, SHA-256 özeti saklanır (veritabanı sızsa bile kodlar okunamaz).
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    attempts: Mapped[int] = mapped_column(default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
