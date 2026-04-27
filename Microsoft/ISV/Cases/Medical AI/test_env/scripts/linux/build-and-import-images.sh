#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

load_env

ASSETS_ROOT="${TEST_ENV_ROOT}/installer/assets"
IMAGE_ASSET_DIR="${ASSETS_ROOT}/images"
RPM_ASSET_DIR="${ASSETS_ROOT}/rpms"
mkdir -p "${IMAGE_ASSET_DIR}"

install_podman() {
  if command -v podman >/dev/null 2>&1; then
    return
  fi

  if compgen -G "${RPM_ASSET_DIR}/*.rpm" >/dev/null; then
    sudo dnf install -y "${RPM_ASSET_DIR}"/*.rpm
    return
  fi

  if sudo dnf install -y podman; then
    return
  fi

  echo "podman installation failed and no local RPM assets were found." >&2
  exit 1
}

install_podman

IMAGE_ROOT="localhost/medicalai"
APPS_DIR="${TEST_ENV_ROOT}/apps"

build_and_import() {
  local app_name="$1"
  local image_name="${IMAGE_ROOT}/${app_name}:${MEDICALAI_IMAGE_TAG}"
  local tar_path="${IMAGE_ASSET_DIR}/${app_name}.tar"

  podman build --build-arg "PYTHON_BASE_IMAGE=${PYTHON_BASE_IMAGE}" -t "${image_name}" "${APPS_DIR}/${app_name}"
  podman save -o "${tar_path}" "${image_name}"
  sudo k3s ctr images import "${tar_path}"
  echo "Saved offline image asset: ${tar_path}"
}

build_and_import "data-sender"
build_and_import "pii-processor"
build_and_import "remote-update-agent"

sudo k3s ctr images ls | grep "localhost/medicalai" || true
echo "Container images were built and imported into k3s containerd."