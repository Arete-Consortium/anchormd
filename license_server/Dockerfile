# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

COPY license_server/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /install /usr/local

COPY license_server/ ./license_server/

ENV PYTHONPATH="/app"
ENV CMDF_DB_PATH="/data/license_server.db"

RUN useradd -m -u 1000 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

ENV PORT=8000
CMD ["sh", "-c", "exec uvicorn license_server.main:app --host 0.0.0.0 --port $PORT"]
