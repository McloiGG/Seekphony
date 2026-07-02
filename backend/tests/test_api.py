from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from seekphony_backend.core.config import Settings
from seekphony_backend.main import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    repo_root = Path(__file__).resolve().parents[2]
    settings = Settings(
        app_name="Seekphony Test Backend",
        api_prefix="/api/v1",
        repo_root=repo_root,
        data_dir=tmp_path,
        database_path=tmp_path / "seekphony.sqlite3",
        seed_path=repo_root / "data" / "seeds" / "songs.json",
        upload_dir=tmp_path / "uploads",
        max_upload_bytes=1024 * 1024,
        provider_timeout_seconds=0.1,
        provider_retry_count=0,
        provider_retry_delay_seconds=0,
        gemini_api_key=None,
        gemini_model="gemini-2.5-flash",
        enable_shazamio=False,
        cors_origins=("*",),
    )
    return TestClient(create_app(settings))


def test_health_and_seeded_songs(client: TestClient) -> None:
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    songs = client.get("/api/v1/songs")
    assert songs.status_code == 200
    assert len(songs.json()) >= 15


def test_text_search_found_with_local_fallback(client: TestClient) -> None:
    response = client.post("/api/v1/search/text", json={"query": "Blinding Lights by The Weeknd"})
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "found"
    assert body["song"]["title"] == "Blinding Lights"
    assert body["provider"]["fallback_used"] is True


def test_text_search_alias_reuses_logic(client: TestClient) -> None:
    response = client.get("/api/search", params={"q": "Adele - Someone Like You"})
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "found"
    assert body["song"]["artist"] == "Adele"


def test_add_song_and_duplicate_detection(client: TestClient) -> None:
    payload = {
        "title": "Midnight City",
        "artist": "M83",
        "genre": "Synth-pop",
        "duration_seconds": 244,
        "source_url": "https://example.com/m83/midnight-city",
    }
    created = client.post("/api/v1/songs", json=payload)
    duplicate = client.post("/api/v1/songs", json=payload)

    assert created.status_code == 200
    assert created.json()["status"] == "created"
    assert duplicate.status_code == 409
    assert duplicate.json()["status"] == "duplicate_detected"


def test_extract_file_and_audio_search_accept_uploaded_blob(client: TestClient) -> None:
    files = {"file": ("The Weeknd - Blinding Lights.webm", b"fake-audio", "audio/webm")}
    extracted = client.post("/api/v1/extract/file", files=files)

    assert extracted.status_code == 200
    assert extracted.json()["title"] == "Blinding Lights"
    assert extracted.json()["artist"] == "The Weeknd"
    assert extracted.json()["file_sha256"]

    audio = client.post(
        "/api/v1/search/audio",
        files={"file": ("The Weeknd - Blinding Lights.webm", b"fake-audio", "audio/webm")},
    )
    body = audio.json()
    assert audio.status_code == 200
    assert body["status"] == "found"
    assert body["song"]["title"] == "Blinding Lights"


def test_play_session_and_analytics(client: TestClient) -> None:
    song_id = client.get("/api/v1/songs").json()[0]["id"]
    started = client.post("/api/v1/plays/start", json={"song_id": song_id})
    stopped = client.post(f"/api/v1/plays/{started.json()['session_id']}/stop")
    analytics = client.get("/api/v1/analytics")

    assert started.status_code == 200
    assert stopped.status_code == 200
    assert stopped.json()["duration_seconds"] >= 1
    assert analytics.status_code == 200
    assert analytics.json()["total_listening_seconds"] >= 1
    assert analytics.json()["recent_sessions"]


def test_play_event_alias(client: TestClient) -> None:
    song_id = client.get("/api/v1/songs").json()[0]["id"]
    response = client.post("/api/analytics/play", json={"song_id": song_id, "duration_seconds": 42})

    assert response.status_code == 200
    assert response.json()["status"] == "recorded"
