from __future__ import annotations

from pathlib import Path

from seekphony_backend.core.config import get_settings

PATH_ENV_KEYS = (
    "SEEKPHONY_REPO_ROOT",
    "SEEKPHONY_DATA_DIR",
    "SEEKPHONY_DATABASE_PATH",
    "SEEKPHONY_SEED_PATH",
    "SEEKPHONY_UPLOAD_DIR",
)


def test_service_env_file_loads_paths_relative_to_env_file(monkeypatch, tmp_path: Path) -> None:
    for key in PATH_ENV_KEYS:
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
                "SEEKPHONY_SEED_PATH=../data/seeds/songs.json",
                "SEEKPHONY_UPLOAD_DIR=../var/uploads",
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
        for key in PATH_ENV_KEYS:
            monkeypatch.delenv(key, raising=False)

    assert settings.repo_root == tmp_path.resolve()
    assert settings.data_dir == (tmp_path / "var").resolve()
    assert settings.database_path == (tmp_path / "var" / "seekphony.sqlite3").resolve()
    assert settings.seed_path == (tmp_path / "data" / "seeds" / "songs.json").resolve()
    assert settings.upload_dir == (tmp_path / "var" / "uploads").resolve()


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
