"""Veritabanı bağlantısı, oturum (session) üretimi ve tüm modellerin ortak tabanı."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    # SQLite varsayılan olarak bağlantıyı tek thread'e kilitler; FastAPI çok thread kullanır.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


if _is_sqlite:

    @event.listens_for(Engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        """SQLite foreign key kurallarını varsayılan olarak UYGULAMAZ; her bağlantıda açıyoruz."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    """Tüm tablo modelleri bu sınıftan türer."""


def get_db() -> Generator[Session, None, None]:
    """Her istek için bir oturum açar, istek bitince kapatır (FastAPI dependency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
