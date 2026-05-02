#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    echo "[init] .env not found, copying from .env.example"
    cp .env.example .env
  fi
fi

if [ ! -d node_modules ]; then
  echo "[init] installing npm dependencies..."
  npm install --no-audit --no-fund
fi

mkdir -p input output work input/done

exec node src/index.mjs "$@"
