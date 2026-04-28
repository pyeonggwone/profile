# 구현 가이드: ExpressRoute (병원 ↔ Azure)

> 근거 문서: [arch-expressroute.md](../arch-expressroute.md)  
> HIPAA 기준: §164.312(e)(1) 전송 보안, §164.312(e)(2)(ii) PHI 암호화 — VPN Gateway 대비 인터넷 미경유로 가장 강력한 충족

---

## 전제조건

- Microsoft HIPAA BAA 체결 완료
- ExpressRoute Connectivity Provider 계약 완료 (Equinix / Megaport / AT&T 등)
- 병원 측 Customer Edge Router (BGP 지원, AS 번호 할당)
- Peering Location 결정 (미국 예: Equinix DC-2 Washington D.C. / 한국 예: KINX Seoul)
- ExpressRoute 제공 파트너와 별도 BAA 또는 DPA 체결

---

## Step 1. ExpressRoute 회로(Circuit) 생성

```bash
RG_HUB="rg-medicalai-hub"
LOCATION="eastus2"              # 한국 병원: koreacentral

# ExpressRoute Circuit 생성
az network express-route create \
  --resource-group $RG_HUB \
  --name er-medicalai-hospital-a \
  --location $LOCATION \
  --bandwidth 1000 \            # 1 Gbps — 병원 규모에 따라 조정
  --peering-location "Washington DC" \
  --provider "Equinix" \
  --sku-family MeteredData \    # UnlimitedData: 대용량 전송 시
  --sku-tier Premium            # 글로벌 연결성 필요 시 Premium, 리전 내만이면 Standard

# Service Key 확인 → Connectivity Provider에 전달
az network express-route show \
  --resource-group $RG_HUB \
  --name er-medicalai-hospital-a \
  --query serviceKey -o tsv
```

> Service Key를 Connectivity Provider에 제공하면, 제공사가 병원 Edge Router와 Azure 간 물리 회선을 프로비저닝한다.  
> 프로비저닝 완료 후 Circuit 상태: `Provisioned` (보통 수일 소요).

---

## Step 2. Private Peering 구성

> **PHI 전송에는 Private Peering만 사용.** Microsoft Peering은 공용 서비스용이며 PHI 전송 금지.

```bash
# Provider 프로비저닝 완료 확인
az network express-route show \
  --resource-group $RG_HUB \
  --name er-medicalai-hospital-a \
  --query serviceProviderProvisioningState -o tsv
# 기대값: Provisioned

# Private Peering 설정
az network express-route peering create \
  --resource-group $RG_HUB \
  --circuit-name er-medicalai-hospital-a \
  --peering-type AzurePrivatePeering \
  --peer-asn 65001 \                    # 병원 측 BGP AS 번호
  --primary-peer-address-prefix 192.168.100.0/30 \   # Primary 링크 /30
  --secondary-peer-address-prefix 192.168.100.4/30 \ # Secondary 링크 /30 (이중화)
  --vlan-id 100 \                       # Provider 할당 VLAN ID
  --shared-key $(az keyvault secret show \
      --vault-name kv-medicalai-shared \
      --name er-bgp-key-hospital-a \
      --query value -o tsv)             # BGP MD5 인증 키 — Key Vault에서 주입
```

---

## Step 3. MACsec 활성화 (ExpressRoute Direct 사용 시)

ExpressRoute Direct(10G/100G 전용 포트)를 사용하는 경우 MACsec으로 Layer 2 암호화 추가.

```bash
# ExpressRoute Direct Port 조회
az network express-route port list --resource-group $RG_HUB --query "[].name" -o tsv

# MACsec 활성화 (AES-256 + GCM)
az network express-route port update \
  --resource-group $RG_HUB \
  --name <ER_DIRECT_PORT_NAME> \
  --macsec-cipher-suite GcmAes256 \
  --macsec-cak $(az keyvault secret show \
      --vault-name kv-medicalai-shared \
      --name er-macsec-cak \
      --query value -o tsv) \
  --macsec-ckn $(az keyvault secret show \
      --vault-name kv-medicalai-shared \
      --name er-macsec-ckn \
      --query value -o tsv)
```

