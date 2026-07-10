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
    database_url: str | None
    max_upload_bytes: int
    min_clip_seconds: float
    max_clip_seconds: float
    decode_timeout_seconds: float
    gemini_api_key: str | None
    gemini_model: str
    provider_timeout_seconds: float
    reference_import_timeout_seconds: float
    admin_token: str | None
    cors_origins: tuple[str, ...]

    @property
    def database_kind(self) -> str:
        if self.database_url:
            if self.database_url.startswith(("postgres://", "postgresql://")):
                return "postgres"
            return "external"
        return "sqlite"


@lru_cache
def get_settings() -> Settings:
    env_file_dir = _load_env_file(_repo_root())
    root = _path_env("SEEKPHONY_REPO_ROOT", _repo_root(), env_file_dir)
    data_dir = _path_env("SEEKPHONY_DATA_DIR", root / "var", env_file_dir)
    cors_raw = os.getenv("SEEKPHONY_CORS_ORIGINS", "*")
    return Settings(
        app_name=os.getenv("SEEKPHONY_APP_NAME", "Seekphony Backend"),
        api_prefix=os.getenv("SEEKPHONY_API_PREFIX", "/api/v1"),
        repo_root=root,
        data_dir=data_dir,
        database_path=_path_env(
            "SEEKPHONY_DATABASE_PATH", data_dir / "seekphony.sqlite3", env_file_dir
        ),
        database_url=os.getenv("DATABASE_URL") or None,
        max_upload_bytes=_int_env("SEEKPHONY_MAX_UPLOAD_BYTES", 30 * 1024 * 1024),
        min_clip_seconds=_float_env("SEEKPHONY_MIN_CLIP_SECONDS", 5.0),
        max_clip_seconds=_float_env("SEEKPHONY_MAX_CLIP_SECONDS", 60.0),
        decode_timeout_seconds=_float_env("SEEKPHONY_DECODE_TIMEOUT_SECONDS", 15.0),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
        gemini_model=os.getenv("SEEKPHONY_GEMINI_MODEL", "gemini-3.1-flash-lite"),
        provider_timeout_seconds=_float_env("SEEKPHONY_PROVIDER_TIMEOUT_SECONDS", 8.0),
        reference_import_timeout_seconds=_float_env(
            "SEEKPHONY_REFERENCE_IMPORT_TIMEOUT_SECONDS",
            30.0,
        ),
        admin_token=os.getenv("SEEKPHONY_ADMIN_TOKEN") or None,
        cors_origins=tuple(origin.strip() for origin in cors_raw.split(",") if origin.strip()),
    )
