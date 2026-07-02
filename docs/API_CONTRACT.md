# Seekphony Backend API Contract

The canonical API prefix is `/api/v1`. Compatibility aliases exist for the current frontend prototype, but they must reuse the same backend services and business logic.

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

Important statuses: `found`, `candidates`, `not_found`, `created`, `duplicate_detected`, `validation_error`, `provider_unavailable`, `unsupported_source`, and `extraction_failed`.

## Health

`GET /api/v1/health`

Aliases: `GET /health`

Returns service status and provider configuration flags.

## Songs

`GET /api/v1/songs`

Aliases: `GET /songs`, `GET /api/songs`

Returns the catalog sorted by title.

`POST /api/v1/songs`

Aliases: `POST /api/songs`, `POST /api/songs/add`

Accepts either JSON:

```json
{
  "title": "Blinding Lights",
  "artist": "The Weeknd",
  "genre": "Synth-pop",
  "duration_seconds": 200,
  "source_url": "https://example.com/song"
}
```

or multipart form fields with optional `file`.

Duplicate response uses HTTP 409:

```json
{
  "status": "duplicate_detected",
  "message": "Duplication detected!",
  "details": {
    "duplicate": {}
  },
  "retryable": false,
  "fallback_used": false
}
```

Duplicates are checked by normalized title+artist, normalized source URL, and uploaded file SHA-256 when present.

## Search

`POST /api/v1/search/text`

Body:

```json
{
  "query": "Blinding Lights by The Weeknd"
}
```

Alias: `GET /api/search?q=Blinding%20Lights`

Returns:

```json
{
  "status": "found",
  "query_type": "text",
  "provider": {
    "provider": "local_text_extractor",
    "stage": "text_extraction",
    "fallback_used": true
  },
  "extracted": {},
  "song": {},
  "candidates": [],
  "message": "Match found."
}
```

`POST /api/v1/search/audio`

Alias: `POST /api/search/audio`

Accepts multipart field `file` or `audio`. Audio capture is a frontend responsibility; the backend only receives uploaded blobs/files. Shazamio recognition is optional and falls back to local file metadata/hash behavior.

Search statuses:

- `found`: high-confidence match, `song` is populated.
- `candidates`: no exact match, `candidates` contains ranked options.
- `not_found`: no usable match, frontend should offer add-song flow.

## Metadata Extraction

`POST /api/v1/extract/file`

Alias: `POST /api/extract/file`

Accepts multipart field `file`. Core behavior is SHA-256 hashing and filename normalization. Audio tag extraction is optional when `mutagen` is installed.

`POST /api/v1/extract/url`

Alias: `POST /api/extract/url`

Body:

```json
{
  "url": "https://example.com/artist-song"
}
```

URL extraction is best-effort. Rich extraction may use optional dependencies; otherwise the backend returns URL-normalized fallback metadata.

## Playback And Analytics

`POST /api/v1/plays/start`

Body:

```json
{
  "song_id": 1
}
```

`POST /api/v1/plays/{session_id}/stop`

Stops a session and increments play count/listening time.

`POST /api/v1/plays/event`

Alias: `POST /api/analytics/play`

One-shot compatibility endpoint for frontend play buttons:

```json
{
  "song_id": 1,
  "duration_seconds": 180
}
```

`GET /api/v1/analytics`

Aliases: `GET /analytics`, `GET /api/analytics`

Returns top songs, total listening seconds/minutes, recent sessions, recent recognitions, and last recognized song.
