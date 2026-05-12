#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ] && [ -f .env.example ]; then
  echo "[init] .env not found, copying from .env.example"
  cp .env.example .env
fi

mkdir -p input input/done output work

DEFAULT_VENV_DIR=".venv"
if grep -qi microsoft /proc/version 2>/dev/null && pwd | grep -q '^/mnt/'; then
  DEFAULT_VENV_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/pdf-translate-v12/.venv"
fi
VENV_DIR="${VENV_DIR:-$DEFAULT_VENV_DIR}"

PYTHON_BIN_FROM_ENV="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN_FROM_ENV" ] && [ -f .env ]; then
  PYTHON_BIN_FROM_ENV="$(grep -E '^PYTHON_BIN=' .env 2>/dev/null | tail -1 | cut -d '=' -f2- || true)"
fi
PYTHON_BIN_FROM_ENV="$(printf '%s' "$PYTHON_BIN_FROM_ENV" | tr -d '\r' | sed -e 's/^ *//' -e 's/ *$//' -e 's/^"//' -e 's/"$//')"

if [ -z "$PYTHON_BIN_FROM_ENV" ]; then
  if [ -x "$VENV_DIR/bin/python" ]; then
    PYTHON_BIN_FROM_ENV="$VENV_DIR/bin/python"
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
  mkdir -p "$(dirname "$VENV_DIR")"
  if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON_BIN_FROM_ENV" -m venv --copies "$VENV_DIR"
  fi
  . "$VENV_DIR/bin/activate"
  echo "[bootstrap] venv=$VENV_DIR"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  exit 0
fi

export PYTHONPATH="$(pwd)/src"
exec "$PYTHON_BIN_FROM_ENV" -m pdf_translate_v12.pipeline "$@"
