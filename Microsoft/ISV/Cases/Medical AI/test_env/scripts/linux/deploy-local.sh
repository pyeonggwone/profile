#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

load_env

KUBECTL="sudo k3s kubectl"
GENERATED_DIR="${TEST_ENV_ROOT}/generated/k8s"
mkdir -p "${GENERATED_DIR}"

sudo mkdir -p "${HOST_VOLUME_ROOT}/data-sender" \
  "${HOST_VOLUME_ROOT}/pii-processor" \
  "${HOST_VOLUME_ROOT}/remote-update-agent"

render_manifest() {
  local source_file="$1"
  local target_file="$2"
  sed \
    -e "s|medical-ai-test|${MEDICALAI_NAMESPACE}|g" \
    -e "s|:0.1.0|:${MEDICALAI_IMAGE_TAG}|g" \
    -e "s|\${HOST_VOLUME_ROOT}|${HOST_VOLUME_ROOT}|g" \
    "${source_file}" > "${target_file}"
}

render_manifest "${TEST_ENV_ROOT}/k8s/00-namespace.yaml" "${GENERATED_DIR}/00-namespace.yaml"
render_manifest "${TEST_ENV_ROOT}/k8s/01-rbac.yaml" "${GENERATED_DIR}/01-rbac.yaml"
render_manifest "${TEST_ENV_ROOT}/k8s/02-storage.template.yaml" "${GENERATED_DIR}/02-storage.yaml"
render_manifest "${TEST_ENV_ROOT}/k8s/03-workloads.yaml" "${GENERATED_DIR}/03-workloads.yaml"
render_manifest "${TEST_ENV_ROOT}/k8s/04-services.yaml" "${GENERATED_DIR}/04-services.yaml"

${KUBECTL} apply -f "${GENERATED_DIR}/00-namespace.yaml"
${KUBECTL} apply -f "${GENERATED_DIR}/01-rbac.yaml"

${KUBECTL} -n "${MEDICALAI_NAMESPACE}" create configmap medicalai-runtime-config \
  --from-literal=DATA_SENDER_INTERVAL_SECONDS="${DATA_SENDER_INTERVAL_SECONDS}" \
  --from-literal=PII_PROCESSOR_URL="${PII_PROCESSOR_URL}" \
  --from-literal=PII_PROCESSOR_FORWARD_ENABLED="${PII_PROCESSOR_FORWARD_ENABLED}" \
  --from-literal=PII_PROCESSOR_FORWARD_URL="${PII_PROCESSOR_FORWARD_URL}" \
  --from-literal=UPDATE_POLL_INTERVAL_SECONDS="${UPDATE_POLL_INTERVAL_SECONDS}" \
  --from-literal=UPDATE_APPLY_ENABLED="${UPDATE_APPLY_ENABLED}" \
  --from-literal=UPDATE_SOURCE_URL="${UPDATE_SOURCE_URL}" \
  --from-literal=CONTAINER_VOLUME_ROOT="${CONTAINER_VOLUME_ROOT}" \
  --dry-run=client -o yaml | ${KUBECTL} apply -f -

${KUBECTL} -n "${MEDICALAI_NAMESPACE}" create secret generic medicalai-azure-config \
  --from-literal=AZURE_TENANT_ID="${AZURE_TENANT_ID}" \
  --from-literal=AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}" \
  --from-literal=AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP}" \
  --from-literal=AZURE_LOCATION="${AZURE_LOCATION}" \
  --from-literal=AZURE_CLIENT_ID="${AZURE_CLIENT_ID}" \
  --from-literal=AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET}" \
  --from-literal=ACR_LOGIN_SERVER="${ACR_LOGIN_SERVER}" \
  --from-literal=AZURE_STORAGE_ACCOUNT="${AZURE_STORAGE_ACCOUNT}" \
  --from-literal=AZURE_STORAGE_CONTAINER="${AZURE_STORAGE_CONTAINER}" \
  --from-literal=AZURE_EVENTHUB_NAMESPACE="${AZURE_EVENTHUB_NAMESPACE}" \
  --from-literal=AZURE_EVENTHUB_NAME="${AZURE_EVENTHUB_NAME}" \
  --dry-run=client -o yaml | ${KUBECTL} apply -f -

${KUBECTL} apply -f "${GENERATED_DIR}/02-storage.yaml"
${KUBECTL} apply -f "${GENERATED_DIR}/03-workloads.yaml"
${KUBECTL} apply -f "${GENERATED_DIR}/04-services.yaml"

${KUBECTL} -n "${MEDICALAI_NAMESPACE}" rollout status deployment/pii-processor --timeout=180s
${KUBECTL} -n "${MEDICALAI_NAMESPACE}" rollout status deployment/data-sender --timeout=180s
${KUBECTL} -n "${MEDICALAI_NAMESPACE}" rollout status deployment/remote-update-agent --timeout=180s

echo "Medical AI test_env deployment completed."