from __future__ import annotations

from pathlib import Path

from seekphony_backend.core.config import get_settings

PATH_ENV_KEYS = (
    "SEEKPHONY_REPO_ROOT",
    "SEEKPHONY_DATA_DIR",
    "SEEKPHONY_DATABASE_PATH",
)


def test_service_env_file_loads_paths_relative_to_env_file(monkeypatch, tmp_path: Path) -> None:
    for key in (*PATH_ENV_KEYS, "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)

    service_dir = tmp_path / "backend"
    service_dir.mkdir()
    env_file = service_dir / ".env"
    env_file.write_text(
        "\n".join(
            [
                "SEEKPHONY_REPO_ROOT=..",
                "SEEKPHONY_DATA_DIR=../var",
                "SEEKPHONY_DATABASE_PATH=../var/seekphony.sqlite3",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SEEKPHONY_ENV_FILE", str(env_file))

    get_settings.cache_clear()
    try:
        settings = get_settings()
    finally:
        get_settings.cache_clear()
        for key in (*PATH_ENV_KEYS, "DATABASE_URL"):
            monkeypatch.delenv(key, raising=False)

    assert settings.repo_root == tmp_path.resolve()
    assert settings.data_dir == (tmp_path / "var").resolve()
    assert settings.database_path == (tmp_path / "var" / "seekphony.sqlite3").resolve()
    assert settings.database_kind == "sqlite"


def test_injected_environment_overrides_service_env_file(monkeypatch, tmp_path: Path) -> None:
    for key in PATH_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    service_dir = tmp_path / "backend"
    service_dir.mkdir()
    env_file = service_dir / ".env"
    env_file.write_text("SEEKPHONY_DATA_DIR=../var\n", encoding="utf-8")
    override_dir = tmp_path / "override-data"

    monkeypatch.setenv("SEEKPHONY_ENV_FILE", str(env_file))
    monkeypatch.setenv("SEEKPHONY_DATA_DIR", str(override_dir))

    get_settings.cache_clear()
    try:
        settings = get_settings()
    finally:
        get_settings.cache_clear()
        for key in PATH_ENV_KEYS:
            monkeypatch.delenv(key, raising=False)

    assert settings.data_dir == override_dir.resolve()


def test_database_url_switches_to_postgres(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example:test@localhost:5432/seekphony")
    get_settings.cache_clear()
    try:
        settings = get_settings()
    finally:
        get_settings.cache_clear()
        monkeypatch.delenv("DATABASE_URL", raising=False)

    assert settings.database_kind == "postgres"


def test_reference_import_timeout_has_separate_environment_key(monkeypatch) -> None:
    monkeypatch.setenv("SEEKPHONY_REFERENCE_IMPORT_TIMEOUT_SECONDS", "42")
    monkeypatch.setenv("SEEKPHONY_PROVIDER_TIMEOUT_SECONDS", "8")
    get_settings.cache_clear()
    try:
        settings = get_settings()
    finally:
        get_settings.cache_clear()
        monkeypatch.delenv("SEEKPHONY_REFERENCE_IMPORT_TIMEOUT_SECONDS", raising=False)
        monkeypatch.delenv("SEEKPHONY_PROVIDER_TIMEOUT_SECONDS", raising=False)

    assert settings.reference_import_timeout_seconds == 42.0
    assert settings.provider_timeout_seconds == 8.0
