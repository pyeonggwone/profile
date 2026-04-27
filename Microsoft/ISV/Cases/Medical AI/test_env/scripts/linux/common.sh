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

  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line%$'\r'}"
    line="${line#${line%%[![:space:]]*}}"
    line="${line%${line##*[![:space:]]}}"

    if [[ -z "${line}" || "${line}" == \#* || "${line}" != *=* ]]; then
      continue
    fi

    local key="${line%%=*}"
    local value="${line#*=}"
    key="${key//[[:space:]]/}"
    value="${value#${value%%[![:space:]]*}}"
    value="${value%${value##*[![:space:]]}}"

    if [[ ! "${key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      continue
    fi

    if [[ "${value}" == \"*\" && "${value}" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "${value}" == \'*\' && "${value}" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi

    export "${key}=${value}"
  done < "${ENV_FILE}"

  if [[ "${UPDATE_SOURCE_URL:-}" == *'${BLOB_SAS_TOKEN}'* ]]; then
    UPDATE_SOURCE_URL="${UPDATE_SOURCE_URL//\$\{BLOB_SAS_TOKEN\}/${BLOB_SAS_TOKEN:-}}"
    export UPDATE_SOURCE_URL
  fi
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command not found: ${command_name}" >&2
    exit 1
  fi
}