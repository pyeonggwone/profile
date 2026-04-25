#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

load_env

sudo dnf install -y curl ca-certificates

sudo mkdir -p "${HOST_VOLUME_ROOT}/data-sender" \
  "${HOST_VOLUME_ROOT}/pii-processor" \
  "${HOST_VOLUME_ROOT}/remote-update-agent"
sudo chmod -R 0775 "${HOST_VOLUME_ROOT}"

if command -v k3s >/dev/null 2>&1; then
  echo "k3s is already installed."
else
  curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="${K3S_VERSION}" sh -s - --write-kubeconfig-mode 644
fi

sudo systemctl enable --now k3s
sudo k3s kubectl get nodes

echo "k3s installation completed with version ${K3S_VERSION}."