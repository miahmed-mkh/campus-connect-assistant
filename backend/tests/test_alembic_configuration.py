from pathlib import Path

import backend.app.models  # noqa: F401
from alembic.config import Config

from backend.app.db.database import Base


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"
MIGRATION_DIRECTORY = PROJECT_ROOT / "backend" / "alembic"
VERSIONS_DIRECTORY = MIGRATION_DIRECTORY / "versions"

EXPECTED_TABLES = {
    "conversation_sessions",
    "feedbacks",
    "messages",
}


def test_alembic_configuration_exists() -> None:
    assert ALEMBIC_CONFIG_PATH.is_file()
    assert (MIGRATION_DIRECTORY / "env.py").is_file()
    assert (MIGRATION_DIRECTORY / "script.py.mako").is_file()
    assert VERSIONS_DIRECTORY.is_dir()


def test_alembic_script_location_is_valid() -> None:
    config = Config(str(ALEMBIC_CONFIG_PATH))
    script_location = Path(
        config.get_main_option("script_location")
    ).resolve()

    assert script_location == MIGRATION_DIRECTORY.resolve()


def test_all_models_are_registered_in_metadata() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_initial_migration_exists() -> None:
    migration_files = [
        path
        for path in VERSIONS_DIRECTORY.glob("*.py")
        if path.name != "__init__.py"
    ]

    assert len(migration_files) == 1
    assert migration_files[0].name.startswith("66a7581910ef_")