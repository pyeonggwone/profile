# 구현 가이드: VPN Gateway (병원 ↔ Azure)

> 근거 문서: [arch-vpn-gateway.md](../arch-vpn-gateway.md)  
> HIPAA 기준: §164.312(e)(1) 전송 보안, §164.312(e)(2)(ii) PHI 암호화

---

## 전제조건

- Azure 구독 3개 생성 완료: Hub, Shared, AI+SW Spoke
- Microsoft HIPAA BAA 체결 완료
- 병원 측 VPN 장비 확보 (Cisco / Palo Alto / FortiGate — IKEv2 지원)
- 병원 온프레미스 공인 IP 확보

---

## Step 1. Hub VNet 및 서브넷 생성

```bash
# 변수 설정
RG_HUB="rg-medicalai-hub"
LOCATION="koreacentral"         # 미국 병원 연동 시 eastus2 로 변경
HUB_VNET="vnet-hub"
HUB_PREFIX="10.0.0.0/16"

# 리소스 그룹 생성
az group create --name $RG_HUB --location $LOCATION

# Hub VNet 생성
az network vnet create \
  --resource-group $RG_HUB \
  --name $HUB_VNET \
  --address-prefix $HUB_PREFIX \
  --location $LOCATION

# GatewaySubnet (이름 변경 불가 — Azure 예약 이름)
az network vnet subnet create \
  --resource-group $RG_HUB \
  --vnet-name $HUB_VNET \
  --name GatewaySubnet \
  --address-prefix 10.0.0.0/27

# AzureFirewallSubnet (이름 변경 불가)
az network vnet subnet create \
  --resource-group $RG_HUB \
  --vnet-name $HUB_VNET \
  --name AzureFirewallSubnet \
  --address-prefix 10.0.1.0/26

# AzureBastionSubnet (이름 변경 불가)
az network vnet subnet create \
  --resource-group $RG_HUB \
  --vnet-name $HUB_VNET \
  --name AzureBastionSubnet \
  --address-prefix 10.0.2.0/27
```

---

## Step 2. VPN Gateway 배포 (Active-Active, Zone Redundant)

```bash
# Public IP 2개 생성 (Active-Active 구성)
az network public-ip create \
  --resource-group $RG_HUB \
  --name pip-vpngw-1 \
  --sku Standard \
  --zone 1 2 3 \
  --allocation-method Static

az network public-ip create \
  --resource-group $RG_HUB \
  --name pip-vpngw-2 \
  --sku Standard \
  --zone 1 2 3 \
  --allocation-method Static

# VPN Gateway 생성 (배포 약 30~45분 소요)
# SKU: VpnGw2AZ — Zone Redundant, 최대 1 Gbps
# 대용량 병원은 VpnGw5AZ (10 Gbps) 선택
az network vnet-gateway create \
  --resource-group $RG_HUB \
  --name vpngw-medicalai-hub \
  --vnet $HUB_VNET \
  --gateway-type Vpn \
  --vpn-type RouteBased \
  --sku VpnGw2AZ \
  --public-ip-addresses pip-vpngw-1 pip-vpngw-2 \
  --enable-bgp true \
  --asn 65515 \
  --location $LOCATION
```

> **HIPAA §164.312(e)(1)**: Route-Based + IKEv2 강제 → IPsec AES-256-GCM 암호화 보장

---

## Step 3. IPsec 정책 강화 (HIPAA 준수)

```bash
# IKEv2 전용 + AES-256 + SHA-256 + DH Group 14 이상 정책 적용
# 기본 정책은 보안 수준 낮은 알고리즘 포함 → 명시적 정책으로 교체

az network vpn-connection ipsec-policy add \
  --resource-group $RG_HUB \
  --connection-name conn-hospital-a \
  --ike-integrity SHA256 \
  --ike-encryption AES256 \
  --dh-group DHGroup14 \
  --ipsec-integrity GCMAES256 \
  --ipsec-encryption GCMAES256 \
  --pfs-group PFS14 \
  --sa-lifetime 28800 \
  --sa-data-size-kilobytes 102400000
```

---

## Step 4. 로컬 네트워크 게이트웨이 (병원 측 정보 등록)

