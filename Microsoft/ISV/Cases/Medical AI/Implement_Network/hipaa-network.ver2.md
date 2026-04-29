# HIPAA 네트워크 구현 가이드 — MedicalAI AiTiA ECO CENTER

> **적용 규정**: §164.312(e)(1) 전송 보안, §164.312(e)(2)(ii) 전송 중 암호화, §164.312(b) 감사 통제
> **구현 방식**: Azure Portal GUI 기준
> **프로젝트 도메인**: `medicalai.onmicrosoft.com`
> **버전**: v2 (2026-04-20 — HIPAA 검토 보완 반영)

---

## 목차

1. [Azure VPN Gateway — 전송 중 암호화](#1-azure-vpn-gateway)
2. [Azure Firewall Premium — 네트워크 전송 보안](#2-azure-firewall-premium)
3. [Private Endpoint — 공인 인터넷 경유 차단](#3-private-endpoint)
4. [TLS 최소 버전 강제 설정](#3-4-tls-최소-버전-강제-설정)
5. [NSG — 서브넷 레벨 접근 통제](#3-5-nsgnetwork-security-group--서브넷-레벨-접근-통제)
6. [요약 — HIPAA 조항별 구현 매핑](#요약--hipaa-조항별-구현-매핑)

---

## 1. Azure VPN Gateway

**HIPAA 관련 조항**: §164.312(e)(1) 전송 보안, §164.312(e)(2)(ii) 전송 중 암호화

---

### 1-1. VPN Gateway 생성

**중분류: Gateway 프로비저닝**

> Azure Portal → Virtual Network Gateways → + Create

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 기본 정보 | Name | `vpngw-medicalai-hub-kr` |
| | Region | Korea Central |
| | Gateway type | VPN |
| | VPN type | Route-based |
| SKU 선택 | Gateway SKU | `VpnGw2` |
| | Generation | Generation2 |
| | Zone redundancy | Zone-redundant (az 1,2,3) |
| VNet 연결 | Virtual network | `vnet-hub-kr` |
| | Subnet | GatewaySubnet (`10.1.255.0/27`) |
| 공인 IP | Public IP name | `pip-vpngw-medicalai-hub-kr` |
| | SKU | Standard |
| Active-Active | Enable active-active mode | **켬** |
| BGP | Configure BGP | **켬** |
| | Autonomous System Number (ASN) | `65515` |

완료 후 **Review + create** → **Create** 클릭

---

### 1-2. Local Network Gateway (병원 온프레미스 정보 등록)

**중분류: 병원 측 네트워크 정의**

> Azure Portal → Local Network Gateways → + Create

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 기본 정보 | Name | `lng-hospitalA-onprem` |
| | Region | Korea Central |
| 온프레미스 정보 | IP address | `203.0.113.10` (Hospital A 공인 IP) |
| | Address space | `192.168.10.0/24` |
| BGP 설정 | Configure BGP settings | **켬** |
| | ASN | `65001` |
| | BGP peer IP address | `192.168.10.1` |

---

### 1-3. VPN Connection 생성 (IPsec/IKEv2 + AES-256)

**중분류: IPsec 터널 암호화 설정**

> Azure Portal → Virtual Network Gateways → `vpngw-medicalai-hub-kr` → Connections → + Add

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 기본 정보 | Name | `conn-hospitalA-s2s` |
| | Connection type | Site-to-site (IPsec) |
| 연결 대상 | Local network gateway | `lng-hospitalA-onprem` |
| 인증 | Shared key (PSK) | *(Key Vault secret `vpn-psk-hospitalA` 값 사용)* |
| BGP | Enable BGP | **켬** |

**Custom IPsec Policy 적용 (HIPAA 요구 AES-256)**

> Connection 생성 후 → `conn-hospitalA-s2s` → Configuration → Use custom IPsec/IKE policy: **켬**

| 소분류 | 항목 | 예시 값 (HIPAA 권고 설정) |
|---|---|---|
| IKE Phase 1 | IKE encryption | `AES256` |
| | IKE integrity | `SHA256` |
| | DH Group | `DHGroup14` |
| IKE Phase 2 | IPsec encryption | `GCMAES256` |
| | IPsec integrity | `GCMAES256` |
| | PFS Group | `PFS2048` |
| | SA Lifetime (seconds) | `28800` |

> HIPAA 포인트: §164.312(e)(2)(ii) — AES-256 암호화 구현으로 전송 중 ePHI 보호
>
> **PSK 관리 정책**: PSK는 Key Vault secret(`vpn-psk-hospitalA`)으로 관리. 교체 주기는 연 1회(또는 직원/계약 변경 시 즉시). 인증서 기반 IKEv2(EAP-TLS) 전환이 권고되나, 온프레미스 VPN 장비 미지원 시 PSK + Key Vault 조합을 허용된 대안으로 채택.

---

### 1-4. VPN Diagnostics 활성화

**중분류: 연결 상태 감사 로깅**

> `vpngw-medicalai-hub-kr` → Diagnostic settings → + Add diagnostic setting

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 설정 이름 | Diagnostic setting name | `diag-vpngw-hipaa` |
| 로그 카테고리 | GatewayDiagnosticLog | ✅ |
| | TunnelDiagnosticLog | ✅ |
| | RouteDiagnosticLog | ✅ |
| | IKEDiagnosticLog | ✅ |
| 전송 대상 | Send to Log Analytics workspace | `law-medicalai-shared` |
| 보존 기간 | Retention (days) | `2190` *(6년, HIPAA §164.312(b) 요구)* |

---

## 2. Azure Firewall Premium

**HIPAA 관련 조항**: §164.312(e)(1) 전송 보안, §164.312(b) 감사 통제

---

### 2-1. Firewall Premium 배포

**중분류: Firewall 인스턴스 생성**

> Azure Portal → Firewalls → + Create

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 기본 정보 | Name | `afw-medicalai-hub-kr` |
| | Region | Korea Central |
| | Tier | **Premium** *(TLS 검사 및 IDPS 필수)* |
| 네트워크 | Virtual network | `vnet-hub-kr` |
| | Subnet | AzureFirewallSubnet (`10.1.0.0/26`) |
| 공인 IP | Public IP | `pip-afw-medicalai-hub` |
| Firewall policy | Create new | `afwpol-medicalai-hipaa` |

---

### 2-2. TLS 검사 활성화

**중분류: 전송 중 트래픽 복호화 검사**

> Firewall Policies → `afwpol-medicalai-hipaa` → TLS inspection → Enable

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 인증서 | Key Vault | `kv-medicalai-shared` |
| | Certificate | `afw-tls-inspection-cert` |
| | Managed Identity | `mi-afw-tls` |
| 검사 범위 | Inbound TLS inspection | ✅ |
| | Outbound TLS inspection | ✅ |

> HIPAA 포인트: 전송 중 암호화 트래픽 내부의 무결성 및 비정상 패턴 감지

---

### 2-3. IDPS (침입 탐지 및 방지) 설정

**중분류: IDPS 프로필 구성**

> Firewall Policies → `afwpol-medicalai-hipaa` → IDPS → Configure

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 모드 | IDPS mode | **Alert and Deny** |
| 서명 규칙 | Threat intelligence mode | **Alert and Deny** |
| | Threat intel allowlist | *(없음 — PHI 환경)* |
| 예외 없음 | Signature overrides | 기본값 유지 (HIPAA 환경에서 비권고) |

---

### 2-4. Network Rule — 병원 → Azure 허용 경로

**중분류: PHI 전송 경로 최소 권한 허용**

> Firewall Policies → Rule Collections → + Add network rule collection

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 컬렉션 | Name | `netrc-hospitalA-to-ai` |
| | Priority | `100` |
| | Action | Allow |
| Rule 1 (VPN → AKS) | Name | `allow-hospitalA-vpn-to-aks` |
| | Source | `192.168.10.0/24` |
| | Destination | `10.2.10.0/24` (AI Spoke AKS Subnet) |
| | Protocol | TCP |
| | Destination Port | `443` |
| Rule 2 (VPN → Storage) | Name | `allow-hospitalA-vpn-to-storage` |
| | Source | `192.168.10.0/24` |
| | Destination | `10.2.20.0/24` (Storage Private Endpoint Subnet) |
| | Protocol | TCP |
| | Destination Port | `443` |

---

### 2-5. Firewall 진단 로그

**중분류: 방화벽 감사 로그 전송**

> `afw-medicalai-hub-kr` → Diagnostic settings → + Add

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 설정 이름 | Name | `diag-afw-hipaa` |
| 로그 | AzureFirewallNetworkRule | ✅ |
| | AzureFirewallApplicationRule | ✅ |
| | AzureFirewallThreatIntelLog | ✅ |
| | AzureFirewallIDPSSignatureHitLogs | ✅ |
| 전송 대상 | Log Analytics workspace | `law-medicalai-shared` |
| 보존 기간 | Retention (days) | `2190` *(6년, HIPAA 요구)* |

---

## 3. Private Endpoint

**HIPAA 관련 조항**: §164.312(e)(1) 전송 보안 — 공용 인터넷 경유 차단

---

### 3-1. Storage Account Private Endpoint

**중분류: PHI 저장소 프라이빗 연결**

> Storage account → Networking → Private endpoint connections → + Private endpoint

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 기본 정보 | Name | `pe-storage-ecg-ai` |
| | Region | Korea Central |
| Resource | Resource type | `Microsoft.Storage/storageAccounts` |
| | Target sub-resource | `blob` |
| 네트워크 | Virtual network | `vnet-ai-spoke` |
| | Subnet | `snet-private-endpoints` (`10.2.20.0/27`) |
| DNS | Integrate with private DNS zone | ✅ |
| | Private DNS zone | `privatelink.blob.core.windows.net` |

---

### 3-2. Key Vault Private Endpoint

**중분류: 키 관리 서비스 프라이빗 연결**

> Key Vault → Networking → Private endpoint connections → + Private endpoint

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 기본 정보 | Name | `pe-kv-medicalai-shared` |
| Resource | Target sub-resource | `vault` |
| 네트워크 | Virtual network | `vnet-shared` |
| | Subnet | `snet-private-endpoints` (`10.3.20.0/27`) |
| DNS | Private DNS zone | `privatelink.vaultcore.azure.net` |

---

### 3-3. MySQL Flexible Server Private Endpoint

**중분류: DB 서버 프라이빗 연결**

> MySQL Flexible Server → Networking → Private access (VNet Integration)

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 접속 방식 | Connectivity method | **Private access (VNet Integration)** |
| 네트워크 | Virtual network | `vnet-sw-spoke` |
| | Delegated subnet | `snet-mysql-delegated` (`10.4.10.0/28`) |
| 공용 접근 | Disable public access | ✅ |

> HIPAA 포인트: 모든 ePHI 전송 경로가 Azure 백본 내부로 한정됨. 인터넷 노출 없음.

---

## 3-4. TLS 최소 버전 강제 설정

**HIPAA 관련 조항**: §164.312(e)(2)(ii) 전송 중 암호화

**중분류: Storage Account TLS 최소 버전**

> Storage account → Configuration → Minimum TLS version

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| TLS 설정 | Minimum TLS version | `TLS1_2` |
| | Secure transfer required | ✅ (HTTPS Only) |

**중분류: Key Vault TLS 최소 버전**

> Key Vault → Networking → Firewall and virtual networks

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 접근 제어 | Allow public access | **Off** (Private Endpoint 전용) |
| TLS | Azure SDK 기본값 | TLS 1.2 이상 강제 (AAD 인증 포함) |

> HIPAA 포인트: §164.312(e)(2)(ii) — TLS 1.0/1.1 비활성화로 취약 암호 스위트 제거

---

## 3-5. NSG(Network Security Group) — 서브넷 레벨 접근 통제

**HIPAA 관련 조항**: §164.312(e)(1) 전송 보안 (Defense-in-depth)

> **범위 명시**: Azure Firewall Premium이 Hub-and-Spoke 트래픽을 1차 통제. NSG는 서브넷 레벨 2차 방어선으로 구성. East-West 세분화 제어 목적.

> Azure Portal → Virtual networks → `vnet-ai-spoke` → Subnets → `snet-aks` → Network security group → + Create NSG

| 소분류 | 항목 | 예시 값 |
|---|---|---|
| 기본 정보 | NSG Name | `nsg-snet-aks-spoke` |
| Inbound Rule 1 | Name | `allow-vpngw-to-aks-443` |
| | Source | VPN Gateway Subnet (`10.1.255.0/27`) |
| | Destination | AKS Subnet (`10.2.10.0/24`) |
| | Port | `443` |
| | Action | Allow |
| Inbound Deny All | Name | `deny-all-inbound` |
| | Priority | `4096` |
| | Action | Deny |

> NSG는 Azure Firewall 규칙과 연동하여 최소 권한 원칙(Least Privilege) 적용.

---

## 요약 — HIPAA 조항별 구현 매핑

| HIPAA 조항 | 내용 | 구현 서비스 |
|---|---|---|
| §164.312(e)(1) | 전송 보안 | VPN Gateway, Firewall Premium, Private Endpoint, NSG |
| §164.312(e)(2)(ii) | 전송 중 암호화 | VPN IPsec AES-256, TLS 1.2/1.3 강제 (Firewall TLS 검사, Storage/KV Minimum TLS 1.2) |
| §164.312(b) | 감사 통제 | Firewall 진단 로그 (보존 2190일), VPN 진단 로그 (보존 2190일) → Log Analytics |
