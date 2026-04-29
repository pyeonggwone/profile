# 구현 가이드: 서비스 간 호출 (ECG 분석 End-to-End)

> 근거 문서: [L3 워크로드 개요.md](../L3%20워크로드%20개요.md), [L4 컴포넌트 상세.md](../L4%20컴포넌트%20상세.md)  
> 모든 서비스 간 통신은 Private Endpoint 경유, 퍼블릭 인터넷 접근 없음

---

## 전체 호출 흐름

```
병원 온프레미스
  └─ PII Masking Container (Docker)
      └─ RabbitMQ Producer
          └─[VPN/ExpressRoute]─ Load Balancer (Azure)
              └─ AKS 마이크로서비스
                  ├─ RabbitMQ Cluster (VM) — 비동기 메시지
                  ├─ CosmosDB (MongoDB API) — ECG 데이터 저장
                  ├─ MySQL Flexible Server — 서비스 운영 데이터
                  └─ Key Vault — 시크릿 조회
                      └─ AI Analysis Module (Container Apps)
                          └─ CosmosDB — 분석 결과 저장
                              └─ 웹 애플리케이션 / Client System
```

---

## 서비스 1: Load Balancer — Inbound 수신

### 용도
병원 온프레미스 PII Masking Container에서 전송한 데이터를 AKS 마이크로서비스로 분산

### 구성

```bash
# Internal Load Balancer (퍼블릭 IP 없음 — Private Endpoint 경유)
az network lb create \
  --resource-group rg-medicalai-sw \
  --name lb-medicalai-internal \
  --sku Standard \
  --backend-pool-name bp-aks-nodes \
  --frontend-ip-name fe-internal \
  --subnet /subscriptions/<SW_SUB_ID>/resourceGroups/rg-medicalai-sw/providers/Microsoft.Network/virtualNetworks/vnet-sw-spoke/subnets/snet-lb \
  --private-ip-address 10.1.10.100 \   # 고정 IP 할당
  --location koreacentral

# 포트 규칙
# MQ Format (실시간): TCP 5672 (AMQP)
# File Format (배치): TCP 8080 (HTTP)
az network lb rule create \
  --resource-group rg-medicalai-sw \
  --lb-name lb-medicalai-internal \
  --name rule-amqp \
  --protocol Tcp \
  --frontend-port 5672 \
  --backend-port 5672 \
  --frontend-ip-name fe-internal \
  --backend-pool-name bp-aks-nodes \
  --probe-name probe-amqp

az network lb rule create \
  --resource-group rg-medicalai-sw \
  --lb-name lb-medicalai-internal \
  --name rule-http \
  --protocol Tcp \
  --frontend-port 8080 \
  --backend-port 8080 \
  --frontend-ip-name fe-internal \
  --backend-pool-name bp-aks-nodes \
  --probe-name probe-http
```

---

## 서비스 2: AKS 마이크로서비스

### AKS Private Cluster 생성

```bash
# SW Subscription에 AKS 배포
az aks create \
  --resource-group rg-medicalai-sw \
  --name aks-medicalai-service \
  --location koreacentral \
  --enable-private-cluster \            # Private Cluster — API Server 퍼블릭 노출 없음
  --network-plugin azure \
  --vnet-subnet-id /subscriptions/<SW_SUB_ID>/resourceGroups/rg-medicalai-sw/providers/Microsoft.Network/virtualNetworks/vnet-sw-spoke/subnets/snet-aks \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --zones 1 2 3 \                       # 가용 영역 분산
  --enable-managed-identity \
  --assign-identity <AKS_MANAGED_IDENTITY_ID> \
  --generate-ssh-keys

# Platform AKS Controller (Shared Subscription) — 다중 AKS 배포 상태 관리
az aks create \
  --resource-group rg-medicalai-shared \
  --name aks-medicalai-platform-ctrl \
  --location koreacentral \
  --enable-private-cluster \
  --node-count 2 \
  --node-vm-size Standard_D2s_v3 \
  --zones 1 2 3 \
  --enable-managed-identity \
  --generate-ssh-keys
```

### AKS → Key Vault 인증 (Workload Identity)

