from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_upload_name(original_name: str | None, file_hash: str) -> str:
    suffix = ""
    if original_name and "." in original_name:
        suffix = Path(original_name).suffix.lower()[:16]
    return f"{file_hash[:16]}-{uuid4().hex[:8]}{suffix}"
