#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

load_env

KUBECTL="sudo k3s kubectl"

${KUBECTL} get nodes -o wide
${KUBECTL} -n "${MEDICALAI_NAMESPACE}" get pods -o wide
${KUBECTL} -n "${MEDICALAI_NAMESPACE}" get services

echo "Volume root: ${HOST_VOLUME_ROOT}"
sudo find "${HOST_VOLUME_ROOT}" -maxdepth 2 -type f -print || true

echo "Recent data-sender logs:"
${KUBECTL} -n "${MEDICALAI_NAMESPACE}" logs deployment/data-sender --tail=20 || true

echo "Recent pii-processor logs:"
${KUBECTL} -n "${MEDICALAI_NAMESPACE}" logs deployment/pii-processor --tail=20 || true

echo "Recent remote-update-agent logs:"
${KUBECTL} -n "${MEDICALAI_NAMESPACE}" logs deployment/remote-update-agent --tail=20 || true