FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    SEEKPHONY_REPO_ROOT=/app \
    SEEKPHONY_DATA_DIR=/app/var \
    SEEKPHONY_DATABASE_PATH=/app/var/seekphony.sqlite3 \
    SEEKPHONY_SEED_PATH=/app/data/seeds/songs.json \
    SEEKPHONY_UPLOAD_DIR=/app/var/uploads

WORKDIR /app

RUN pip install --no-cache-dir uv==0.8.22

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/uv.lock /app/backend/uv.lock
COPY backend/src /app/backend/src
COPY data/seeds /app/data/seeds

WORKDIR /app/backend

RUN uv sync --no-dev --frozen

RUN mkdir -p /app/var/uploads

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "seekphony_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
