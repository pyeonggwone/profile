# 구현 가이드: 병원 온프레미스 클라이언트 — k3s 에이전트 방식

> 적용 시나리오: Windows Server 2019 / 2022 병원 서버에 k3s를 설치하고, 컨테이너 기반 클라이언트 에이전트를 Azure SaaS 백엔드와 연동  
> 네트워크 연동 기준: [hipaa-network.ver4.md](../Implement_Network/hipaa-network.ver4.md) — S2S VPN + NSG  
> HIPAA 기준: §164.312(e)(1) 전송 보안, §164.312(e)(2)(ii) 전송 중 암호화, §164.312(b) 감사 통제  
> 버전: v7 (2026-04-20 — 크로스링크 ver2 반영)

---

## 배포 방식 선택 기준

| 항목 | 이 가이드 (k3s) | [06 가이드 (PowerShell Installer)](./06-windows-installer-client.ver2.md) |
|---|---|---|
| **지원 OS** | Windows Server 2019 / 2022 (64-bit) 전용 | Windows Server 2012 R2 이상 (범용) |
| **런타임** | k3s (containerd) | Windows SCM (Service Control Manager) |
| **배포 단위** | 컨테이너 이미지 | ZIP 번들 + PowerShell Installer |
| **원격 업데이트** | Arc GitOps (Flux) | Arc Run Command (Install.ps1) |
| **병원 IT 요구 역량** | 높음 (K8s 기본 이해 필요) | 낮음 (표준 Windows 운영) |

> **선택 기준**: 병원 서버 OS 확인 후 결정. OS 버전이 불명확하거나 혼재한다면 [06 가이드 (PowerShell Installer)](./06-windows-installer-client.ver2.md) 사용.

---

## 전체 구조

```
병원 온프레미스 (Windows Server 2019/2022)
  └─ k3s 단일 노드 클러스터
      ├─ pii-masking (Pod)
      ├─ rabbitmq-producer (Pod)
      └─ config-sync (Pod)
          └─[S2S VPN — IPsec AES-256]─ Azure VPN Gateway (vpngw-medicalai-hub-us)
              └─ NSG (nsg-snet-aks) — 최소 권한 접근 통제
                  └─ AKS 마이크로서비스 (10.2.10.0/24)
                      ├─ RabbitMQ Cluster
                      ├─ MySQL Flexible Server
                      └─ AI Analysis Module

Arc-enabled Server (병원 온프레미스 서버)
  └─[HTTPS 443]─ Azure Arc Service
      ├─ Flux (GitOps) — k3s 매니페스트 자동 동기화
      ├─ Azure Update Manager — OS 패치 관리
      ├─ Machine Configuration — 컴플라이언스 드리프트 감지
      └─ Key Vault CSI Driver — 시크릿 주입
```

---

## 1. 지원 OS 매트릭스

| OS | k3s Windows 노드 지원 | Arc 지원 | HIPAA 패치 관리 | 비고 |
|---|---|---|---|---|
| Windows Server 2022 | ✅ 공식 지원 | ✅ | ✅ | **권장** |
| Windows Server 2019 | ✅ 공식 지원 | ✅ | ✅ | 지원 |
| Windows Server 2016 이하 | ❌ 불가 | ✅ | 조건부 | → [06 가이드 (PowerShell Installer)](./06-windows-installer-client.ver2.md) 사용 |