```yaml
# Azure Workload Identity를 통한 Key Vault 접근 (서비스 주체 시크릿 없이 인증)
# 1. Workload Identity 활성화
# az aks update --resource-group rg-medicalai-sw --name aks-medicalai-service \
#   --enable-oidc-issuer --enable-workload-identity

# 2. Kubernetes ServiceAccount + Federated Credential 연결
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sa-ecg-service
  namespace: ecg
  annotations:
    azure.workload.identity/client-id: "<MANAGED_IDENTITY_CLIENT_ID>"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ecg-api
  namespace: ecg
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ecg-api
  template:
    metadata:
      labels:
        app: ecg-api
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: sa-ecg-service
      containers:
      - name: ecg-api
        image: <ACR_NAME>.azurecr.io/ecg-api:latest
        env:
        - name: AZURE_KEY_VAULT_URL
          value: "https://kv-medicalai-shared.vault.azure.net/"
        - name: COSMOSDB_ENDPOINT
          value: "https://cosmos-medicalai.documents.azure.com:443/"
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
```

---

## 서비스 3: RabbitMQ Cluster (Azure VM)

### VM 기반 RabbitMQ 클러스터 구성

```bash
# RabbitMQ VM 3대 배포 (3 노드 클러스터)
for i in 1 2 3; do
  az vm create \
    --resource-group rg-medicalai-sw \
    --name vm-rabbitmq-$i \
    --image Ubuntu2204 \
    --size Standard_D2s_v3 \
    --vnet-name vnet-sw-spoke \
    --subnet snet-rabbitmq \
    --private-ip-address 10.1.20.$((10+i)) \
    --no-wait \
    --authentication-type ssh \
    --ssh-key-values ~/.ssh/id_rsa.pub \
    --zone $i
done
```

RabbitMQ 설치 및 클러스터 구성 (각 VM에서 실행):

```bash
# 패키지 설치
apt-get install -y rabbitmq-server

# 클러스터 쿠키 동기화 (모든 노드 동일한 값)
echo "MEDICALAI_RABBIT_COOKIE" > /var/lib/rabbitmq/.erlang.cookie
chmod 400 /var/lib/rabbitmq/.erlang.cookie
chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie

# vm-rabbitmq-2, 3에서 클러스터 합류
rabbitmqctl stop_app
rabbitmqctl join_cluster rabbit@vm-rabbitmq-1
rabbitmqctl start_app

# AMQP TLS 활성화 (포트 5671)
cat >> /etc/rabbitmq/rabbitmq.conf <<EOF
listeners.ssl.default = 5671
ssl_options.cacertfile = /etc/rabbitmq/certs/ca.pem
ssl_options.certfile   = /etc/rabbitmq/certs/server.pem
ssl_options.keyfile    = /etc/rabbitmq/certs/server.key
ssl_options.verify     = verify_peer
ssl_options.fail_if_no_peer_cert = true
EOF

# 큐 설정 (ECG 전용 vhost + 미러링)
rabbitmqctl add_vhost ecg-data
rabbitmqctl set_policy ha-all -p ecg-data ".*" \
  '{"ha-mode":"all","ha-sync-mode":"automatic"}' --priority 0
```

---

## 서비스 4: CosmosDB (MongoDB API)

### Private Endpoint 연결 구성

```bash
# CosmosDB 계정 생성 (Public 접근 차단)
az cosmosdb create \
  --resource-group rg-medicalai-sw \
  --name cosmos-medicalai \
  --kind MongoDB \
  --server-version "6.0" \
  --locations regionName=koreacentral failoverPriority=0 isZoneRedundant=true \
  --enable-public-network false \       # 퍼블릭 접근 완전 차단
  --default-consistency-level Session

# Private Endpoint 생성
az network private-endpoint create \
  --resource-group rg-medicalai-sw \
  --name pe-cosmosdb \
  --vnet-name vnet-sw-spoke \
  --subnet snet-pe \
  --private-connection-resource-id $(az cosmosdb show -g rg-medicalai-sw -n cosmos-medicalai --query id -o tsv) \
  --group-id MongoDB \
  --connection-name pec-cosmosdb

# Private DNS Zone 연결
az network private-dns zone create \
  --resource-group rg-medicalai-sw \
  --name "privatelink.mongo.cosmos.azure.com"

az network private-dns link vnet create \
  --resource-group rg-medicalai-sw \
  --zone-name "privatelink.mongo.cosmos.azure.com" \
  --name dnslink-cosmos \
  --virtual-network vnet-sw-spoke \
  --registration-enabled false
```

AKS 파드에서 CosmosDB 연결 (Connection String 예시):

