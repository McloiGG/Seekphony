# Seekphony Backend API Contract

The canonical API prefix is `/api/v1`.

All error responses use this shape:

```json
{
  "status": "validation_error",
  "message": "Request validation failed.",
  "details": {},
  "retryable": false,
  "fallback_used": false
}
```

Important statuses include `validation_error`, `file_too_large`,
`unsupported_audio`, `audio_decode_failed`, `reference_import_failed`, and
`not_found`.

## Health

`GET /api/v1/health`

Alias: `GET /health`

Returns service status, configured persistence mode, provider flags, and limits:

```json
{
  "status": "ok",
  "service": "Seekphony Backend",
  "api_prefix": "/api/v1",
  "database": {
    "kind": "sqlite",
    "postgres_configured": false
  },
  "providers": {
    "gemini_configured": false
  },
  "limits": {
    "max_upload_bytes": 31457280,
    "min_clip_seconds": 5,
    "max_clip_seconds": 60
  }
}
```

## Import Reference Audio

`POST /api/v1/reference-audio/import`

Accepts JSON:

```json
{
  "url": "https://example.com/reference.mp3"
}
```

The backend imports direct audio URLs and best-effort YouTube links, validates
HTTP(S) targets, rejects local/private/reserved hosts, enforces the configured
30 MB limit, and returns the imported audio bytes without permanent storage.

Response body is binary audio. Metadata is returned in exposed headers:

- `X-Seekphony-Filename`
- `X-Seekphony-Source-Type`: `direct_url` or `youtube`
- `X-Seekphony-Title`
- `X-Seekphony-Byte-Size`

YouTube support depends on `yt-dlp` and is not guaranteed for every video.

## Create Evaluation

`POST /api/v1/evaluations`

Accepts multipart form data:

- `reference`: audio file; WAV is supported directly, other formats use `ffmpeg`
  when available.
- `performance`: uploaded or browser-recorded singing audio.
- `clip_start_seconds`: reference clip start, default `0`.
- `clip_duration_seconds`: selected clip duration, default `30`; must be within
  configured min/max.
- `performance_start_seconds`: optional performance start offset, default `0`.

Response:

```json
{
  "status": "completed",
  "evaluation_id": 1,
  "created_at": "2026-07-08T00:00:00+00:00",
  "reference_filename": "song.wav",
  "performance_filename": "take.wav",
  "clip_start_seconds": 0,
  "clip_duration_seconds": 5,
  "performance_start_seconds": 0,
  "scores": {
    "overall": 88.0,
    "pitch": 91.0,
    "rhythm": 84.0,
    "stability": 90.0,
    "coverage": 86.0,
    "audio_quality": 87.0
  },
  "metrics": {
    "key_shift_semitones": 0,
    "pitch_error_cents": 22.0,
    "timing_offset_ms": 40.0,
    "voiced_coverage": 0.86,
    "reference_voiced_ratio": 0.9,
    "performance_voiced_ratio": 0.88,
    "confidence": 0.87,
    "reference_duration_seconds": 5.0,
    "performance_duration_seconds": 5.0
  },
  "segments": [],
  "warnings": [],
  "explanation": {
    "status": "unavailable",
    "provider": "gemini",
    "error": "Gemini API key is not configured.",
    "content": null
  }
}
```

Gemini receives only structured metrics, warnings, and weak segments. If Gemini is
not configured or fails, metric scoring still returns.

## List Evaluations

`GET /api/v1/evaluations?limit=20`

Returns recent saved evaluations:

```json
{
  "status": "ok",
  "evaluations": []
}
```

## Get Evaluation

`GET /api/v1/evaluations/{evaluation_id}`

Returns the same shape as create evaluation. Missing evaluations return HTTP 404
with status `not_found`.

Saved evaluations contain scores, metrics, warnings, weak segments, Gemini state,
filenames, and clip settings. They do not contain replayable audio.

## Delete Evaluation

`DELETE /api/v1/evaluations/{evaluation_id}`

Deletes one saved metadata row:

```json
{
  "status": "ok",
  "deleted_count": 1
}
```

Missing evaluations return HTTP 404 with status `not_found`.

## Clear Evaluations

`DELETE /api/v1/evaluations`

Deletes all saved evaluation metadata rows:

```json
{
  "status": "ok",
  "deleted_count": 3
}
```
