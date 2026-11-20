"""Tüm tablolarda tekrar eden kolonlar ve tipler: UUID primary key, UTC tarih, zaman damgaları."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> str:
    return str(uuid.uuid4())


def enum_column(enum_cls: type[StrEnum]) -> Enum:
    """Enum'u veritabanında metin + CHECK kuralı olarak saklar (SQLite'ta native enum yok)."""
    return Enum(
        enum_cls,
        native_enum=False,
        create_constraint=True,  # SQLAlchemy 2.0'da CHECK kuralı varsayılan olarak kapalı
        length=20,
        validate_strings=True,
    )


class UTCDateTime(TypeDecorator[datetime]):
    """Tarihleri her zaman UTC olarak yazar ve UTC bilgisiyle geri okur.

    SQLite saat dilimi bilgisini saklamaz; okunan tarih "saat dilimsiz" gelir ve
    datetime.now(UTC) ile karşılaştırınca TypeError verir. Bu tip o farkı kapatır.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Saat dilimi olmayan tarih kaydedilemez; datetime.now(UTC) kullanın.")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None else None


class UUIDPrimaryKeyMixin:
    # QR kod içeriği UUID istiyor; ayrıca sıralı ID'ler (1, 2, 3...) tahmin edilebilir olduğu için tercih etmedik.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, onupdate=utc_now)
