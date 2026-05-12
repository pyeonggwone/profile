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

# v1 의 pdftr CLI 가 빌드되어 있는지 확인 (없어도 PDF_ENGINE_BIN 으로 외부 경로 지정 가능)
if [ -z "${PDF_ENGINE_BIN:-}" ] \
   && [ ! -x "pdf-engine/target/release/pdftr" ] \
   && [ ! -x "../pdf-translate-v1/target/release/pdftr" ]; then
  echo "[warn] pdftr 바이너리를 찾을 수 없습니다."
  echo "       INSTALL.md 5단계를 참조해 다음 명령을 실행하세요:"
  echo "         (cd ../pdf-translate-v1 && cargo build --release -p pdftr_cli)"
fi

exec node src/index.mjs "$@"
