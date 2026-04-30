# 구현 가이드: Windows 설치 프로그램 (병원 온프레미스 클라이언트 컴포넌트)

> 적용 시나리오: 병원 내부 서버에 Windows 설치 프로그램 배포 후 ISV Azure SaaS 백엔드와 연동  
> 네트워크 연동 기준: [hipaa-network.ver4.md](../Implement_Network/hipaa-network.ver4.md) — S2S VPN + Private Endpoint  
> HIPAA 기준: §164.312(e)(1) 전송 보안, §164.312(e)(2)(ii) 전송 중 암호화

---

## 전체 구조

```
병원 온프레미스 (클라이언트 컴포넌트)
  └─ Windows 설치 프로그램 (MedicalAI-Client-Setup.exe)
      ├─ PII Masking Service (Windows Service)
      ├─ RabbitMQ Producer Agent
      └─ Config Manager (Azure 연동 설정 도구)
          └─[S2S VPN — IPsec AES-256]─ Azure VPN Gateway (vpngw-medicalai-hub-us)
              └─ Azure Firewall Premium (afw-medicalai-hub-us)
                  └─ AKS 마이크로서비스 (10.2.10.0/24)
                      ├─ RabbitMQ Cluster
                      ├─ CosmosDB (MongoDB API)
                      └─ AI Analysis Module
```

---

## 1. 설치 파일 구성

### 1-1. 설치 파일 종류

| 파일명 | 유형 | 용도 |
|---|---|---|
| `MedicalAI-Client-Setup.exe` | NSIS / WiX Toolset 기반 Windows Installer | 전체 클라이언트 컴포넌트 설치 |
| `config-template.json` | JSON 설정 템플릿 | Azure 연동 정보 (엔드포인트, 인증) 입력 |
| `install-guide.pdf` | 설치 매뉴얼 | 병원 IT 담당자용 가이드 |
| `cert-bundle.pfx` | TLS 인증서 번들 | ISV 발급 클라이언트 인증서 (mTLS 옵션) |

### 1-2. 설치 후 생성되는 Windows 서비스

| 서비스 이름 | 실행 파일 | 역할 |
|---|---|---|
| `MedicalAI PII Masker` | `pii-masking-service.exe` | EMR/PACS 데이터 수신 후 환자 식별정보 마스킹 |
| `MedicalAI Queue Agent` | `rabbitmq-producer.exe` | 마스킹 완료 데이터를 Azure로 전송 (AMQP-over-TLS) |
| `MedicalAI Config Sync` | `config-sync.exe` | Azure Key Vault에서 설정값 동기화 (주기적 polling) |

---

## 2. 설치 파일 다운로드 경로

> 초기 배포 단계에서는 별도 배포(오프라인 전달). 이후 Azure Marketplace SaaS offer 등록 후 Landing Page를 통한 온라인 배포로 전환 예정.

### 2-1. 초기 단계 — 오프라인 배포

ISV 담당자가 병원 IT팀에 직접 전달하는 방식:

| 전달 방법 | 상세 |
|---|---|
| 보안 USB / 암호화 외장 드라이브 | 오프라인 환경 병원 대상 |
| ISV 전용 SFTP 서버 | 병원 IT팀 계정 발급 후 전달 (TLS 1.2 이상 강제) |
| 암호화 이메일 첨부 | 소용량 설정 파일 한정 (exe 전달은 제외 권장) |

### 2-2. Marketplace 등록 후 단계 — Landing Page 연동

Azure Marketplace SaaS offer 구독 완료 시:

1. 고객이 Azure Marketplace에서 MedicalAI SaaS offer 구독
2. Landing Page (`https://portal.medicalai.com/activate`) 리디렉션
3. Entra ID SSO 인증 후 설치 파일 다운로드 링크 제공
4. Landing Page에서 `config-template.json` 자동 생성 (테넌트 정보 포함)

> Landing Page 구현 기준: [03-service-calls.md](./03-service-calls.md) Load Balancer 섹션 참조

---

## 3. 설정 파일 템플릿 (config-template.json)

병원별로 개별 발급되며, Azure 연동 정보를 포함한다.

