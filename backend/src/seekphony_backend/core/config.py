from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_env_file(root: Path) -> Path | None:
    explicit = os.getenv("SEEKPHONY_ENV_FILE")
    candidates = [Path(explicit)] if explicit else [root / "backend" / ".env"]
    for candidate in candidates:
        path = candidate.expanduser().resolve()
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line.removeprefix("export ").strip()
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)
        return path.parent
    return None


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


def _path_env(name: str, default: Path, base_dir: Path | None) -> Path:
    value = os.getenv(name)
    if value is None:
        return default.resolve()
    path = Path(value)
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path.resolve()


@dataclass(frozen=True)
class Settings:
    app_name: str
    api_prefix: str
    repo_root: Path
    data_dir: Path
    database_path: Path
    seed_path: Path
    upload_dir: Path
    max_upload_bytes: int
    provider_timeout_seconds: float
    provider_retry_count: int
    provider_retry_delay_seconds: float
    gemini_api_key: str | None
    gemini_model: str
    enable_shazamio: bool
    cors_origins: tuple[str, ...]


@lru_cache
def get_settings() -> Settings:
    env_file_dir = _load_env_file(_repo_root())
    root = _path_env("SEEKPHONY_REPO_ROOT", _repo_root(), env_file_dir)
    data_dir = _path_env("SEEKPHONY_DATA_DIR", root / "data", env_file_dir)
    cors_raw = os.getenv("SEEKPHONY_CORS_ORIGINS", "*")
    return Settings(
        app_name=os.getenv("SEEKPHONY_APP_NAME", "Seekphony Backend"),
        api_prefix=os.getenv("SEEKPHONY_API_PREFIX", "/api/v1"),
        repo_root=root,
        data_dir=data_dir,
        database_path=_path_env(
            "SEEKPHONY_DATABASE_PATH", data_dir / "seekphony.sqlite3", env_file_dir
        ),
        seed_path=_path_env("SEEKPHONY_SEED_PATH", data_dir / "seeds" / "songs.json", env_file_dir),
        upload_dir=_path_env("SEEKPHONY_UPLOAD_DIR", data_dir / "uploads", env_file_dir),
        max_upload_bytes=_int_env("SEEKPHONY_MAX_UPLOAD_BYTES", 15 * 1024 * 1024),
        provider_timeout_seconds=_float_env("SEEKPHONY_PROVIDER_TIMEOUT_SECONDS", 8.0),
        provider_retry_count=_int_env("SEEKPHONY_PROVIDER_RETRY_COUNT", 2),
        provider_retry_delay_seconds=_float_env("SEEKPHONY_PROVIDER_RETRY_DELAY_SECONDS", 0.5),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        gemini_model=os.getenv("SEEKPHONY_GEMINI_MODEL", "gemini-2.5-flash"),
        enable_shazamio=_bool_env("SEEKPHONY_ENABLE_SHAZAMIO", False),
        cors_origins=tuple(origin.strip() for origin in cors_raw.split(",") if origin.strip()),
    )
