from __future__ import annotations

import ipaddress
import urllib.error
import urllib.request
from email.message import Message

from seekphony_backend.services import reference_imports


def test_direct_reference_import_retries_transient_download_failure(monkeypatch) -> None:
    opener = FakeOpener()
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: opener)

    imported = reference_imports._download_direct_url(
        "https://example.com/reference.wav",
        max_bytes=1024,
        timeout_seconds=30.0,
        resolver=public_resolver,
    )

    assert imported.content == b"RIFFdata"
    assert imported.filename == "reference.wav"
    assert imported.media_type == "audio/wav"
    assert opener.open_count == 2
    assert opener.timeouts == [30.0, 30.0]
    assert opener.user_agents[0]


class FakeOpener:
    def __init__(self) -> None:
        self.open_count = 0
        self.timeouts: list[float] = []
        self.user_agents: list[str | None] = []

    def open(self, request: urllib.request.Request, timeout: float) -> object:
        self.open_count += 1
        self.timeouts.append(timeout)
        self.user_agents.append(request.get_header("User-agent"))
        if self.open_count == 1:
            raise urllib.error.URLError("temporary connection reset")
        return FakeResponse()


class FakeResponse:
    def __init__(self) -> None:
        headers = Message()
        headers["Content-Type"] = "audio/wav"
        headers["Content-Length"] = "8"
        self.headers = headers
        self._chunks = [b"RIFFdata", b""]

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def geturl(self) -> str:
        return "https://example.com/reference.wav"

    def read(self, _size: int) -> bytes:
        return self._chunks.pop(0)


def public_resolver(_hostname: str) -> list[ipaddress.IPv4Address]:
    return [ipaddress.ip_address("8.8.8.8")]
