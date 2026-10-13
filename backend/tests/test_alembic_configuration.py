from pathlib import Path

import backend.app.models  # noqa: F401
from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.app.db.database import Base


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"
MIGRATION_DIRECTORY = PROJECT_ROOT / "backend" / "alembic"
VERSIONS_DIRECTORY = MIGRATION_DIRECTORY / "versions"

EXPECTED_TABLES = {
    "conversation_sessions",
    "feedbacks",
    "iot_readings",
    "messages",
}

# Chaîne de migrations attendue : revision -> down_revision
EXPECTED_REVISIONS = {
    "66a7581910ef": None,
    "090ffb7eecf9": "66a7581910ef",
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


def test_migration_files_match_expected_revisions() -> None:
    migration_files = [
        path
        for path in VERSIONS_DIRECTORY.glob("*.py")
        if path.name != "__init__.py"
    ]
    found_prefixes = {path.name.split("_", 1)[0] for path in migration_files}

    assert found_prefixes == set(EXPECTED_REVISIONS)


def test_migration_chain_is_linear_and_consistent() -> None:
    config = Config(str(ALEMBIC_CONFIG_PATH))
    script = ScriptDirectory.from_config(config)

    actual_chain = {
        revision.revision: revision.down_revision
        for revision in script.walk_revisions()
    }

    assert actual_chain == EXPECTED_REVISIONS
    assert script.get_heads() == ["090ffb7eecf9"]
