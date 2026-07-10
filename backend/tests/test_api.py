from __future__ import annotations

import io
import ipaddress
import math
import sqlite3
import wave
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from seekphony_backend.application import create_app
from seekphony_backend.core.config import Settings
from seekphony_backend.db import Database
from seekphony_backend.services.reference_imports import ImportedReference, ReferenceImportService

DEVICE_A = "11111111-1111-4111-8111-111111111111"
DEVICE_B = "22222222-2222-4222-8222-222222222222"
ADMIN_TOKEN = "test-admin-token"
LEGACY_SQLITE_SCHEMA = """
CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    reference_filename TEXT NOT NULL,
    performance_filename TEXT NOT NULL,
    reference_sha256 TEXT NOT NULL,
    performance_sha256 TEXT NOT NULL,
    clip_start_seconds REAL NOT NULL,
    clip_duration_seconds REAL NOT NULL,
    performance_start_seconds REAL NOT NULL,
    overall_score REAL NOT NULL,
    pitch_score REAL NOT NULL,
    rhythm_score REAL NOT NULL,
    stability_score REAL NOT NULL,
    coverage_score REAL NOT NULL,
    audio_quality_score REAL NOT NULL,
    key_shift_semitones INTEGER,
    pitch_error_cents REAL,
    timing_offset_ms REAL,
    voiced_coverage REAL NOT NULL,
    confidence REAL NOT NULL,
    metrics_json TEXT NOT NULL,
    segments_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    explanation_status TEXT NOT NULL,
    explanation_error TEXT,
    explanation_json TEXT
);
"""


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(make_settings(tmp_path)))


def make_settings(tmp_path: Path, *, admin_token: str | None = ADMIN_TOKEN) -> Settings:
    return Settings(
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
        reference_import_timeout_seconds=30.0,
        admin_token=admin_token,
        cors_origins=("*",),
    )


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

    listed = client.get("/api/v1/evaluations", headers=device_headers())
    fetched = client.get(f"/api/v1/evaluations/{evaluation_id}", headers=device_headers())

    assert listed.status_code == 200
    assert listed.json()["evaluations"][0]["evaluation_id"] == evaluation_id
    assert fetched.status_code == 200
    assert fetched.json()["evaluation_id"] == evaluation_id


def test_evaluation_history_delete_and_clear(client: TestClient) -> None:
    first = post_evaluation(client, make_wav(440.0, 6.0), make_wav(440.0, 6.0))
    second = post_evaluation(client, make_wav(440.0, 6.0), make_wav(493.883, 6.0))
    first_id = first.json()["evaluation_id"]

    deleted = client.delete(f"/api/v1/evaluations/{first_id}", headers=device_headers())
    missing = client.get(f"/api/v1/evaluations/{first_id}", headers=device_headers())
    missing_delete = client.delete("/api/v1/evaluations/99999", headers=device_headers())
    cleared = client.delete("/api/v1/evaluations", headers=device_headers())
    listed = client.get("/api/v1/evaluations", headers=device_headers())

    assert second.status_code == 200
    assert deleted.status_code == 200
    assert deleted.json()["deleted_count"] == 1
    assert missing.status_code == 404
    assert missing_delete.status_code == 404
    assert cleared.status_code == 200
    assert cleared.json()["deleted_count"] == 1
    assert listed.json()["evaluations"] == []