```python
# Python (pymongo) — Managed Identity로 Key Vault에서 연결 문자열 가져옴
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import pymongo

credential = DefaultAzureCredential()
kv_client = SecretClient(
    vault_url="https://kv-medicalai-shared.vault.azure.net/",
    credential=credential
)
conn_str = kv_client.get_secret("cosmosdb-connection-string").value

client = pymongo.MongoClient(
    conn_str,
    tls=True,
    tlsCAFile="/etc/ssl/certs/ca-certificates.crt",
    serverSelectionTimeoutMS=5000,
    retryWrites=True
)
db = client["ecg-data"]
ecg_collection = db["ecg-records"]
```

---

## 서비스 5: MySQL Flexible Server

```bash
# MySQL Flexible Server (Private Endpoint only)
az mysql flexible-server create \
  --resource-group rg-medicalai-sw \
  --name mysql-medicalai \
  --location koreacentral \
  --sku-name Standard_D4ds_v4 \
  --storage-size 128 \
  --version 8.0 \
  --high-availability ZoneRedundant \
  --standby-zone 2 \
  --private-dns-zone-name privatelink.mysql.database.azure.com \
  --vnet vnet-sw-spoke \
  --subnet snet-mysql \
  --public-access Disabled \
  --admin-user $(az keyvault secret show --vault-name kv-medicalai-shared --name mysql-admin-user --query value -o tsv) \
  --admin-password $(az keyvault secret show --vault-name kv-medicalai-shared --name mysql-admin-password --query value -o tsv)

# TDE (Transparent Data Encryption) — CMK 적용
az mysql flexible-server update \
  --resource-group rg-medicalai-sw \
  --name mysql-medicalai \
  --data-encryption-key-uri $(az keyvault key show --vault-name kv-medicalai-shared --name mysql-tde-key --query key.kid -o tsv) \
  --data-encryption-identity $(az identity show -g rg-medicalai-shared -n id-mysql-tde --query id -o tsv)
```

---

## 서비스 6: AI Analysis Module (Azure Container Apps)

```bash
# Container Apps Environment 생성 (Internal — 퍼블릭 외부 트래픽 없음)
az containerapp env create \
  --resource-group rg-medicalai-ai \
  --name cae-medicalai-ai \
  --location koreacentral \
  --internal-only true \
  --infrastructure-subnet-resource-id /subscriptions/<AI_SUB_ID>/resourceGroups/rg-medicalai-ai/providers/Microsoft.Network/virtualNetworks/vnet-ai-spoke/subnets/snet-cae

# AI Analysis Container App 배포
az containerapp create \
  --resource-group rg-medicalai-ai \
  --name ca-ecg-analyzer \
  --environment cae-medicalai-ai \
  --image <ACR_NAME>.azurecr.io/ecg-analyzer:latest \
  --cpu 4 --memory 16Gi \
  --min-replicas 1 --max-replicas 10 \
  --scale-rule-name rabbitmq-scale \
  --scale-rule-type rabbitmq \
  --scale-rule-metadata "queueName=ecg-analysis-queue" "queueLength=5" \
  --ingress internal \               # 내부 트래픽만 허용
  --target-port 8080 \
  --env-vars \
    COSMOSDB_ENDPOINT=https://cosmos-medicalai.privatelink.mongo.cosmos.azure.com \
    KEY_VAULT_URL=https://kv-medicalai-shared.vault.azure.net/
```

### AI Module → CosmosDB Private Endpoint 경유 검증

```bash
# Container App 내부에서 CosmosDB DNS 해석 확인
# privatelink.mongo.cosmos.azure.com → 10.x.x.x (Private IP) 반환 확인
az containerapp exec \
  --resource-group rg-medicalai-ai \
  --name ca-ecg-analyzer \
  --command "nslookup cosmos-medicalai.mongo.cosmos.azure.com"
# 기대: 10.x.x.x (Private IP)
```

---

## 서비스 7: Key Vault (시크릿 중앙 관리)