> **HIPAA §164.312(e)(2)(ii)**: MACsec(L2) + TLS 1.3(L7) = 이중 암호화 계층 충족

---

## Step 4. ExpressRoute Gateway 배포

```bash
# Public IP (Zone Redundant)
az network public-ip create \
  --resource-group $RG_HUB \
  --name pip-ergw \
  --sku Standard \
  --zone 1 2 3 \
  --allocation-method Static

# ExpressRoute Gateway 배포 (약 30~45분 소요)
# SKU: UltraPerformance — 10 Gbps, Zone Redundant
az network vnet-gateway create \
  --resource-group $RG_HUB \
  --name ergw-medicalai-hub \
  --vnet vnet-hub \
  --gateway-type ExpressRoute \
  --sku UltraPerformance \
  --public-ip-addresses pip-ergw \
  --location $LOCATION
```

> ExpressRoute Gateway SLA: **99.95%** (UltraPerformance + Zone Redundant)

---

## Step 5. Gateway ↔ Circuit 연결

```bash
ER_CIRCUIT_ID=$(az network express-route show \
  --resource-group $RG_HUB \
  --name er-medicalai-hospital-a \
  --query id -o tsv)

az network vpn-connection create \
  --resource-group $RG_HUB \
  --name conn-er-hospital-a \
  --vnet-gateway1 ergw-medicalai-hub \
  --express-route-circuit2 $ER_CIRCUIT_ID \
  --routing-weight 10
```

---

## Step 6. UDR — 강제 터널링 (Azure Firewall 경유)

```bash
AFW_PRIVATE_IP=$(az network firewall show -g $RG_HUB -n afw-medicalai-hub \
  --query "ipConfigurations[0].privateIPAddress" -o tsv)

az network route-table create \
  --resource-group $RG_HUB \
  --name rt-er-to-firewall

# ExpressRoute에서 들어온 모든 트래픽 → Azure Firewall 강제
az network route-table route create \
  --resource-group $RG_HUB \
  --route-table-name rt-er-to-firewall \
  --name route-all-to-afw \
  --next-hop-type VirtualAppliance \
  --next-hop-ip-address $AFW_PRIVATE_IP \
  --address-prefix 0.0.0.0/0

# GatewaySubnet에 적용
az network vnet subnet update \
  --resource-group $RG_HUB \
  --vnet-name vnet-hub \
  --name GatewaySubnet \
  --route-table rt-er-to-firewall
```

> Azure Firewall IDPS 모드: `Deny` (의료 데이터 환경 필수)

---

## Step 7. Azure Policy — PHI 데이터 거주지 강제

```bash
# East US 2 외 리전 리소스 배포 거부 정책 할당
az policy assignment create \
  --name "deny-non-eastus2-resources" \
  --policy "/providers/Microsoft.Authorization/policyDefinitions/e765b5de-1225-4ba3-bd56-1ac6695af988" \
  --scope "/subscriptions/<AI_SUB_ID>" \
  --params '{"listOfAllowedLocations": {"value": ["eastus2"]}}'

# Public Network Access 차단 (PHI 서비스 전체)
az policy assignment create \
  --name "deny-public-network-access" \
  --policy "/providers/Microsoft.Authorization/policyDefinitions/b0f33259-77d7-4c9e-aac6-3aabcfae693c" \
  --scope "/subscriptions/<AI_SUB_ID>"

# HIPAA HITRUST 9.2 Built-in Initiative 할당
az policy assignment create \
  --name "hipaa-hitrust-9.2" \
  --policy-set-definition "/providers/Microsoft.Authorization/policySetDefinitions/a169a624-5599-4385-a696-c8d643089fab" \
  --scope "/subscriptions/<AI_SUB_ID>"
```

