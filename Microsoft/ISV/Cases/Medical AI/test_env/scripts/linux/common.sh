#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ENV_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${TEST_ENV_ROOT}/.env"

load_env() {
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo ".env file not found: ${ENV_FILE}" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command not found: ${command_name}" >&2
    exit 1
  fi
}