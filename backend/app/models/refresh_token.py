from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Kullanıcının açık oturumları. Her refresh token tek kullanımlıktır (rotation).

    Token'ın kendisi değil SHA-256 özeti saklanır. Çıkış yapınca revoked_at dolar ve
    o token bir daha kullanılamaz.
    """

    __tablename__ = "refresh_tokens"

    # CASCADE: kullanıcı silinirse oturumları da silinir.
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
