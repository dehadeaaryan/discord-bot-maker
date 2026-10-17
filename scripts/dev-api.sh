#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-sqlite:///./development.db}"
.venv/bin/alembic upgrade head
exec .venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port "${PORT:-8000}" --no-access-log
