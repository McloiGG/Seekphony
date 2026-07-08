FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    SEEKPHONY_REPO_ROOT=/app \
    SEEKPHONY_DATA_DIR=/app/var \
    SEEKPHONY_DATABASE_PATH=/app/var/seekphony.sqlite3

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.8.22

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/uv.lock /app/backend/uv.lock
COPY backend/src /app/backend/src

WORKDIR /app/backend

RUN uv sync --no-dev --frozen

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "seekphony_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
