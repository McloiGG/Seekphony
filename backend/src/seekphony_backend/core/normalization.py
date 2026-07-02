from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_PUNCTUATION_RE = re.compile(r"[^a-z0-9]+")
_SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_value.casefold().strip()
    compact = _PUNCTUATION_RE.sub(" ", lowered)
    return _SPACE_RE.sub(" ", compact).strip()


def normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    split = urlsplit(value.strip())
    if not split.scheme or not split.netloc:
        return value.strip()
    query = urlencode(sorted(parse_qsl(split.query, keep_blank_values=True)))
    path = split.path.rstrip("/") or "/"
    return urlunsplit((split.scheme.lower(), split.netloc.lower(), path, query, ""))