```json
{
  "tenant": {
    "hospitalId": "hospital-us-001",
    "tenantId": "<HOSPITAL_ENTRA_TENANT_ID>",
    "region": "eastus"
  },
  "network": {
    "vpnMode": "s2s",
    "azureVpnGatewayIp": "<pip-vpngw-medicalai-hub-us 공인 IP>",
    "localNetworkCidr": "192.168.10.0/24",
    "ikeVersion": "IKEv2",
    "encryption": "AES256",
    "pskSecretName": "vpn-psk-hospital-us"
  },
  "endpoints": {
    "rabbitmqAmqp": "amqps://rabbitmq.internal.medicalai.com:5671",
    "aiApiBase": "https://api.internal.medicalai.com",
    "keyVaultUri": "https://kv-medicalai-shared.vault.azure.net/"
  },
  "auth": {
    "method": "ManagedIdentity",
    "clientId": "<USER_ASSIGNED_MANAGED_IDENTITY_CLIENT_ID>"
  },
  "tls": {
    "minVersion": "1.2",
    "serverCertThumbprint": "<ISV CA 인증서 지문>"
  },
  "logging": {
    "logLevel": "Info",
    "localLogPath": "C:\\ProgramData\\MedicalAI\\logs",
    "retentionDays": 90
  }
}
```

> **중요**: `pskSecretName`은 Azure Key Vault에서 조회. PSK 평문은 로컬에 저장하지 않음.

---

## 4. 설치 절차

### 4-1. 사전 조건 확인

병원 IT팀이 설치 전 준비해야 할 항목:

| 항목 | 요구사항 |
|---|---|
| OS | Windows Server 2019 / 2022 (64-bit) |
| .NET Runtime | .NET 8 이상 |
| 네트워크 포트 | Outbound TCP 443 (HTTPS), TCP 5671 (AMQPS) Azure 방향 허용 |
| VPN 장비 | IKEv2 지원 (Cisco / Palo Alto / FortiGate) |
| 병원 공인 IP | ISV에 사전 통보 (Local Network Gateway 등록용) |
| Entra ID 계정 | ISV가 병원 테넌트에 Guest 계정 초대 또는 Cross-Tenant Sync 설정 필요 |

### 4-2. Azure 측 사전 구성 (ISV 담당)

설치 전 ISV가 Azure에서 완료해야 할 작업:

**Step A. Local Network Gateway 등록**

> Azure Portal → Local Network Gateways → + Create

| 항목 | 값 |
|---|---|
| Name | `lng-hospital-us-001` |
| IP address | 병원 공인 IP (사전 수집) |
| Address space | 병원 내부 CIDR (예: `192.168.10.0/24`) |
| BGP ASN | `65001` |

**Step B. VPN Connection 생성**

> `vpngw-medicalai-hub-us` → Connections → + Add

| 항목 | 값 |
|---|---|
| Connection type | Site-to-site (IPsec) |
| Local network gateway | `lng-hospital-us-001` |
| Shared key (PSK) | Key Vault `kv-medicalai-shared` → Secret `vpn-psk-hospital-us` 에 저장된 값 |
| IPsec Policy | IKEv2 + AES-256 + SHA-256 (HIPAA 기준) |

> 상세 설정은 [hipaa-network.ver4.md §1-3](../Implement_Network/hipaa-network.ver4.md) 참조

**Step C. Firewall Network Rule 추가**

> `afwpol-medicalai-hipaa` → Rule Collections → `netrc-hospital-us-to-ai` 에 Rule 추가

| 항목 | 값 |
|---|---|
| Name | `allow-hospital-us-001-to-aks` |
| Source | `192.168.10.0/24` |
| Destination | `10.2.10.0/24` (AKS Subnet) |
| Protocol / Port | TCP / 443, 5671 |
| Action | Allow |

**Step D. Entra ID 계정 구성**

- 병원 테넌트에 Guest 계정 초대 또는 Cross-Tenant Sync 설정
- 상세 절차: [04-entra-cross-tenant-sync.md](./04-entra-cross-tenant-sync.md) 참조

---

