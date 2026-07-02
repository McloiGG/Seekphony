# Architecture

## System Flow

User input
→ Frontend validation
→ FastAPI backend
→ Data service
→ AI matching service
→ Structured response
→ Frontend result display
→ Analytics update

## Layers

### Frontend

Handles UI, user input, alerts, modals, charts, and API calls.

### Backend API

Exposes routes and validates requests.

### Data Layer

Loads, stores, and updates the song catalog and analytics data.

### AI Layer

Performs text/audio matching, confidence scoring, duplicate detection, and fallback handling.

### Integration Layer

Handles environment variables, configuration, and service coordination.

## Boundary Rules

- Frontend must not fake backend results.
- Route handlers should delegate to services.
- AI logic should not be mixed into UI code.
- Data storage logic should not be duplicated across routes.