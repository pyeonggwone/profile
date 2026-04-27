#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

load_env

ASSETS_ROOT="${TEST_ENV_ROOT}/installer/assets"
K3S_ASSET_DIR="${ASSETS_ROOT}/k3s"
RPM_ASSET_DIR="${ASSETS_ROOT}/rpms"

install_packages() {
  if sudo dnf install -y "$@"; then
    return
  fi

  if compgen -G "${RPM_ASSET_DIR}/*.rpm" >/dev/null; then
    sudo dnf install -y "${RPM_ASSET_DIR}"/*.rpm
    return
  fi

  echo "Package installation failed and no local RPM assets were found." >&2
  exit 1
}

install_packages curl ca-certificates

sudo mkdir -p "${HOST_VOLUME_ROOT}/data-sender" \
  "${HOST_VOLUME_ROOT}/pii-processor" \
  "${HOST_VOLUME_ROOT}/remote-update-agent"
sudo chmod -R 0775 "${HOST_VOLUME_ROOT}"

if command -v k3s >/dev/null 2>&1; then
  echo "k3s is already installed."
else
  if [[ -x "${K3S_ASSET_DIR}/k3s" && -f "${K3S_ASSET_DIR}/install.sh" ]]; then
    sudo install -m 0755 "${K3S_ASSET_DIR}/k3s" /usr/local/bin/k3s
    INSTALL_K3S_SKIP_DOWNLOAD=true sh "${K3S_ASSET_DIR}/install.sh" --write-kubeconfig-mode 644
  else
    curl -sfL "${K3S_INSTALL_SCRIPT_URL}" | INSTALL_K3S_VERSION="${K3S_VERSION}" sh -s - --write-kubeconfig-mode 644
  fi
fi

sudo systemctl enable --now k3s
sudo k3s kubectl get nodes

echo "k3s installation completed with version ${K3S_VERSION}."