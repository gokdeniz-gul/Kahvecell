"""Alembic ortamı: veritabanı adresini uygulamanın ayarlarından, tablo tanımlarını modellerden alır."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401  (tüm tablolar Base.metadata'ya kaydolsun)
from app.core.config import settings
from app.core.database import Base

config = context.config
# Uygulamanın kendi log ayarı varsa (programatik çalıştırma) onu ezmeyelim.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_with(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # SQLite ALTER TABLE'ı kısıtlı destekler; "batch" modu tabloyu kopyalayarak değiştirir.
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Dışarıdan bağlantı verildiyse (testler) onu kullan; kapatmak ve commit etmek çağıranın işi.
    external = config.attributes.get("connection")
    if external is not None:
        _run_with(external)
        return

    engine = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with engine.connect() as connection:
        _run_with(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
