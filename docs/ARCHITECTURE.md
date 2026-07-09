# Architecture

## System Flow

Reference upload or URL import + performance recording/upload + clip selection
-> Frontend validation
-> FastAPI multipart endpoint
-> Audio decoding and clip extraction
-> Deterministic pitch/rhythm/quality analysis
-> Optional Gemini explanation from structured metrics
-> Evaluation persistence
-> Frontend score, warnings, weak segments, and explanation display

## Layers

### Frontend

React + TypeScript SPA in `Frontend/`. Handles reference upload or URL import,
playback confirmation, clip controls, WAV microphone recording, performance
upload, readable backend-unavailable states, evaluation submission, score
display, warnings, weak segments, AI explanation state, and saved evaluation
history details/deletion.

Browser-visible configuration uses public environment variables only.

### Backend API

FastAPI service under `backend/`. It exposes health, reference import, evaluation,
and history mutation routes, validates request boundaries, delegates work to
services, and returns structured JSON or imported audio bytes.

### Data Layer

Stores evaluation records, file hashes, scores, metrics JSON, warning JSON,
problem-segment JSON, and Gemini explanation metadata. SQLite is the default local
database. `DATABASE_URL` switches deployment to Postgres.

Raw uploaded, imported, and recorded audio is not stored permanently in the MVP.

### Audio Analysis Layer

Decodes WAV directly and can use `ffmpeg` for broader formats when available.
Extracts frame-level RMS, voicing, pitch estimates, timing offset, key shift,
pitch error, stability, coverage, and audio-quality confidence.

### Reference Import Layer

Direct audio URLs are streamed through backend size and SSRF checks. Best-effort
YouTube import uses pinned `yt-dlp` and temporary files only; imported bytes are
returned to the frontend for playback and then submitted through the normal
evaluation endpoint.

### AI Layer

Gemini receives only structured scores, metrics, warnings, and weak segments. It
returns validated coaching JSON when available. If it is not configured or fails,
the backend returns deterministic metrics with `explanation.status` set to
`unavailable` or `error`.

### Integration Layer

Docker Compose uses optional `env_file` entries plus explicit environment
mappings. The frontend container uses runtime public config. The backend container
installs `ffmpeg` and keeps runtime SQLite state under `/app/var`.

## Boundary Rules

- Frontend must not fabricate successful evaluations.
- Route handlers should delegate to services.
- Audio metrics must not depend on Gemini.
- Gemini must not receive raw audio.
- URL import must not allow local, private, or reserved network targets.
- Frontend environment variables are public and must not contain secrets.
- Backend provider credentials and `DATABASE_URL` must be injected at runtime.
