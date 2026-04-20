#!/bin/bash
set -e

DB_PATH="${ANMD_DB_PATH:-/data/license_server.db}"

if [ -n "$LITESTREAM_REPLICA_BUCKET" ]; then
    if [ -f "$DB_PATH" ]; then
        echo "Database already exists at $DB_PATH, skipping restore."
    else
        echo "Restoring database from Litestream replica..."
        litestream restore -if-replica-exists \
            -config /app/license_server/litestream.yml \
            "$DB_PATH"
    fi
    echo "Starting with Litestream replication..."
    exec litestream replicate \
        -exec "uvicorn license_server.main:app --host 0.0.0.0 --port 8000" \
        -config /app/license_server/litestream.yml
else
    echo "No LITESTREAM_REPLICA_BUCKET set, running without replication..."
    exec uvicorn license_server.main:app --host 0.0.0.0 --port 8000
fi
