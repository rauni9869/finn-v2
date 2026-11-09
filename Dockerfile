# One container for the whole app: build the frontend, then serve it from FastAPI.
# Used by Hugging Face Spaces (Docker SDK), which expects the app on port 7860.

FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --include=dev
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
# Spaces run the container as user 1000, so it needs its own writable home for the cache
RUN useradd -m -u 1000 finn
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=frontend /build/dist frontend/dist
RUN mkdir -p /app/.cache && chown -R finn /app
USER finn

ENV PYTHONPATH=/app/backend \
    FINN_CACHE_DIR=/app/.cache \
    PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["uvicorn", "finn.main:app", "--host", "0.0.0.0", "--port", "7860"]