---

## Step 8. Log Analytics 감사 로그 설정 (HIPAA §164.312(b))

```bash
# Log Analytics Workspace 생성 (Shared Subscription)
az monitor log-analytics workspace create \
  --resource-group rg-medicalai-shared \
  --workspace-name law-medicalai \
  --location $LOCATION \
  --retention-time 2190 \       # 6년 = 2190일
  --sku PerGB2018

# ExpressRoute Gateway 진단 로그 활성화
ER_GW_ID=$(az network vnet-gateway show -g $RG_HUB -n ergw-medicalai-hub --query id -o tsv)
LAW_ID=$(az monitor log-analytics workspace show -g rg-medicalai-shared -n law-medicalai --query id -o tsv)

az monitor diagnostic-settings create \
  --resource $ER_GW_ID \
  --name diag-ergw \
  --workspace $LAW_ID \
  --logs '[
    {"category":"GatewayDiagnosticLog","enabled":true},
    {"category":"TunnelDiagnosticLog","enabled":true},
    {"category":"RouteDiagnosticLog","enabled":true},
    {"category":"IKEDiagnosticLog","enabled":true}
  ]'
```

---

## Step 9. 병원 측 CE Router 설정 (BGP 예시 — Cisco IOS-XE)

```
! Cisco IOS-XE BGP 설정 예시

router bgp 65001
 bgp router-id 192.168.100.1
 neighbor 192.168.100.2 remote-as 12076      ! Azure BGP AS
 neighbor 192.168.100.2 password <BGP_MD5_KEY>
 neighbor 192.168.100.2 soft-reconfiguration inbound
 !
 address-family ipv4
  neighbor 192.168.100.2 activate
  network 192.168.10.0 mask 255.255.255.0    ! 병원 내부망 광고
 exit-address-family
!
! MACsec (ExpressRoute Direct 사용 시)
macsec policy HIPAA-POLICY
 cipher-suite GCM-AES-256
 include-icv-indicator
 sak-rekey-interval 60
!
interface GigabitEthernet0/0/0
 macsec network-link
 macsec policy HIPAA-POLICY
```

---

## Step 10. 이중화 검증 — Failover 테스트

```bash
# Primary 회선 BGP 강제 종료 후 Secondary 자동 전환 확인
az network express-route peering update \
  --resource-group $RG_HUB \
  --circuit-name er-medicalai-hospital-a \
  --peering-type AzurePrivatePeering \
  --state Disabled              # Primary 일시 비활성화

# Secondary 경로로 BGP 수렴 확인 (< 1분 기대)
az network vnet-gateway list-bgp-peer-status \
  --resource-group $RG_HUB \
  --name ergw-medicalai-hub \
  --query "[].{Peer:neighbor,State:connectedDuration,Routes:routesReceived}"

# 복구
az network express-route peering update \
  --resource-group $RG_HUB \
  --circuit-name er-medicalai-hospital-a \
  --peering-type AzurePrivatePeering \
  --state Enabled
```

---

## 검증 체크리스트

| 항목 | 확인 방법 | 기대 결과 |
|------|-----------|-----------|
| Circuit 상태 | `az network express-route show --query serviceProviderProvisioningState` | `Provisioned` |
| BGP 피어링 | `az network vnet-gateway list-bgp-peer-status` | `Connected` |
| 인터넷 경로 없음 | 병원 서버에서 `traceroute <AKS_PRIVATE_IP>` | Azure 퍼블릭 IP 경유 없음 |
| Firewall IDPS | Azure Firewall 정책 > IDPS 모드 | `Deny` |
| Policy 적용 | Defender for Cloud 규정 준수 > HIPAA HITRUST 9.2 | 위반 항목 0 |
| 로그 보존 | Log Analytics workspace retention | 2190일 |
| MACsec (Direct 사용 시) | `az network express-route port show --query macsecConfig` | `GcmAes256` |