def test_evaluation_history_is_scoped_by_device(client: TestClient) -> None:
    first = post_evaluation(
        client,
        make_wav(440.0, 6.0),
        make_wav(440.0, 6.0),
        device_id=DEVICE_A,
    )
    second = post_evaluation(
        client,
        make_wav(440.0, 6.0),
        make_wav(493.883, 6.0),
        device_id=DEVICE_B,
    )
    first_id = first.json()["evaluation_id"]
    second_id = second.json()["evaluation_id"]

    listed_a = client.get("/api/v1/evaluations", headers=device_headers(DEVICE_A))
    listed_b = client.get("/api/v1/evaluations", headers=device_headers(DEVICE_B))
    cross_get = client.get(f"/api/v1/evaluations/{first_id}", headers=device_headers(DEVICE_B))
    cross_delete = client.delete(
        f"/api/v1/evaluations/{first_id}",
        headers=device_headers(DEVICE_B),
    )
    clear_b = client.delete("/api/v1/evaluations", headers=device_headers(DEVICE_B))
    listed_a_after_clear = client.get("/api/v1/evaluations", headers=device_headers(DEVICE_A))
    listed_b_after_clear = client.get("/api/v1/evaluations", headers=device_headers(DEVICE_B))

    assert listed_a.json()["evaluations"][0]["evaluation_id"] == first_id
    assert listed_b.json()["evaluations"][0]["evaluation_id"] == second_id
    assert cross_get.status_code == 404
    assert cross_delete.status_code == 404
    assert clear_b.status_code == 200
    assert clear_b.json()["deleted_count"] == 1
    assert [item["evaluation_id"] for item in listed_a_after_clear.json()["evaluations"]] == [
        first_id
    ]
    assert listed_b_after_clear.json()["evaluations"] == []


def test_evaluation_history_requires_valid_device_header(client: TestClient) -> None:
    missing = post_evaluation_without_device_header(
        client,
        make_wav(440.0, 6.0),
        make_wav(440.0, 6.0),
    )
    invalid = client.get(
        "/api/v1/evaluations",
        headers={"X-Seekphony-Device-ID": "not-a-uuid"},
    )

    assert missing.status_code == 422
    assert missing.json()["status"] == "validation_error"
    assert invalid.status_code == 422
    assert invalid.json()["status"] == "validation_error"


def test_admin_global_clear_requires_token_and_clears_all_devices(client: TestClient) -> None:
    post_evaluation(client, make_wav(440.0, 6.0), make_wav(440.0, 6.0), device_id=DEVICE_A)
    post_evaluation(client, make_wav(440.0, 6.0), make_wav(493.883, 6.0), device_id=DEVICE_B)

    missing = client.delete("/api/v1/admin/evaluations")
    wrong = client.delete(
        "/api/v1/admin/evaluations",
        headers={"X-Seekphony-Admin-Token": "wrong"},
    )
    cleared = client.delete(
        "/api/v1/admin/evaluations",
        headers={"X-Seekphony-Admin-Token": ADMIN_TOKEN},
    )
    listed_a = client.get("/api/v1/evaluations", headers=device_headers(DEVICE_A))
    listed_b = client.get("/api/v1/evaluations", headers=device_headers(DEVICE_B))

    assert missing.status_code == 403
    assert missing.json()["status"] == "forbidden"
    assert wrong.status_code == 403
    assert wrong.json()["status"] == "forbidden"
    assert cleared.status_code == 200
    assert cleared.json()["deleted_count"] == 2
    assert listed_a.json()["evaluations"] == []
    assert listed_b.json()["evaluations"] == []


def test_admin_global_clear_can_be_disabled(tmp_path: Path) -> None:
    disabled_client = TestClient(create_app(make_settings(tmp_path, admin_token=None)))

    response = disabled_client.delete(
        "/api/v1/admin/evaluations",
        headers={"X-Seekphony-Admin-Token": ADMIN_TOKEN},
    )

    assert response.status_code == 403
    assert response.json()["status"] == "admin_disabled"


