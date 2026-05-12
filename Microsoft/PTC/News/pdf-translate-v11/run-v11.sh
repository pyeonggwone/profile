#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ] && [ -f .env.example ]; then
  echo "[init] .env not found, copying from .env.example"
  cp .env.example .env
fi

mkdir -p input input/done output work

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
  PYTHON_PURELIB="$(python - <<'PY'
import sysconfig
print(sysconfig.get_paths()["purelib"])
PY
)"
  PYTHON_PLATLIB="$(python - <<'PY'
import sysconfig
print(sysconfig.get_paths()["platlib"])
PY
)"
  if [ "$PYTHON_PURELIB" != "$PYTHON_PLATLIB" ] && printf '%s' "$PYTHON_PURELIB" | grep -q '^/mnt/'; then
    python -m pip install --upgrade --target "$PYTHON_PURELIB" -r requirements.txt
  else
    python -m pip install -r requirements.txt
  fi
  if command -v npm >/dev/null 2>&1; then
    npm install --no-audit --no-fund
  fi
  exit 0
fi

export PYTHONPATH="$(pwd)/src"
exec "$PYTHON_BIN_FROM_ENV" -m pdf_translate_v11.pipeline "$@"
