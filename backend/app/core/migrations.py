"""Veritabanı şemasını Alembic migration'larıyla güncel tutar (case 4.2).

Uygulama ve seed betiği açılırken çağrılır; elle çalıştırmak için:
    alembic upgrade head                      # şemayı en son sürüme getir
    alembic revision --autogenerate -m "..."  # model değişikliğinden yeni migration üret
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import engine

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.attributes["configure_logger"] = False  # uygulamanın log ayarını koru
    return config


def upgrade_database() -> None:
    config = _alembic_config()
    tables = set(inspect(engine).get_table_names())

    if "users" in tables and "alembic_version" not in tables:
        # Alembic'ten önce create_all ile oluşturulmuş eski veritabanı: tablolar zaten
        # ilk migration ile aynı; yeniden oluşturmak yerine "bu sürümde" diye işaretle.
        logger.warning("Migration geçmişi olmayan veritabanı bulundu; ilk sürüm olarak işaretleniyor.")
        command.stamp(config, "0001_initial")

    command.upgrade(config, "head")
