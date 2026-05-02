#!/usr/bin/env bash
# epub-translate-v2 entry script (Linux / AlmaLinux 9)
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
SCRIPT="${SCRIPT_DIR}/epub_translate.mjs"

if [[ ! -f "${SCRIPT}" ]]; then
  echo "epub_translate.mjs 를 찾을 수 없음: ${SCRIPT}" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js 20+ 가 필요합니다. 설치: dnf module install -y nodejs:20" >&2
  exit 1
fi

if [[ ! -d "${SCRIPT_DIR}/node_modules" ]]; then
  echo "[npm install] 최초 의존성 설치 중..."
  (cd "${SCRIPT_DIR}" && npm install)
fi

cd "${SCRIPT_DIR}"
exec node "${SCRIPT}" "$@"
