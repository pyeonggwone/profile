#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

load_env

NETWORK_INTERFACE="${ROCKY_NETWORK_INTERFACE:-auto}"
HOSTNAME_VALUE="${ROCKY_HOSTNAME:-medicalai-rocky9-k3s}"

require_command sudo

select_network_interface() {
  if [[ "${NETWORK_INTERFACE}" != "auto" && -n "${NETWORK_INTERFACE}" ]]; then
    echo "${NETWORK_INTERFACE}"
    return
  fi

  local connected_device
  connected_device="$(nmcli -t -f DEVICE,TYPE,STATE device status | awk -F: '$2 == "ethernet" && $3 == "connected" { print $1; exit }')"
  if [[ -n "${connected_device}" ]]; then
    echo "${connected_device}"
    return
  fi

  nmcli -t -f DEVICE,TYPE device status | awk -F: '$2 == "ethernet" { print $1; exit }'
}

echo "Bootstrapping Rocky Linux host for Medical AI test_env."

sudo systemctl enable --now NetworkManager

INTERFACE_NAME="$(select_network_interface)"
if [[ -z "${INTERFACE_NAME}" ]]; then
  echo "No ethernet interface was found. Check the Hyper-V VM network adapter and virtual switch." >&2
  exit 1
fi

echo "Configuring network interface: ${INTERFACE_NAME}"
sudo nmcli device set "${INTERFACE_NAME}" managed yes || true
sudo nmcli connection modify "${INTERFACE_NAME}" ipv4.method auto ipv6.method auto connection.autoconnect yes 2>/dev/null || true
sudo nmcli device connect "${INTERFACE_NAME}" || true

if ! hostname -I | grep -Eq '[0-9]'; then
  echo "No IPv4 address is assigned yet. Renewing DHCP for ${INTERFACE_NAME}."
  sudo nmcli connection up "${INTERFACE_NAME}" || true
fi

sudo hostnamectl set-hostname "${HOSTNAME_VALUE}"

sudo dnf install -y \
  ca-certificates \
  curl \
  dnf-plugins-core \
  firewalld \
  openssh-server \
  podman \
  rsync \
  tar \
  gzip

sudo systemctl enable --now sshd
sudo systemctl enable --now firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-port=30080/tcp
sudo firewall-cmd --reload

sudo mkdir -p "${HOST_VOLUME_ROOT}/data-sender" \
  "${HOST_VOLUME_ROOT}/pii-processor" \
  "${HOST_VOLUME_ROOT}/remote-update-agent"
sudo chmod -R 0775 "${HOST_VOLUME_ROOT}"

echo "Bootstrap completed."
echo "Hostname: $(hostname)"
echo "IP addresses: $(hostname -I || true)"
echo "Next: run ./scripts/linux/prepare-online-assets.sh"