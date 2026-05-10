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

if [ -f requirements.txt ]; then
  PYTHON_BIN_FROM_ENV="${PYTHON_BIN:-}"
  if [ -z "$PYTHON_BIN_FROM_ENV" ] && [ -f .env ]; then
    PYTHON_BIN_FROM_ENV="$(grep -E '^PYTHON_BIN=' .env | tail -1 | cut -d '=' -f2-)"
  fi
  PYTHON_BIN_FROM_ENV="$(printf '%s' "$PYTHON_BIN_FROM_ENV" | tr -d '\r' | sed -e 's/^ *//' -e 's/ *$//' -e 's/^"//' -e 's/"$//')"
  if [ -z "$PYTHON_BIN_FROM_ENV" ]; then
    if command -v python3 >/dev/null 2>&1; then
      PYTHON_BIN_FROM_ENV="python3"
    elif command -v python >/dev/null 2>&1; then
      PYTHON_BIN_FROM_ENV="python"
    fi
  fi
  if [ -z "$PYTHON_BIN_FROM_ENV" ]; then
    echo "[error] python 이 설치되어 있지 않습니다. PyMuPDF 엔진을 실행할 수 없습니다." >&2
    exit 1
  fi
  if ! "$PYTHON_BIN_FROM_ENV" -c 'import fitz' >/dev/null 2>&1; then
    echo "[init] installing Python dependencies..."
    "$PYTHON_BIN_FROM_ENV" -m pip install -r requirements.txt
  fi
  export PYTHON_BIN="$PYTHON_BIN_FROM_ENV"
fi

mkdir -p input output work input/done

PDF_ENGINE_FROM_ENV="${PDF_ENGINE:-}"
if [ -z "$PDF_ENGINE_FROM_ENV" ] && [ -f .env ]; then
  PDF_ENGINE_FROM_ENV="$(grep -E '^PDF_ENGINE=' .env | tail -1 | cut -d '=' -f2-)"
fi
PDF_ENGINE_FROM_ENV="$(printf '%s' "$PDF_ENGINE_FROM_ENV" | tr -d '\r' | sed -e 's/^ *//' -e 's/ *$//' -e 's/^"//' -e 's/"$//')"
PDF_ENGINE_FROM_ENV="${PDF_ENGINE_FROM_ENV:-pymupdf}"

# pdftr CLI (Rust) 가 빌드되어 있지 않으면 자동 빌드.
# .env 의 PDF_ENGINE_BIN 이 명시되었으면 빌드를 건너뛴다.
if [ "$PDF_ENGINE_FROM_ENV" = "pdftr" ]; then
PDF_ENGINE_BIN_FROM_ENV="${PDF_ENGINE_BIN:-}"
if [ -z "$PDF_ENGINE_BIN_FROM_ENV" ] && [ -f .env ]; then
  PDF_ENGINE_BIN_FROM_ENV="$(grep -E '^PDF_ENGINE_BIN=' .env | tail -1 | cut -d '=' -f2-)"
fi
PDF_ENGINE_BIN_FROM_ENV="$(printf '%s' "$PDF_ENGINE_BIN_FROM_ENV" | tr -d '\r' | sed -e 's/^ *//' -e 's/ *$//' -e 's/^"//' -e 's/"$//')"

if [ -n "$PDF_ENGINE_BIN_FROM_ENV" ] && [ ! -x "$PDF_ENGINE_BIN_FROM_ENV" ]; then
  echo "[warn] PDF_ENGINE_BIN 이 실행 파일이 아닙니다. 자체 pdftr 빌드를 시도합니다: $PDF_ENGINE_BIN_FROM_ENV" >&2
  PDF_ENGINE_BIN_FROM_ENV=""
fi

PDFTR_BUILT=""
if [ -x "target/release/pdftr" ] || [ -x "target/debug/pdftr" ]; then
  PDFTR_BUILT="yes"
fi

if [ -z "$PDF_ENGINE_BIN_FROM_ENV" ] && [ -z "$PDFTR_BUILT" ]; then
  if ! command -v cargo >/dev/null 2>&1; then
    echo "[error] cargo 가 설치되어 있지 않습니다. INSTALL.md 의 Rust toolchain 섹션을 참조하세요." >&2
    exit 1
  fi
  echo "[init] building Rust pdftr CLI (cargo build --release -p pdftr_cli)..."
  cargo build --release -p pdftr_cli
fi
fi

exec node src/index.mjs "$@"
