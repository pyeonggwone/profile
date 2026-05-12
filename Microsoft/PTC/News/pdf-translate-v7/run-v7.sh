#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

mkdir -p input output work

PYTHON_BIN_FROM_ENV="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN_FROM_ENV" ] && [ -f .env ]; then
  PYTHON_BIN_FROM_ENV="$(grep -E '^PYTHON_BIN=' .env 2>/dev/null | tail -1 | cut -d '=' -f2- || true)"
fi
PYTHON_BIN_FROM_ENV="$(printf '%s' "$PYTHON_BIN_FROM_ENV" | tr -d '\r' | sed -e 's/^ *//' -e 's/ *$//' -e 's/^"//' -e 's/"$//')"

if [ -z "$PYTHON_BIN_FROM_ENV" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN_FROM_ENV=".venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN_FROM_ENV="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN_FROM_ENV="python"
  fi
fi

if [ -z "$PYTHON_BIN_FROM_ENV" ]; then
  echo "[error] python is required" >&2
  exit 1
fi

if [ "${1:-}" = "bootstrap" ]; then
  if [ ! -d .venv ]; then
    "$PYTHON_BIN_FROM_ENV" -m venv --copies .venv
  fi
  . .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  exit 0
fi

export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON_BIN_FROM_ENV" -m pdf_translate_v7.pipeline "$@"
