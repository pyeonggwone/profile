# Implementation Guide: Hospital On-Premises Client — k3s Agent Method

> Applicable Scenario: Install k3s on Windows Server 2019 / 2022 hospital servers and integrate container-based client agents with Azure SaaS backend  
> Network Integration Reference: [hipaa-network.ver4.md](../Implement_Network/hipaa-network.ver4.md) — S2S VPN + NSG  
> HIPAA Standards: §164.312(e)(1) Transmission Security, §164.312(e)(2)(ii) Encryption in Transit, §164.312(b) Audit Controls  
> Version: v7 (2026-04-20 — Cross-link ver2 reflected)

---

## Deployment Method Selection Criteria

| Item | This Guide (k3s) | [Guide 06 (PowerShell Installer)](./06-windows-installer-client.ver2.md) |
|---|---|---|
| **Supported OS** | Windows Server 2019 / 2022 (64-bit) only | Windows Server 2012 R2 or later (general purpose) |
| **Runtime** | k3s (containerd) | Windows SCM (Service Control Manager) |
| **Deployment Unit** | Container image | ZIP bundle + PowerShell Installer |
| **Remote Update** | Arc GitOps (Flux) | Arc Run Command (Install.ps1) |
| **Hospital IT Skill Requirement** | High (basic K8s knowledge required) | Low (standard Windows operations) |

> **Selection Criteria**: Determine after confirming the hospital server OS. If the OS version is unclear or mixed, use [Guide 06 (PowerShell Installer)](./06-windows-installer-client.ver2.md).

---

## Overall Architecture

```
Hospital On-Premises (Windows Server 2019/2022)
  └─ k3s Single Node Cluster
      ├─ pii-masking (Pod)
      ├─ rabbitmq-producer (Pod)
      └─ config-sync (Pod)
          └─[S2S VPN — IPsec AES-256]─ Azure VPN Gateway (vpngw-medicalai-hub-us)
              └─ NSG (nsg-snet-aks) — Least-privilege access control
                  └─ AKS Microservices (10.2.10.0/24)
                      ├─ RabbitMQ Cluster
                      ├─ MySQL Flexible Server
                      └─ AI Analysis Module

Arc-enabled Server (Hospital On-Premises Server)
  └─[HTTPS 443]─ Azure Arc Service
      ├─ Flux (GitOps) — Automatic k3s manifest synchronization
      ├─ Azure Update Manager — OS patch management
      ├─ Machine Configuration — Compliance drift detection
      └─ Key Vault CSI Driver — Secret injection
```

---

## 1. Supported OS Matrix

| OS | k3s Windows Node Support | Arc Support | HIPAA Patch Management | Notes |
|---|---|---|---|---|
| Windows Server 2022 | ✅ Officially supported | ✅ | ✅ | **Recommended** |
| Windows Server 2019 | ✅ Officially supported | ✅ | ✅ | Supported |
| Windows Server 2016 or earlier | ❌ Not supported | ✅ | Conditional | → Use [Guide 06 (PowerShell Installer)](./06-windows-installer-client.ver2.md) |