def test_sqlite_migration_adds_device_hash_column(tmp_path: Path) -> None:
    database_path = tmp_path / "seekphony.sqlite3"
    with sqlite3.connect(database_path) as conn:
        conn.executescript(LEGACY_SQLITE_SCHEMA)

    Database(make_settings(tmp_path)).initialize()

    with sqlite3.connect(database_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(evaluations)")}
        indexes = {row[1] for row in conn.execute("PRAGMA index_list(evaluations)")}

    assert "device_id_hash" in columns
    assert "idx_evaluations_device_created_at" in indexes


def test_postgres_create_evaluation_returns_inserted_id(tmp_path: Path) -> None:
    database = Database(
        replace(
            make_settings(tmp_path),
            database_url="postgresql://seekphony:test@example.com:5432/seekphony",
        )
    )
    cursor = FakePostgresCursor({"id": 42})

    @contextmanager
    def fake_postgres_transaction() -> Iterator[FakePostgresConnection]:
        yield FakePostgresConnection(cursor)

    database.postgres_transaction = fake_postgres_transaction  # type: ignore[method-assign]

    evaluation_id = database.create_evaluation(evaluation_row())

    assert evaluation_id == 42
    assert cursor.executed_sql is not None
    assert "RETURNING id" in cursor.executed_sql


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


def test_reference_import_normalizes_youtube_share_and_shorts_urls(client: TestClient) -> None:
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

    urls = [
        "https://www.youtube.com/watch?v=7wtfhZwyrcc&list=RD7wtfhZwyrcc&start_radio=1",
        "https://www.youtube.com/shorts/ixQwMYQZ9W8",
        "https://youtu.be/7wtfhZwyrcc?si=NJmun_IjWKetKPHh",
    ]

    for url in urls:
        response = client.post("/api/v1/reference-audio/import", json={"url": url})
        assert response.status_code == 200

    assert calls == [
        "https://www.youtube.com/watch?v=7wtfhZwyrcc",
        "https://www.youtube.com/watch?v=ixQwMYQZ9W8",
        "https://www.youtube.com/watch?v=7wtfhZwyrcc",
    ]


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
    device_id: str = DEVICE_A,
) -> object:
    return client.post(
        "/api/v1/evaluations",
        headers=device_headers(device_id),
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


def post_evaluation_without_device_header(
    client: TestClient,
    reference: bytes,
    performance: bytes,
) -> object:
    return client.post(
        "/api/v1/evaluations",
        data={
            "clip_start_seconds": "0",
            "clip_duration_seconds": "5.0",
            "performance_start_seconds": "0",
        },
        files={
            "reference": ("reference.wav", reference, "audio/wav"),
            "performance": ("performance.wav", performance, "audio/wav"),
        },
    )


def device_headers(device_id: str = DEVICE_A) -> dict[str, str]:
    return {"X-Seekphony-Device-ID": device_id}


def public_resolver(_hostname: str) -> list[ipaddress.IPv4Address]:
    return [ipaddress.ip_address("8.8.8.8")]


def evaluation_row() -> dict[str, Any]:
    return {
        "device_id_hash": "device-hash",
        "created_at": "2026-07-09T00:00:00+00:00",
        "reference_filename": "reference.wav",
        "performance_filename": "performance.wav",
        "reference_sha256": "reference-sha",
        "performance_sha256": "performance-sha",
        "clip_start_seconds": 0.0,
        "clip_duration_seconds": 5.0,
        "performance_start_seconds": 0.0,
        "overall_score": 90.0,
        "pitch_score": 90.0,
        "rhythm_score": 90.0,
        "stability_score": 90.0,
        "coverage_score": 90.0,
        "audio_quality_score": 90.0,
        "key_shift_semitones": 0,
        "pitch_error_cents": 0.0,
        "timing_offset_ms": 0.0,
        "voiced_coverage": 0.9,
        "confidence": 0.9,
        "metrics_json": {"confidence": 0.9},
        "segments_json": [],
        "warnings_json": [],
        "explanation_status": "unavailable",
        "explanation_error": "Gemini API key is not configured.",
        "explanation_json": None,
    }


class FakePostgresConnection:
    def __init__(self, cursor: FakePostgresCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> FakePostgresCursor:
        return self._cursor


class FakePostgresCursor:
    def __init__(self, row: dict[str, int]) -> None:
        self.row = row
        self.executed_sql: str | None = None

    def __enter__(self) -> FakePostgresCursor:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, sql: str, _values: tuple[object, ...]) -> None:
        self.executed_sql = sql

    def fetchone(self) -> dict[str, int]:
        return self.row


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
