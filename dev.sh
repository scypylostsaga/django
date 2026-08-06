#!/bin/bash
# Dev launcher used by the preview: ensures deps are installed, then runs Django.
set -e

cd "$(dirname "$0")"

PORT="${PORT:-3000}"

# Create the virtual environment and install dependencies if missing.
if [ ! -x ".venv/bin/python" ]; then
  echo "[dev] Creating virtual environment..."
  uv venv --python 3.13 .venv
  .venv/bin/python -m ensurepip >/dev/null 2>&1 || true
  .venv/bin/python -m pip install -r requirements.txt
fi

# Apply any pending migrations against the configured database (Neon).
.venv/bin/python manage.py migrate --noinput || true

echo "[dev] Starting Django on port ${PORT}..."
exec .venv/bin/python manage.py runserver "0.0.0.0:${PORT}"