> k3s Windows node requirement: containerd runtime is only supported on Windows Server 2019+.  
> Reference: [k3s Windows Support](https://docs.k3s.io/advanced#windows-agent-nodes)

---

## 2. Prerequisites

| Item | Requirement |
|---|---|
| OS | Windows Server 2019 / 2022 (64-bit) |
| CPU / Memory | 2 vCPU or more, 4 GB RAM or more |
| Disk | 20 GB or more (including image storage) |
| Network Ports (Outbound) | TCP 443 (HTTPS), TCP 5671 (AMQPS) — Allow outbound to Azure |
| VPN Equipment | IKEv2 support (hospital-side VPN device) |
| Hospital Public IP | Pre-notified to ISV (for Local Network Gateway registration) |
| Azure Subscription | ISV Azure subscription (Arc registration target) |
| Container Image Registry | Azure Container Registry (ACR) `acrmedicalai` — ISV managed |

---

## 3. ISV-Side Azure Pre-Configuration

### 3-1. Azure Container Registry Image Preparation

ISV development team builds 3 agent types as container images and pushes to ACR:

```bash
# Run in ISV development environment

# Build images (.NET 8 Linux-based — k3s uses Linux containers)
docker build -t pii-masking-service:v7.0 ./src/pii-masking
docker build -t rabbitmq-producer:v7.0 ./src/rabbitmq-producer
docker build -t config-sync:v7.0 ./src/config-sync

# Push to ACR
az acr login --name acrmedicalai
docker tag pii-masking-service:v7.0 acrmedicalai.azurecr.io/pii-masking-service:v7.0
docker tag rabbitmq-producer:v7.0 acrmedicalai.azurecr.io/rabbitmq-producer:v7.0
docker tag config-sync:v7.0 acrmedicalai.azurecr.io/config-sync:v7.0
docker push acrmedicalai.azurecr.io/pii-masking-service:v7.0
docker push acrmedicalai.azurecr.io/rabbitmq-producer:v7.0
docker push acrmedicalai.azurecr.io/config-sync:v7.0
```

> **Architecture clarification**: k3s is Linux container-based. If the hospital server only has Windows, [Guide 06 (PowerShell Installer)](./06-windows-installer-client.ver2.md) is recommended.

---

## 3-A. Architecture Premise Clarification

When deploying k3s to hospital on-premises, choose one of **two configurations**:

| Configuration | Hospital Server OS | k3s Role | Notes |
|---|---|---|---|
| **A. Linux Server** | Ubuntu 22.04 / RHEL 8 | k3s server (single node) | Recommended — Container native |
| **B. Windows Server + WSL2** | Windows Server 2022 | k3s via WSL2 | When hospital operates Windows only |

> This guide is based on **Configuration A (Linux Server)**. If the hospital server is Windows only, [Guide 06 (PowerShell Installer)](./06-windows-installer-client.ver2.md) is recommended.

---

### 3-2. VPN Configuration (ISV Responsibility)

**Step A. Register Local Network Gateway**

| Item | Value |
|---|---|
| Name | `lng-hospital-us-001` |
| IP address | Hospital public IP (collected in advance) |
| Address space | Hospital internal CIDR (`192.168.10.0/24`) |

**Step B. Create VPN Connection**

| Item | Value |
|---|---|
| Connection type | Site-to-site (IPsec) |
| Local network gateway | `lng-hospital-us-001` |
| Shared key (PSK) | Key Vault `kv-medicalai-shared` → Secret `vpn-psk-hospital-us` |
| IPsec Policy | IKEv2 + AES-256 + SHA-256 |

**Step C. Add NSG Rule**

| Item | Value |
|---|---|
| Name | `allow-hospital-us-001-to-aks` |
| Source | `192.168.10.0/24` |
| Destination | `10.2.10.0/24` (AKS Subnet) |
| Destination port ranges | `443, 5671` |
| Action | Allow |

### 3-3. Arc GitOps Repository Configuration (ISV Responsibility)

ISV manages k3s manifests in a dedicated GitOps repository:

```
git-repo: medicalai-k3s-manifests (private)
  └─ hospitals/
      ├─ base/
      │   ├─ namespace.yaml
      │   ├─ pii-masking-deployment.yaml
      │   ├─ rabbitmq-producer-deployment.yaml
      │   └─ config-sync-deployment.yaml
      └─ hospital-us-001/
          └─ kustomization.yaml  # Per-hospital overrides (image tags, secret references)
```

---

## 4. Hospital Server Installation Procedure

### 4-1. S2S VPN Connection Configuration (Hospital Network Team)

Configure IKEv2 tunnel on hospital VPN device (Cisco / Palo Alto / FortiGate):

| Item | Value |
|---|---|
| Remote IP | `pip-vpngw-medicalai-hub-us` (provided by ISV) |
| PSK | Provided by ISV (ISV retrieves from Key Vault and delivers via separate channel) |
| IKE Version | IKEv2 |
| Encryption | AES-256 |
| Hash | SHA-256 |
| Local CIDR | `192.168.10.0/24` |
| Remote CIDR | `10.2.10.0/24` |

```bash
# Verify VPN tunnel (from hospital server)
ping 10.2.0.1  # Azure VPN Gateway internal IP
```

### 4-2. k3s Installation (Hospital Server — Linux)

```bash
# k3s single node installation (server mode)
curl -sfL https://get.k3s.io | sh -s - \
  --disable traefik \
  --disable servicelb \
  --write-kubeconfig-mode 644

# Verify installation
sudo systemctl status k3s
sudo kubectl get nodes
# NAME         STATUS   ROLES                  AGE
# hospital-01  Ready    control-plane,master   1m
```

### 4-3. Azure Arc Agent Registration

```bash
# Install Azure Arc Connected Machine Agent (Linux)
wget https://aka.ms/azcmagent -O ~/install_linux_azcmagent.sh
sudo bash ~/install_linux_azcmagent.sh

# Arc registration (register to ISV Azure subscription)
sudo azcmagent connect \
  --resource-group rg-medicalai-arc \
  --tenant-id <ISV_TENANT_ID> \
  --location eastus \
  --subscription-id <ISV_SUBSCRIPTION_ID>
```

### 4-4. Key Vault CSI Driver Installation and Secret Mount

```bash
# Install Secrets Store CSI Driver + Azure Key Vault Provider
sudo kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/main/deploy/rbac-secretproviderclass.yaml
sudo kubectl apply -f https://raw.githubusercontent.com/Azure/secrets-store-csi-driver-provider-azure/master/deployment/provider-azure-installer.yaml

# Create SecretProviderClass (manifest provided by ISV)
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

> PSK plaintext is not stored in local files. Key Vault CSI Driver mounts it at runtime when Pod starts. (§164.312(a)(2)(iv))

### 4-5. Arc GitOps Flux Integration (ISV Responsibility — Configure via Arc Portal)

> Azure Portal → Azure Arc → Servers → Target Server → GitOps → + Create

| Item | Value |
|---|---|
| Configuration name | `medicalai-agents` |
| Namespace | `medicalai` |
| Scope | Namespace |
| Repository URL | ISV GitOps repository URL |
| Branch | `main` |
| Path | `hospitals/hospital-us-001` |
| Sync interval | 5 minutes |

Flux periodically synchronizes the GitOps repository and automatically deploys when manifests change.

### 4-6. Deployment Verification

```bash
sudo kubectl get pods -n medicalai
# NAME                              READY   STATUS    RESTARTS
# pii-masking-xxx                   1/1     Running   0
# rabbitmq-producer-xxx             1/1     Running   0
# config-sync-xxx                   1/1     Running   0

# Check RabbitMQ transmission logs
sudo kubectl logs -n medicalai -l app=rabbitmq-producer --tail=30 | grep "Published\|Error"

# Verify Key Vault secret mount
sudo kubectl exec -n medicalai deployment/config-sync -- ls /mnt/secrets-store/
```

---

## 5. Azure Integration Verification

### 5-1. VPN Tunnel

> Azure Portal → VPN Gateway `vpngw-medicalai-hub-us` → Connections → `lng-hospital-us-001`  
> Connection status: Confirm **Connected**

### 5-2. Arc Registration Status

> Azure Portal → Azure Arc → Servers → `hospital-us-001` → Confirm **Connected**

### 5-3. GitOps Sync Status

> Azure Portal → Azure Arc → Servers → Target Server → GitOps  
> Compliance state: Confirm **Compliant**

---

## 6. Image Update (New Version Deployment)

When ISV pushes a new image to ACR and changes the image tag in the GitOps repository, Flux automatically synchronizes:

```bash
# ISV development team — push new image
docker push acrmedicalai.azurecr.io/pii-masking-service:v7.1

# Change image tag in GitOps repository (PR → merge)
# hospitals/hospital-us-001/kustomization.yaml
# images:
#   - name: acrmedicalai.azurecr.io/pii-masking-service
#     newTag: v7.1

# Flux auto-detects within 5 minutes → rolling update
```

> ISV can manage image updates without direct involvement of hospital IT team.

---

## 7. HIPAA Requirements Checklist

| Item | Implementation | HIPAA Clause |
|---|---|---|
| Encryption in transit | S2S VPN IPsec AES-256 + TLS 1.2 or later | §164.312(e)(2)(ii) |
| No local storage of PSK / secrets | Key Vault CSI Driver — Runtime mount at Pod startup | §164.312(a)(2)(iv) |
| Container image integrity | ACR image signing (Notary v2 / cosign) recommended | §164.312(c)(1) |
| Least privilege | Pod SecurityContext — nonRoot, readOnlyRootFilesystem | §164.312(a)(1) |
| Network access restriction | NSG + K8s NetworkPolicy (restrict inter-Pod communication) | §164.312(e)(1) |
| Audit logs | Pod logs → Azure Log Analytics (Fluent Bit DaemonSet) | §164.312(b) |
| OS patch management | Azure Arc + Azure Update Manager | §164.312(a)(2)(ii) |
| Configuration compliance | Arc Machine Configuration + GitOps Compliance | §164.306(a)(1) |

---

## 8. Reference Links

| Purpose | Link |
|---|---|
| k3s Official Documentation | [docs.k3s.io](https://docs.k3s.io) |
| k3s Installation Guide | [docs.k3s.io/quick-start](https://docs.k3s.io/quick-start) |
| Azure Arc GitOps (Flux) | [learn.microsoft.com/en-us/azure/azure-arc/kubernetes/tutorial-use-gitops-flux2](https://learn.microsoft.com/en-us/azure/azure-arc/kubernetes/tutorial-use-gitops-flux2) |
| Key Vault CSI Driver | [learn.microsoft.com/en-us/azure/aks/csi-secrets-store-driver](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-driver) |
| Azure Arc Server Network Requirements | [learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements](https://learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements) |
| ACR Image Signing (Notary) | [learn.microsoft.com/en-us/azure/container-registry/container-registry-content-trust](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-content-trust) |
