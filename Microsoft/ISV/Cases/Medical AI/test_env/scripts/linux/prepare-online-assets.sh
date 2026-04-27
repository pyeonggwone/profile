#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

load_env

ASSETS_ROOT="${TEST_ENV_ROOT}/installer/assets"
K3S_ASSET_DIR="${ASSETS_ROOT}/k3s"
RPM_ASSET_DIR="${ASSETS_ROOT}/rpms"
IMAGE_ASSET_DIR="${ASSETS_ROOT}/images"
LOG_ASSET_DIR="${ASSETS_ROOT}/logs"

mkdir -p "${K3S_ASSET_DIR}" "${RPM_ASSET_DIR}" "${IMAGE_ASSET_DIR}" "${LOG_ASSET_DIR}"

echo "Preparing online assets under ${ASSETS_ROOT}"

"${SCRIPT_DIR}/bootstrap-rocky.sh"

cat > "${ASSETS_ROOT}/versions.env" <<EOF
GUEST_OS_TARGET=${GUEST_OS_TARGET}
PYTHON_VERSION=${PYTHON_VERSION}
PYTHON_BASE_IMAGE=${PYTHON_BASE_IMAGE}
K3S_VERSION=${K3S_VERSION}
K3S_INSTALL_SCRIPT_URL=${K3S_INSTALL_SCRIPT_URL}
K3S_BINARY_URL=${K3S_BINARY_URL}
ROCKY_ISO_URL=${ROCKY_ISO_URL}
ROCKY_ISO_PATH=${ROCKY_ISO_PATH}
MEDICALAI_IMAGE_TAG=${MEDICALAI_IMAGE_TAG}
EOF

sudo dnf install -y curl ca-certificates dnf-plugins-core podman
rpm -q curl ca-certificates dnf-plugins-core podman python3 python3-pip > "${LOG_ASSET_DIR}/rpm-direct-versions.txt" || true

if command -v dnf download >/dev/null 2>&1; then
  sudo dnf download --resolve --alldeps --destdir "${RPM_ASSET_DIR}" \
    curl \
    ca-certificates \
    dnf-plugins-core \
    podman \
    python3 \
    python3-pip || true
fi

  find "${RPM_ASSET_DIR}" -maxdepth 1 -type f -name "*.rpm" -printf "%f\n" | sort > "${LOG_ASSET_DIR}/rpm-asset-files.txt"
  rpm -qa | sort > "${LOG_ASSET_DIR}/installed-rpm-versions.txt"

  podman pull "${PYTHON_BASE_IMAGE}"
  podman image inspect "${PYTHON_BASE_IMAGE}" --format '{{.Id}} {{index .RepoDigests 0}}' > "${LOG_ASSET_DIR}/python-base-image-digest.txt" || true

curl -fL "${K3S_INSTALL_SCRIPT_URL}" -o "${K3S_ASSET_DIR}/install.sh"
chmod +x "${K3S_ASSET_DIR}/install.sh"

curl -fL "${K3S_BINARY_URL}" -o "${K3S_ASSET_DIR}/k3s"
chmod +x "${K3S_ASSET_DIR}/k3s"

"${SCRIPT_DIR}/install-k3s.sh" | tee "${LOG_ASSET_DIR}/install-k3s.log"
"${SCRIPT_DIR}/build-and-import-images.sh" | tee "${LOG_ASSET_DIR}/build-and-import-images.log"
"${SCRIPT_DIR}/deploy-local.sh" | tee "${LOG_ASSET_DIR}/deploy-local.log"
"${SCRIPT_DIR}/verify.sh" | tee "${LOG_ASSET_DIR}/verify.log"

sudo k3s ctr images ls | grep "localhost/medicalai" > "${LOG_ASSET_DIR}/k3s-medicalai-images.txt" || true
find "${ASSETS_ROOT}" -maxdepth 3 -type f | sort > "${LOG_ASSET_DIR}/asset-file-list.txt"

echo "Online asset preparation completed."
echo "k3s assets: ${K3S_ASSET_DIR}"
echo "RPM assets: ${RPM_ASSET_DIR}"
echo "Image tar assets: ${IMAGE_ASSET_DIR}"
echo "Logs: ${LOG_ASSET_DIR}"