```bash
# 병원 A 등록 예시
# HOSPITAL_IP: 병원 VPN 장비의 공인 IP
# HOSPITAL_CIDR: 병원 내부망 대역

az network local-gateway create \
  --resource-group $RG_HUB \
  --name lgw-hospital-a \
  --gateway-ip-address <HOSPITAL_A_PUBLIC_IP> \
  --local-address-prefixes 192.168.10.0/24 \
  --asn 65001 \
  --bgp-peering-address 192.168.10.1

# 추가 병원 등록 시 동일 패턴으로 반복 (lgw-hospital-b, lgw-hospital-c ...)
```

> **격리 원칙 (DongJoo 지적 사항)**: 병원마다 별도 Local Network Gateway + Connection 생성 → 병원 간 라우팅 격리 보장

---

## Step 5. VPN 연결 생성

```bash
# Key Vault에서 PSK 가져옴 (직접 하드코딩 금지 — HIPAA §164.312(a)(2)(iv))
PSK=$(az keyvault secret show \
  --vault-name kv-medicalai-shared \
  --name vpn-psk-hospital-a \
  --query value -o tsv)

az network vpn-connection create \
  --resource-group $RG_HUB \
  --name conn-hospital-a \
  --vnet-gateway1 vpngw-medicalai-hub \
  --local-gateway2 lgw-hospital-a \
  --shared-key $PSK \
  --enable-bgp true \
  --connection-protocol IKEv2
```

---

## Step 6. Azure Firewall Premium 배포

```bash
# Firewall Policy 생성 (Premium SKU — TLS Inspection + IDPS)
az network firewall policy create \
  --resource-group $RG_HUB \
  --name afwp-medicalai \
  --sku Premium \
  --threat-intel-mode Alert \
  --idps-mode Deny              # HIPAA 환경: Alert 아닌 Deny 모드 필수

# Firewall 배포
az network firewall create \
  --resource-group $RG_HUB \
  --name afw-medicalai-hub \
  --sku-name AZFW_VNet \
  --sku-tier Premium \
  --firewall-policy afwp-medicalai \
  --vnet-name $HUB_VNET \
  --location $LOCATION \
  --zones 1 2 3

# 진단 로그 → Log Analytics (HIPAA §164.312(b) 6년 보존)
az monitor diagnostic-settings create \
  --resource $(az network firewall show -g $RG_HUB -n afw-medicalai-hub --query id -o tsv) \
  --name diag-afw \
  --workspace $(az monitor log-analytics workspace show -g rg-medicalai-shared -n law-medicalai --query id -o tsv) \
  --logs '[{"category":"AzureFirewallNetworkRule","enabled":true,"retentionPolicy":{"days":2190,"enabled":true}},{"category":"AzureFirewallApplicationRule","enabled":true,"retentionPolicy":{"days":2190,"enabled":true}}]'
```

> `retentionPolicy.days: 2190` = 6년 (HIPAA §164.312(b) 감사 로그 보존 요건)

---

## Step 7. UDR(강제 터널링) 설정

```bash
# VPN GW에서 들어온 트래픽을 반드시 Firewall 경유하도록 강제
AFW_PRIVATE_IP=$(az network firewall show -g $RG_HUB -n afw-medicalai-hub \
  --query "ipConfigurations[0].privateIPAddress" -o tsv)

az network route-table create \
  --resource-group $RG_HUB \
  --name rt-hub-to-firewall

az network route-table route create \
  --resource-group $RG_HUB \
  --route-table-name rt-hub-to-firewall \
  --name route-all-to-firewall \
  --next-hop-type VirtualAppliance \
  --next-hop-ip-address $AFW_PRIVATE_IP \
  --address-prefix 0.0.0.0/0

# GatewaySubnet에 UDR 연결
az network vnet subnet update \
  --resource-group $RG_HUB \
  --vnet-name $HUB_VNET \
  --name GatewaySubnet \
  --route-table rt-hub-to-firewall
```

---

## Step 8. VNet Peering (Hub ↔ Spoke)