```bash
# Key Vault 생성 (Shared Subscription, Premium SKU — HSM 지원)
az keyvault create \
  --resource-group rg-medicalai-shared \
  --name kv-medicalai-shared \
  --location koreacentral \
  --sku Premium \
  --enable-rbac-authorization true \
  --public-network-access Disabled \
  --enable-purge-protection true \
  --retention-days 90

# Private Endpoint
az network private-endpoint create \
  --resource-group rg-medicalai-shared \
  --name pe-keyvault \
  --vnet-name vnet-shared \
  --subnet snet-pe \
  --private-connection-resource-id $(az keyvault show -g rg-medicalai-shared -n kv-medicalai-shared --query id -o tsv) \
  --group-id vault \
  --connection-name pec-keyvault

# AKS Managed Identity에 Key Vault Secrets User 권한 부여
AKS_IDENTITY=$(az aks show -g rg-medicalai-sw -n aks-medicalai-service \
  --query "identityProfile.kubeletidentity.clientId" -o tsv)

az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee $AKS_IDENTITY \
  --scope $(az keyvault show -g rg-medicalai-shared -n kv-medicalai-shared --query id -o tsv)

# Container Apps Managed Identity에도 동일 권한 부여
CA_IDENTITY=$(az containerapp identity show -g rg-medicalai-ai -n ca-ecg-analyzer --query principalId -o tsv)
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee $CA_IDENTITY \
  --scope $(az keyvault show -g rg-medicalai-shared -n kv-medicalai-shared --query id -o tsv)

# 키 자동 로테이션 정책 설정 (90일)
az keyvault key rotation-policy update \
  --vault-name kv-medicalai-shared \
  --name cosmosdb-cmk \
  --value '{
    "lifetimeActions": [
      {"trigger": {"timeAfterCreate": "P90D"}, "action": {"type": "Rotate"}}
    ]
  }'
```

---

## 서비스 8: Azure Monitor + Grafana

```bash
# Azure Monitor Workspace
az monitor account create \
  --resource-group rg-medicalai-shared \
  --name amon-medicalai \
  --location koreacentral

# Managed Grafana
az grafana create \
  --resource-group rg-medicalai-shared \
  --name grafana-medicalai \
  --location koreacentral \
  --sku Standard

# AKS Prometheus 메트릭 수집 활성화
az aks update \
  --resource-group rg-medicalai-sw \
  --name aks-medicalai-service \
  --enable-azure-monitor-metrics \
  --azure-monitor-workspace-resource-id $(az monitor account show -g rg-medicalai-shared -n amon-medicalai --query id -o tsv) \
  --grafana-resource-id $(az grafana show -g rg-medicalai-shared -n grafana-medicalai --query id -o tsv)

# Sentinel — PHI 이상 접근 알림 규칙
az sentinel alert-rule create \
  --resource-group rg-medicalai-shared \
  --workspace-name law-medicalai \
  --rule-name "PHI-Anomaly-Access" \
  --kind Scheduled \
  --display-name "PHI 데이터 비정상 접근 탐지" \
  --severity High \
  --enabled true \
  --query-period PT1H \
  --query-frequency PT5M \
  --trigger-threshold 0 \
  --trigger-operator GreaterThan \
  --query "CosmosDBLogs | where OperationName == 'Query' and CallerIpAddress !startswith '10.' | project TimeGenerated, CallerIpAddress, DatabaseName"
```

---

## 서비스 9: Azure Arc (온프레미스 VM 원격 관리)

설치 방법은 [01-vpn-gateway.md Step 9](01-vpn-gateway.md) 참조.

Arc 연결 후 정책 적용:

```bash
# 온프레미스 Arc VM에 보안 기준선 적용
az policy assignment create \
  --name "arc-linux-security-baseline" \
  --policy "/providers/Microsoft.Authorization/policyDefinitions/fc9b3da7-8347-4380-8e70-0a0361d8dedd" \
  --scope "/subscriptions/<SHARED_SUB_ID>/resourceGroups/rg-medicalai-shared"

# 자동 패치 관리
az maintenance configuration create \
  --resource-group rg-medicalai-shared \
  --resource-name mc-arc-patch \
  --maintenance-scope InGuestPatch \
  --location koreacentral \
  --install-patches-linux-parameters packageNameMasksToInclude="*" classificationToInclude="Security"
```

---

## 서비스 호출 흐름 NSG 규칙 요약

| 소스 | 목적지 | 포트 | 방향 | NSG |
|------|--------|------|------|-----|
| 병원 온프레미스 | Load Balancer | 5672 (AMQP TLS), 8080 | Inbound | nsg-lb |
| Load Balancer | AKS Node | 5672, 8080 | Inbound | nsg-aks |
| AKS | RabbitMQ VM | 5672 | Outbound | nsg-aks |
| AKS | CosmosDB PE | 10255 (Mongo) | Outbound | nsg-aks |
| AKS | MySQL PE | 3306 | Outbound | nsg-aks |
| AKS | Key Vault PE | 443 | Outbound | nsg-aks |
| Container Apps | CosmosDB PE | 10255 | Outbound | nsg-cae |
| Container Apps | Key Vault PE | 443 | Outbound | nsg-cae |
| 전 서비스 | Log Analytics | 443 | Outbound | (공통) |
| 전 서비스 | * (인터넷) | any | Outbound (Deny) | (공통) |
