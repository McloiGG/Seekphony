from __future__ import annotations

import io
import ipaddress
import math
import wave
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from seekphony_backend.application import create_app
from seekphony_backend.core.config import Settings
from seekphony_backend.services.reference_imports import ImportedReference, ReferenceImportService


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        app_name="Seekphony Test Backend",
        api_prefix="/api/v1",
        repo_root=Path(__file__).resolve().parents[2],
        data_dir=tmp_path,
        database_path=tmp_path / "seekphony.sqlite3",
        database_url=None,
        max_upload_bytes=30 * 1024 * 1024,
        min_clip_seconds=5.0,
        max_clip_seconds=60.0,
        decode_timeout_seconds=1.0,
        gemini_api_key=None,
        gemini_model="gemini-3.1-flash-lite",
        provider_timeout_seconds=0.1,
        cors_origins=("*",),
    )
    return TestClient(create_app(settings))


def test_health_reports_evaluator_runtime(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["kind"] == "sqlite"
    assert body["providers"]["gemini_configured"] is False
    assert body["limits"]["max_clip_seconds"] == 60.0


def test_evaluation_returns_metrics_without_gemini(client: TestClient) -> None:
    reference = make_wav(440.0, 6.0)
    performance = make_wav(440.0, 6.0)

    response = post_evaluation(client, reference, performance)
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "completed"
    assert body["evaluation_id"] == 1
    assert body["scores"]["overall"] > 80
    assert body["scores"]["pitch"] > 80
    assert body["metrics"]["key_shift_semitones"] == 0
    assert body["metrics"]["voiced_coverage"] > 0.75
    assert body["explanation"]["status"] == "unavailable"
    assert "Gemini API key" in body["explanation"]["error"]


def test_evaluation_acknowledges_transposed_performance(client: TestClient) -> None:
    reference = make_wav(440.0, 6.0)
    performance = make_wav(493.883, 6.0)

    response = post_evaluation(client, reference, performance)
    body = response.json()

    assert response.status_code == 200
    assert body["metrics"]["key_shift_semitones"] == 2
    assert body["scores"]["pitch"] > 70


def test_noisy_or_unvoiced_performance_returns_warning(client: TestClient) -> None:
    reference = make_wav(440.0, 6.0)
    performance = make_wav(0.0, 6.0, amplitude=0.0)

    response = post_evaluation(client, reference, performance)
    body = response.json()

    assert response.status_code == 200
    assert body["scores"]["coverage"] < 10
    assert body["metrics"]["confidence"] < 0.5
    assert body["warnings"]
    assert body["segments"]


def test_too_long_clip_is_rejected(client: TestClient) -> None:
    reference = make_wav(440.0, 65.0)
    performance = make_wav(440.0, 65.0)

    response = post_evaluation(client, reference, performance, clip_duration_seconds=61.0)

    assert response.status_code == 422
    assert response.json()["status"] == "validation_error"


def test_invalid_audio_is_rejected(client: TestClient) -> None:
    response = post_evaluation(client, b"not-a-wav", b"also-not-a-wav")

    assert response.status_code == 422
    assert response.json()["status"] == "audio_decode_failed"


def test_evaluation_history_endpoints(client: TestClient) -> None:
    response = post_evaluation(client, make_wav(440.0, 6.0), make_wav(440.0, 6.0))
    evaluation_id = response.json()["evaluation_id"]

    listed = client.get("/api/v1/evaluations")
    fetched = client.get(f"/api/v1/evaluations/{evaluation_id}")

    assert listed.status_code == 200
    assert listed.json()["evaluations"][0]["evaluation_id"] == evaluation_id
    assert fetched.status_code == 200
    assert fetched.json()["evaluation_id"] == evaluation_id


def test_evaluation_history_delete_and_clear(client: TestClient) -> None:
    first = post_evaluation(client, make_wav(440.0, 6.0), make_wav(440.0, 6.0))
    second = post_evaluation(client, make_wav(440.0, 6.0), make_wav(493.883, 6.0))
    first_id = first.json()["evaluation_id"]

    deleted = client.delete(f"/api/v1/evaluations/{first_id}")
    missing = client.get(f"/api/v1/evaluations/{first_id}")
    missing_delete = client.delete("/api/v1/evaluations/99999")
    cleared = client.delete("/api/v1/evaluations")
    listed = client.get("/api/v1/evaluations")

    assert second.status_code == 200
    assert deleted.status_code == 200
    assert deleted.json()["deleted_count"] == 1
    assert missing.status_code == 404
    assert missing_delete.status_code == 404
    assert cleared.status_code == 200
    assert cleared.json()["deleted_count"] == 1
    assert listed.json()["evaluations"] == []


def test_reference_import_endpoint_returns_direct_audio_blob(client: TestClient) -> None:
    services = client.app.state.services
    services.reference_imports = ReferenceImportService(
        services.settings,
        resolver=public_resolver,
        direct_adapter=lambda _url: ImportedReference(
            content=make_wav(440.0, 5.0),
            filename="reference.wav",
            media_type="audio/wav",
            source_type="direct_url",
            title="Reference",
        ),
    )

    response = client.post(
        "/api/v1/reference-audio/import",
        json={"url": "https://example.com/reference.wav"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.headers["x-seekphony-filename"] == "reference.wav"
    assert response.headers["x-seekphony-source-type"] == "direct_url"
    assert response.content.startswith(b"RIFF")


def test_reference_import_endpoint_uses_youtube_adapter(client: TestClient) -> None:
    calls: list[str] = []
    services = client.app.state.services

    def fake_youtube_import(url: str) -> ImportedReference:
        calls.append(url)
        return ImportedReference(
            content=make_wav(330.0, 5.0),
            filename="youtube-reference.m4a",
            media_type="audio/mp4",
            source_type="youtube",
            title="YouTube Reference",
        )

    services.reference_imports = ReferenceImportService(
        services.settings,
        resolver=public_resolver,
        youtube_adapter=fake_youtube_import,
    )

    response = client.post(
        "/api/v1/reference-audio/import",
        json={"url": "https://www.youtube.com/watch?v=abc123"},
    )

    assert response.status_code == 200
    assert calls == ["https://www.youtube.com/watch?v=abc123"]
    assert response.headers["x-seekphony-source-type"] == "youtube"
    assert response.headers["x-seekphony-filename"] == "youtube-reference.m4a"


def test_reference_import_rejects_invalid_and_private_urls(client: TestClient) -> None:
    unsupported = client.post(
        "/api/v1/reference-audio/import", json={"url": "ftp://example.com/a.wav"}
    )
    private = client.post(
        "/api/v1/reference-audio/import",
        json={"url": "http://127.0.0.1/a.wav"},
    )
    local = client.post(
        "/api/v1/reference-audio/import",
        json={"url": "https://localhost/a.wav"},
    )

    assert unsupported.status_code == 422
    assert private.status_code == 422
    assert local.status_code == 422


def test_reference_import_rejects_oversize_adapter_result(client: TestClient) -> None:
    services = client.app.state.services
    limited_settings = replace(services.settings, max_upload_bytes=4)
    services.reference_imports = ReferenceImportService(
        limited_settings,
        resolver=public_resolver,
        direct_adapter=lambda _url: ImportedReference(
            content=b"12345",
            filename="too-large.wav",
            media_type="audio/wav",
            source_type="direct_url",
            title="Too large",
        ),
    )

    response = client.post(
        "/api/v1/reference-audio/import",
        json={"url": "https://example.com/too-large.wav"},
    )

    assert response.status_code == 413
    assert response.json()["status"] == "file_too_large"


def post_evaluation(
    client: TestClient,
    reference: bytes,
    performance: bytes,
    *,
    clip_duration_seconds: float = 5.0,
) -> object:
    return client.post(
        "/api/v1/evaluations",
        data={
            "clip_start_seconds": "0",
            "clip_duration_seconds": str(clip_duration_seconds),
            "performance_start_seconds": "0",
        },
        files={
            "reference": ("reference.wav", reference, "audio/wav"),
            "performance": ("performance.wav", performance, "audio/wav"),
        },
    )


def public_resolver(_hostname: str) -> list[ipaddress.IPv4Address]:
    return [ipaddress.ip_address("8.8.8.8")]


def make_wav(frequency: float, duration_seconds: float, *, amplitude: float = 0.45) -> bytes:
    sample_rate = 16_000
    frame_count = int(sample_rate * duration_seconds)
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        frames = bytearray()
        for index in range(frame_count):
            sample = amplitude * math.sin(2 * math.pi * frequency * (index / sample_rate))
            value = int(max(-1.0, min(1.0, sample)) * 32767)
            frames.extend(value.to_bytes(2, "little", signed=True))
        writer.writeframes(bytes(frames))
    return output.getvalue()