```bash
# Hub → AI Spoke 피어링
az network vnet peering create \
  --resource-group $RG_HUB \
  --name peer-hub-to-ai-spoke \
  --vnet-name $HUB_VNET \
  --remote-vnet /subscriptions/<AI_SUB_ID>/resourceGroups/rg-medicalai-ai/providers/Microsoft.Network/virtualNetworks/vnet-ai-spoke \
  --allow-vnet-access true \
  --allow-forwarded-traffic true \
  --allow-gateway-transit true   # Hub의 VPN GW를 Spoke가 공유

# AI Spoke → Hub 피어링 (역방향)
az network vnet peering create \
  --resource-group rg-medicalai-ai \
  --name peer-ai-spoke-to-hub \
  --vnet-name vnet-ai-spoke \
  --remote-vnet /subscriptions/<HUB_SUB_ID>/resourceGroups/$RG_HUB/providers/Microsoft.Network/virtualNetworks/$HUB_VNET \
  --allow-vnet-access true \
  --allow-forwarded-traffic true \
  --use-remote-gateways true     # Spoke가 Hub VPN GW 사용
```

---

## Step 9. Azure Arc Agent 설치 (온프레미스 VM 관리)

병원 온프레미스 Windows Server에서 실행:

```powershell
# 1. 서비스 주체(Service Principal) 생성 (Azure 측에서 사전 준비)
# az ad sp create-for-rbac --name sp-arc-hospital-a --role "Azure Connected Machine Onboarding" \
#   --scopes /subscriptions/<SHARED_SUB_ID>/resourceGroups/rg-medicalai-shared

# 2. Arc 에이전트 설치 스크립트 다운로드 (Azure Portal > Azure Arc > Add Server)
# 병원 서버에서 아래 실행

Invoke-WebRequest -Uri https://aka.ms/azcmagent-windows -OutFile "$env:TEMP\install_windows_azcmagent.ps1"
& "$env:TEMP\install_windows_azcmagent.ps1"

# 3. 에이전트 등록
& "$env:ProgramFiles\AzureConnectedMachineAgent\azcmagent.exe" connect `
  --service-principal-id "<SP_APP_ID>" `
  --service-principal-secret "<SP_SECRET>" `
  --tenant-id "<TENANT_ID>" `
  --subscription-id "<SHARED_SUB_ID>" `
  --resource-group "rg-medicalai-shared" `
  --location $LOCATION
```

> **목적**: 온프레미스 VM 보안 패치 자동화, 보안 기준선 적용 (HIPAA §164.312(a)(1) 접근 제어)

---

## Step 10. 병원 측 VPN 장비 설정 (FortiGate 예시)

```
# FortiGate CLI 설정 예시 (IKEv2 + AES-256)

config vpn ipsec phase1-interface
  edit "azure-medicalai"
    set interface "wan1"
    set ike-version 2
    set keylife 28800
    set peertype any
    set proposal aes256-sha256
    set dhgrp 14
    set remote-gw <AZURE_VPN_GW_PUBLIC_IP_1>
    set psksecret <PSK_FROM_KEYVAULT>
  next
end

config vpn ipsec phase2-interface
  edit "azure-medicalai-p2"
    set phase1name "azure-medicalai"
    set proposal aes256gcm-prfsha256
    set dhgrp 14
    set keylifeseconds 3600
    set src-addr-type subnet
    set src-subnet 192.168.10.0 255.255.255.0
    set dst-addr-type subnet
    set dst-subnet 10.0.0.0 255.255.0.0
  next
end
```

---

## 검증 체크리스트

| 항목 | 확인 방법 | 기대 결과 |
|------|-----------|-----------|
| VPN 연결 상태 | `az network vpn-connection show --name conn-hospital-a -g $RG_HUB --query connectionStatus` | `Connected` |
| BGP 피어링 | `az network vnet-gateway list-bgp-peer-status -g $RG_HUB -n vpngw-medicalai-hub` | `Connected` |
| Firewall 트래픽 통과 | Azure Firewall 로그에서 병원 IP → Spoke 트래픽 확인 | Allow 규칙 매칭 |
| Private Endpoint 해석 | 병원 → Azure 내부에서 `nslookup <storage>.blob.core.windows.net` | 10.x.x.x 반환 |
| 감사 로그 보존 기간 | Log Analytics workspace 설정 | 2190일 (6년) |
