from __future__ import annotations

import json
import asyncio
import io
import os
import time
import base64
import hmac
import hashlib
from typing import TYPE_CHECKING, Any
import requests

from fastapi import FastAPI, Request, File, UploadFile, Query, status
from fastapi.responses import JSONResponse, FileResponse

from seekphony_backend.core.errors import AppError
from seekphony_backend.core.normalization import normalize_url
from seekphony_backend.schemas import (
    SongCreate,
    SongOut,
    UrlExtractRequest,
    AnalyticsResponse,
)

if TYPE_CHECKING:
    from seekphony_backend.main import AppServices


def register_routes(app: FastAPI, services: AppServices) -> None:
    api_prefix = services.settings.api_prefix
    
    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": services.settings.app_name,
            "api_prefix": api_prefix,
        }
        
    @app.get(f"{api_prefix}")
    async def api_root() -> dict[str, Any]:
        return {
            "status": "active",
            "message": f"Welcome to the {services.settings.app_name} API layer v1.",
            "documentation": "/docs"
        }

    @app.get(f"{api_prefix}/songs")
    async def list_songs() -> list[SongOut]:
        return services.catalog.list_songs()

    @app.get(f"{api_prefix}/songs/stream/{{song_id}}")
    async def stream_song(song_id: int):
        song = services.catalog.get_song(song_id)
        if song.file_path and os.path.exists(song.file_path):
            return FileResponse(song.file_path, media_type="audio/mpeg")
            
        fallback_audio = services.settings.data_dir / "seeds" / "sample.mp3"
        if fallback_audio.exists():
            return FileResponse(fallback_audio, media_type="audio/mpeg")
            
        raise AppError(404, "not_found", "Audio source track file could not be located on server storage.")

    @app.delete(f"{api_prefix}/songs/{{song_id}}")
    async def delete_song(song_id: int):
        success = services.catalog.delete_song(song_id)
        if not success:
            raise AppError(404, "not_found", f"Song track with ID {song_id} could not be located.")
        return {"status": "success", "message": f"Track ID {song_id} cleanly purged from database."}
    
    @app.get(f"{api_prefix}/search")
    async def search_text(q: str = Query(..., min_length=1)) -> dict[str, Any]:
        result = await services.search.search_text(q)
        if result.status == "found" and result.song:
            return {"song": result.song}
        raise AppError(404, "not_found", result.message or f"No exact match found for: '{q}'")

    # 🚀 FIX: FULLY FUNCTIONAL ACRCLOUD RECOGNITION SEARCH ENDPOINT (NO WINDOWS COMPILATION CRASHES)
    @app.post(f"{api_prefix}/search/audio")
    async def search_audio(file: UploadFile = File(...)) -> dict[str, Any]:
        """Sends the browser recording directly to ACRCloud via signed HTTP REST API without SDK binaries"""
        try:
            content = await file.read()
            _validate_upload(content, services.settings.max_upload_bytes)
            
            # --- ☁️ CONFIGURING YOUR ACRCLOUD CONSOLE KEYS ---
            host = "identify-ap-southeast-1.acrcloud.com".strip()
            access_key = "eee0bb77e41fc3e62f57838bf435ddaa".strip()
            access_secret = "4f1kMWNlicePoMTFZEZWctFbYU8HQ5ClDRx1Q04G".strip()

            requrl = f"https://{host}/v1/identify"
            http_method = "POST"
            http_uri = "/v1/identify"
            data_type = "audio"
            signature_version = "1"
            timestamp = str(int(time.time()))

            string_to_sign = f"{http_method}\n{http_uri}\n{access_key}\n{data_type}\n{signature_version}\n{timestamp}"
            sign = base64.b64encode(
                hmac.new(access_secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha1).digest()
            ).decode('utf-8')

            files_payload = {
                'sample': (file.filename, content, file.content_type)
            }
            data_payload = {
                'access_key': access_key,
                'sample_bytes': len(content),
                'timestamp': timestamp,
                'signature': sign,
                'data_type': data_type,
                'signature_version': signature_version
            }

            response = requests.post(requrl, data=data_payload, files=files_payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                acr_status = result.get("status", {})
                print(f"--- 🤖 ACRCLOUD AI DIAGNOSTICS ---")
                print(f"AI Response Code: {acr_status.get('code')}")
                print(f"AI Message String: {acr_status.get('msg')}")
                print(f"----------------------------------")
                
                # Check if custom humming registry matched or generic music database matched
                if acr_status.get("code") == 0 and "metadata" in result:
                    metadata = result["metadata"]
                    track_info = None
                    
                    if "humming" in metadata and metadata["humming"]:
                        track_info = metadata["humming"][0]
                    elif "custom_files" in metadata and metadata["custom_files"]:
                        track_info = metadata["custom_files"][0]
                    elif "music" in metadata and metadata["music"]:
                        track_info = metadata["music"][0]
                        
                    if track_info:
                        detected_title = track_info.get("title", "Unknown Track")
                        
                        # Handle array structure variations for artist list strings safely
                        if "artists" in track_info and isinstance(track_info["artists"], list) and len(track_info["artists"]) > 0:
                            detected_artist = track_info["artists"][0].get("name", "Unknown Artist")
                        else:
                            detected_artist = track_info.get("artist", "Unknown Artist")
                        
                        # 🌐 Bypassing local DB lookups to route straight to your custom Frontend YouTube engine!
                        matched_song = {
                            "id": 999, 
                            "title": detected_title,
                            "artist": detected_artist,
                            "genre": "Identified Humming Track",
                            "play_count": 0
                        }
                        print(f"⚠️ Track identified: '{detected_title}' by {detected_artist}. Offloading to Frontend YouTube pipeline.")
                        return {"song": matched_song}

            # If it gets past the 'if track_info' block or response fails, raise the 404 explicitly
            raise AppError(404, "not_found", "Acoustic signature could not be identified inside cloud charts.")

        except AppError:
            raise
        except Exception as e:
            print(f"ACRCloud API gateway connection failure: {e}")
            raise AppError(500, "processing_error", "Audio recognition network timed out.")

    @app.post(f"{api_prefix}/songs", status_code=status.HTTP_201_CREATED)
    async def add_song(request: Request) -> dict[str, Any]:
        payload, upload = await _parse_song_payload(request)
        song_create = SongCreate(
            title=payload.get("title", ""),
            artist=payload.get("artist", ""),
            genre=payload.get("genre", "Unknown"),
            duration_seconds=payload.get("duration_seconds"),
            source_url=payload.get("source_url")
        )
        if upload:
            content = await upload.read()
            _validate_upload(content, services.settings.max_upload_bytes)
        
        new_song = services.catalog.add_song(song_create)
        return {"song": new_song}

    @app.post(f"{api_prefix}/analytics/play")
    async def track_one_shot_playback(request: Request) -> dict[str, Any]:
        try:
            body = await request.json()
            song_id = int(body.get("song_id"))
            duration_seconds = int(body.get("duration_seconds", 180))
        except Exception as exc:
            raise AppError(422, "validation_error", "Invalid analytics play payload body context.") from exc

        start_res = services.analytics.start_session(song_id)
        with services.analytics.db.transaction() as conn:
            conn.execute(
                "UPDATE play_sessions SET status = 'completed' WHERE id = ?",
                (start_res.session_id,)
            )
            services.analytics._increment_song(conn, song_id, duration_seconds)
            
        updated_song = services.catalog.get_song(song_id)
        return {"song": updated_song}

    @app.post(f"{api_prefix}/extract/url")
    async def extract_url(payload: UrlExtractRequest) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        url_str = str(payload.url)
        metadata = await loop.run_in_executor(None, services.metadata.extract_from_url, url_str)
        return {
            "title": metadata.title,
            "artist": metadata.artist,
            "genre": metadata.genre or "Web Stream"
        }

    @app.post(f"{api_prefix}/extract/file")
    async def extract_file(file: UploadFile = File(...)) -> dict[str, Any]:
        content = await file.read()
        _validate_upload(content, services.settings.max_upload_bytes)
        metadata = services.metadata.extract_from_file(content, file.filename)
        return {
            "title": metadata.title,
            "artist": metadata.artist,
            "genre": metadata.genre or "Audio Tracking File"
        }


async def _parse_song_payload(request: Request) -> tuple[dict[str, Any], UploadFile | None]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        payload = {
            "title": _empty_to_none(form.get("title")),
            "artist": _empty_to_none(form.get("artist")),
            "genre": _empty_to_none(form.get("genre")),
            "duration_seconds": _int_or_none(form.get("duration_seconds")),
            "source_url": _empty_to_none(form.get("source_url")),
        }
        return {k: v for k, v in payload.items() if v is not None}, (upload if isinstance(upload, UploadFile) else None)

    try:
        raw = await request.body()
        if not raw:
            raise ValueError("Empty body definition context.")
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise AppError(422, "validation_error", "Expected JSON or multipart song payload.") from exc
    return payload, None


def _empty_to_none(value: Any) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _int_or_none(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(value)


def _validate_upload(content: bytes, max_bytes: int) -> None:
    if not content:
        raise AppError(422, "validation_error", "Uploaded file stream cannot be empty.")
    if len(content) > max_bytes:
        raise AppError(413, "payload_too_large", f"File dimensions exceed permitted storage limits ({max_bytes // (1024 * 1024)}MB).")