### 4-3. 클라이언트 설치 실행

병원 IT 담당자가 실행:

```powershell
# 1. 설치 파일 실행 (관리자 권한)
.\MedicalAI-Client-Setup.exe /S /CONFIG="C:\deploy\config-template.json"

# 2. 설치 완료 후 서비스 상태 확인
Get-Service -Name "MedicalAI*" | Select-Object Name, Status, StartType

# 예상 출력:
# MedicalAI PII Masker     Running  Automatic
# MedicalAI Queue Agent    Running  Automatic
# MedicalAI Config Sync    Running  Automatic
```

```powershell
# 3. 설치 로그 확인
Get-Content "C:\ProgramData\MedicalAI\logs\install.log" -Tail 50
```

---

## 5. Azure 연동 확인

### 5-1. VPN 터널 연결 확인

> Azure Portal → VPN Gateway `vpngw-medicalai-hub-us` → Connections → `conn-hospital-us-001`

| 확인 항목 | 정상 상태 |
|---|---|
| Connection status | **Connected** |
| Ingress / Egress bytes | 0 이상 (트래픽 발생 시) |
| IKE protocol | IKEv2 |

```powershell
# 병원 측에서 Azure 내부 IP로 연결 테스트
Test-NetConnection -ComputerName "10.2.10.10" -Port 443
# TcpTestSucceeded: True 확인
```

### 5-2. RabbitMQ 전송 확인

```powershell
# Queue Agent 로그에서 메시지 전송 성공 여부 확인
Get-Content "C:\ProgramData\MedicalAI\logs\queue-agent.log" -Tail 30 | Select-String "Published|Error"
```

정상 로그 예:
```
[INFO] 2026-04-20T10:00:00Z Published message to amqps://rabbitmq.internal.medicalai.com:5671/ecg.queue (msgId: abc123)
```

### 5-3. Key Vault 접근 확인

> Config Sync 서비스가 Azure Key Vault에서 설정값을 가져오는지 확인:

```powershell
Get-Content "C:\ProgramData\MedicalAI\logs\config-sync.log" -Tail 10 | Select-String "Synced|Error"
# [INFO] Synced 3 secrets from kv-medicalai-shared
```

---

## 6. 보안 및 HIPAA 요구사항 체크리스트

| 항목 | 구현 방법 | HIPAA 조항 |
|---|---|---|
| 전송 중 암호화 | S2S VPN IPsec AES-256 + TLS 1.2 이상 | §164.312(e)(2)(ii) |
| PSK/시크릿 로컬 미저장 | Azure Key Vault에서 런타임 조회 | §164.312(a)(2)(iv) |
| 설치 로그 보존 | 로컬 90일, Azure Log Analytics 전송 후 2190일 | §164.312(b) |
| 최소 권한 서비스 계정 | Windows 서비스 전용 로컬 계정, 관리자 권한 미부여 | §164.312(a)(1) |
| 네트워크 접근 제한 | Azure Firewall Network Rule + NSG (최소 권한) | §164.312(e)(1) |
| 클라이언트 인증 | Entra ID Managed Identity 또는 mTLS 인증서 | §164.312(d) |

---

## 7. 문제 해결 (Troubleshooting)

| 증상 | 확인 사항 | 조치 |
|---|---|---|
| VPN Connection 상태 `Not connected` | 병원 VPN 장비 IKEv2 설정, PSK 일치 여부 | [hipaa-network.ver4.md §1-3](../Implement_Network/hipaa-network.ver4.md) IPsec Policy 재확인 |
| RabbitMQ 전송 실패 (TCP 5671 차단) | Azure Firewall Rule에 Port 5671 허용 여부 | Firewall Rule `netrc-hospital-us-to-ai` 에 Port 5671 추가 |
| Key Vault 접근 오류 (403) | Managed Identity에 Key Vault Secrets User 역할 부여 여부 | `kv-medicalai-shared` → Access control (IAM) → Role assignment 확인 |
| 서비스 시작 실패 | config-template.json 형식 오류, .NET 버전 미설치 | 설치 로그 `C:\ProgramData\MedicalAI\logs\install.log` 확인 |