> k3s Windows 노드 요구사항: containerd 런타임은 Windows Server 2019+ 에서만 지원.  
> 참고: [k3s Windows Support](https://docs.k3s.io/advanced#windows-agent-nodes)

---

## 2. 사전 조건

| 항목 | 요구사항 |
|---|---|
| OS | Windows Server 2019 / 2022 (64-bit) |
| CPU / Memory | 2 vCPU 이상, 4 GB RAM 이상 |
| 디스크 | 20 GB 이상 (이미지 스토리지 포함) |
| 네트워크 포트 (Outbound) | TCP 443 (HTTPS), TCP 5671 (AMQPS) Azure 방향 허용 |
| VPN 장비 | IKEv2 지원 (병원 측 VPN 장비) |
| 병원 공인 IP | ISV에 사전 통보 (Local Network Gateway 등록용) |
| Azure 구독 | ISV Azure 구독 (Arc 등록 대상) |
| 컨테이너 이미지 레지스트리 | Azure Container Registry (ACR) `acrmedicalai` — ISV 관리 |

---

## 3. ISV 측 Azure 사전 구성

### 3-1. Azure Container Registry 이미지 준비

ISV 개발팀에서 3종 에이전트를 컨테이너 이미지로 빌드 후 ACR에 푸시:

```bash
# ISV 개발환경에서 실행

# 이미지 빌드 (.NET 8 Linux 기반 — k3s는 Linux 컨테이너)
docker build -t pii-masking-service:v7.0 ./src/pii-masking
docker build -t rabbitmq-producer:v7.0 ./src/rabbitmq-producer
docker build -t config-sync:v7.0 ./src/config-sync

# ACR 푸시
az acr login --name acrmedicalai
docker tag pii-masking-service:v7.0 acrmedicalai.azurecr.io/pii-masking-service:v7.0
docker tag rabbitmq-producer:v7.0 acrmedicalai.azurecr.io/rabbitmq-producer:v7.0
docker tag config-sync:v7.0 acrmedicalai.azurecr.io/config-sync:v7.0
docker push acrmedicalai.azurecr.io/pii-masking-service:v7.0
docker push acrmedicalai.azurecr.io/rabbitmq-producer:v7.0
docker push acrmedicalai.azurecr.io/config-sync:v7.0
```

> **실제 구성**: k3s는 Linux 컨테이너 기반. 병원 서버가 Windows만 있다면 [06 가이드 (PowerShell Installer)](./06-windows-installer-client.ver2.md) 권장.

---

## 3-A. 아키텍처 전제 명확화

k3s를 병원 온프레미스에 배포할 때 **두 가지 구성** 중 하나를 선택:

| 구성 | 병원 서버 OS | k3s 역할 | 비고 |
|---|---|---|---|
| **A. Linux 서버** | Ubuntu 22.04 / RHEL 8 | k3s server (단일 노드) | 권장 — 컨테이너 네이티브 |
| **B. Windows Server + WSL2** | Windows Server 2022 | k3s via WSL2 | 병원이 Windows만 운영할 경우 |

> 이 가이드는 **구성 A (Linux 서버)** 기준. 병원 서버가 Windows만 있다면 [06 가이드 (PowerShell Installer)](./06-windows-installer-client.ver2.md) 권장.

---

### 3-2. VPN 구성 (ISV 담당)

**Step A. Local Network Gateway 등록**

| 항목 | 값 |
|---|---|
| Name | `lng-hospital-us-001` |
| IP address | 병원 공인 IP (사전 수집) |
| Address space | 병원 내부 CIDR (`192.168.10.0/24`) |

**Step B. VPN Connection 생성**

| 항목 | 값 |
|---|---|
| Connection type | Site-to-site (IPsec) |
| Local network gateway | `lng-hospital-us-001` |
| Shared key (PSK) | Key Vault `kv-medicalai-shared` → Secret `vpn-psk-hospital-us` |
| IPsec Policy | IKEv2 + AES-256 + SHA-256 |

**Step C. NSG Rule 추가**

| 항목 | 값 |
|---|---|
| Name | `allow-hospital-us-001-to-aks` |
| Source | `192.168.10.0/24` |
| Destination | `10.2.10.0/24` (AKS Subnet) |
| Destination port ranges | `443, 5671` |
| Action | Allow |

### 3-3. Arc GitOps 저장소 구성 (ISV 담당)

ISV가 GitOps 전용 저장소에 k3s 매니페스트를 관리:

```
git-repo: medicalai-k3s-manifests (private)
  └─ hospitals/
      ├─ base/
      │   ├─ namespace.yaml
      │   ├─ pii-masking-deployment.yaml
      │   ├─ rabbitmq-producer-deployment.yaml
      │   └─ config-sync-deployment.yaml
      └─ hospital-us-001/
          └─ kustomization.yaml  # 병원별 오버라이드 (이미지 태그, 시크릿 참조)
```

---

## 4. 병원 서버 측 설치 절차

### 4-1. S2S VPN 연결 구성 (병원 네트워크 담당)

병원 VPN 장비(Cisco / Palo Alto / FortiGate)에서 IKEv2 터널 구성:

| 항목 | 값 |
|---|---|
| Remote IP | `pip-vpngw-medicalai-hub-us` (ISV 제공) |
| PSK | ISV 제공 (Key Vault에서 ISV가 조회 후 별도 채널로 전달) |
| IKE Version | IKEv2 |
| Encryption | AES-256 |
| Hash | SHA-256 |
| Local CIDR | `192.168.10.0/24` |
| Remote CIDR | `10.2.10.0/24` |

```bash
# VPN 터널 확인 (병원 서버에서)
ping 10.2.0.1  # Azure VPN Gateway 내부 IP
```

### 4-2. k3s 설치 (병원 서버 — Linux)

```bash
# k3s 단일 노드 설치 (server 모드)
curl -sfL https://get.k3s.io | sh -s - \
  --disable traefik \
  --disable servicelb \
  --write-kubeconfig-mode 644

# 설치 확인
sudo systemctl status k3s
sudo kubectl get nodes
# NAME         STATUS   ROLES                  AGE
# hospital-01  Ready    control-plane,master   1m
```

### 4-3. Azure Arc 에이전트 등록

```bash
# Azure Arc Connected Machine Agent 설치 (Linux)
wget https://aka.ms/azcmagent -O ~/install_linux_azcmagent.sh
sudo bash ~/install_linux_azcmagent.sh

# Arc 등록 (ISV Azure 구독에 등록)
sudo azcmagent connect \
  --resource-group rg-medicalai-arc \
  --tenant-id <ISV_TENANT_ID> \
  --location eastus \
  --subscription-id <ISV_SUBSCRIPTION_ID>
```

### 4-4. Key Vault CSI Driver 설치 및 시크릿 마운트

```bash
# Secrets Store CSI Driver + Azure Key Vault Provider 설치
sudo kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/main/deploy/rbac-secretproviderclass.yaml
sudo kubectl apply -f https://raw.githubusercontent.com/Azure/secrets-store-csi-driver-provider-azure/master/deployment/provider-azure-installer.yaml

# SecretProviderClass 생성 (ISV가 제공하는 매니페스트)
sudo kubectl apply -f - <<EOF
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: medicalai-kv-secrets
  namespace: medicalai
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    clientID: "<USER_ASSIGNED_MI_CLIENT_ID>"
    keyvaultName: "kv-medicalai-shared"
    tenantID: "<ISV_TENANT_ID>"
    objects: |
      array:
        - |
          objectName: vpn-psk-hospital-us
          objectType: secret
        - |
          objectName: rabbitmq-amqp-uri
          objectType: secret
EOF
```

> PSK 평문은 로컬 파일에 저장하지 않음. Key Vault CSI Driver가 Pod 기동 시 런타임 마운트. (§164.312(a)(2)(iv))

### 4-5. Arc GitOps Flux 연동 (ISV 담당 — Arc 포털에서 구성)

> Azure Portal → Azure Arc → Servers → 해당 서버 → GitOps → + Create

| 항목 | 값 |
|---|---|
| Configuration name | `medicalai-agents` |
| Namespace | `medicalai` |
| Scope | Namespace |
| Repository URL | ISV GitOps 저장소 URL |
| Branch | `main` |
| Path | `hospitals/hospital-us-001` |
| Sync interval | 5분 |

Flux가 GitOps 저장소를 주기적으로 동기화하여 매니페스트 변경 시 자동 배포.

### 4-6. 배포 확인

```bash
sudo kubectl get pods -n medicalai
# NAME                              READY   STATUS    RESTARTS
# pii-masking-xxx                   1/1     Running   0
# rabbitmq-producer-xxx             1/1     Running   0
# config-sync-xxx                   1/1     Running   0

# RabbitMQ 전송 로그 확인
sudo kubectl logs -n medicalai -l app=rabbitmq-producer --tail=30 | grep "Published\|Error"

# Key Vault 시크릿 마운트 확인
sudo kubectl exec -n medicalai deployment/config-sync -- ls /mnt/secrets-store/
```

---

## 5. Azure 연동 확인

### 5-1. VPN 터널

> Azure Portal → VPN Gateway `vpngw-medicalai-hub-us` → Connections → `lng-hospital-us-001`  
> Connection status: **Connected** 확인

### 5-2. Arc 등록 상태

> Azure Portal → Azure Arc → Servers → `hospital-us-001` → **Connected** 확인

### 5-3. GitOps 동기화 상태

> Azure Portal → Azure Arc → Servers → 해당 서버 → GitOps  
> Compliance state: **Compliant** 확인

---

## 6. 이미지 업데이트 (신규 버전 배포)

ISV가 새 이미지를 ACR에 푸시 후 GitOps 저장소의 이미지 태그를 변경하면 Flux가 자동 동기화:

```bash
# ISV 개발팀 — 새 이미지 푸시
docker push acrmedicalai.azurecr.io/pii-masking-service:v7.1

# GitOps 저장소에서 이미지 태그 변경 (PR → merge)
# hospitals/hospital-us-001/kustomization.yaml
# images:
#   - name: acrmedicalai.azurecr.io/pii-masking-service
#     newTag: v7.1

# Flux가 5분 내 자동 감지 → 롤링 업데이트
```

> 병원 IT팀의 직접 개입 없이 ISV가 이미지 업데이트 관리 가능.

---

## 7. HIPAA 요구사항 체크리스트

| 항목 | 구현 방법 | HIPAA 조항 |
|---|---|---|
| 전송 중 암호화 | S2S VPN IPsec AES-256 + TLS 1.2 이상 | §164.312(e)(2)(ii) |
| PSK / 시크릿 로컬 미저장 | Key Vault CSI Driver — Pod 기동 시 런타임 마운트 | §164.312(a)(2)(iv) |
| 컨테이너 이미지 무결성 | ACR 이미지 서명 (Notary v2 / cosign) 권장 | §164.312(c)(1) |
| 최소 권한 | Pod SecurityContext — nonRoot, readOnlyRootFilesystem | §164.312(a)(1) |
| 네트워크 접근 제한 | NSG + K8s NetworkPolicy (Pod 간 통신 제한) | §164.312(e)(1) |
| 감사 로그 | Pod 로그 → Azure Log Analytics (Fluent Bit DaemonSet) | §164.312(b) |
| OS 패치 관리 | Azure Arc + Azure Update Manager | §164.312(a)(2)(ii) |
| 설정 컴플라이언스 | Arc Machine Configuration + GitOps Compliance | §164.306(a)(1) |

---

## 8. 참고 링크

| 목적 | 링크 |
|---|---|
| k3s 공식 문서 | [docs.k3s.io](https://docs.k3s.io) |
| k3s 설치 가이드 | [docs.k3s.io/quick-start](https://docs.k3s.io/quick-start) |
| Azure Arc GitOps (Flux) | [learn.microsoft.com/en-us/azure/azure-arc/kubernetes/tutorial-use-gitops-flux2](https://learn.microsoft.com/en-us/azure/azure-arc/kubernetes/tutorial-use-gitops-flux2) |
| Key Vault CSI Driver | [learn.microsoft.com/en-us/azure/aks/csi-secrets-store-driver](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-driver) |
| Azure Arc 서버 네트워크 요구사항 | [learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements](https://learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements) |
| ACR 이미지 서명 (Notary) | [learn.microsoft.com/en-us/azure/container-registry/container-registry-content-trust](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-content-trust) |
