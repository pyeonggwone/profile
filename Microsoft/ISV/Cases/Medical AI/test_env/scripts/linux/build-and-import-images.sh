#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

load_env

sudo dnf install -y podman

IMAGE_ROOT="localhost/medicalai"
APPS_DIR="${TEST_ENV_ROOT}/apps"

build_and_import() {
  local app_name="$1"
  local image_name="${IMAGE_ROOT}/${app_name}:${MEDICALAI_IMAGE_TAG}"
  local tar_path="${TEST_ENV_ROOT}/${app_name}-${MEDICALAI_IMAGE_TAG}.tar"

  podman build -t "${image_name}" "${APPS_DIR}/${app_name}"
  podman save -o "${tar_path}" "${image_name}"
  sudo k3s ctr images import "${tar_path}"
  rm -f "${tar_path}"
}

build_and_import "data-sender"
build_and_import "pii-processor"
build_and_import "remote-update-agent"

sudo k3s ctr images ls | grep "localhost/medicalai" || true
echo "Container images were built and imported into k3s containerd."