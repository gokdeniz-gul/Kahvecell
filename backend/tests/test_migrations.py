"""Migration'lar modellerle birebir aynı şemayı üretiyor mu? (case 4.2)

Bir model değiştirilip migration yazılması unutulursa bu test kırılır.
"""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.core.database import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _config_for(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.attributes["configure_logger"] = False
    return config


def _upgrade(engine, config: Config, revision: str = "head") -> None:
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)


def test_migrations_match_models(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'migrated.db'}")
    _upgrade(engine, _config_for(str(engine.url)))

    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert differences == [], f"Modeller ile migration'lar farklı: {differences}"


def test_downgrade_removes_all_tables(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'roundtrip.db'}")
    config = _config_for(str(engine.url))
    _upgrade(engine, config)

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")

    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
