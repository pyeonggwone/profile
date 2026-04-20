# 구현 가이드: Windows 설치 프로그램 — MSI 방식 (병원 온프레미스 클라이언트 컴포넌트)

> 적용 시나리오: 병원 내부 서버에 MSI 설치 프로그램 배포 후 ISV Azure SaaS 백엔드와 연동  
> 네트워크 연동 기준: [hipaa-network.ver4.md](../Implement_Network/hipaa-network.ver4.md) — S2S VPN + NSG (Azure Firewall Premium 미사용)  
> HIPAA 기준: §164.312(e)(1) 전송 보안, §164.312(e)(2)(ii) 전송 중 암호화, §164.312(b) 감사 통제  
> 버전: v5 (2026-04-20 — MSI 방식 전환, Azure Arc 업데이트 관리 적용)

---

## 전체 구조

```
병원 온프레미스 (클라이언트 컴포넌트)
  └─ MSI 설치 프로그램 (MedicalAI-Client-Setup.msi)
      ├─ PII Masking Service (Windows Service)
      ├─ RabbitMQ Producer Agent (Windows Service)
      └─ Config Sync Service (Windows Service)
          └─[S2S VPN — IPsec AES-256]─ Azure VPN Gateway (vpngw-medicalai-hub-us)
              └─ NSG (nsg-snet-aks) — 최소 권한 접근 통제
                  └─ AKS 마이크로서비스 (10.2.10.0/24)
                      ├─ RabbitMQ Cluster
                      ├─ MySQL Flexible Server (VNet Integration)
                      └─ AI Analysis Module

Arc-enabled Server (병원 온프레미스 서버)
  └─[HTTPS 443]─ Azure Arc Service
      ├─ Azure Update Manager — OS 패치 관리
      ├─ Machine Configuration — 설정 컴플라이언스 (HIPAA 드리프트 감지)
      └─ Run Command — MSI 재배포 (원격 실행)
```

---

## 1. 설치 파일 구성

### 1-1. 설치 파일 종류

| 파일명 | 유형 | 용도 |
|---|---|---|
| `MedicalAI-Client-Setup.msi` | WiX Toolset 기반 Windows Installer (MSI) | 전체 클라이언트 컴포넌트 설치 |
| `config-template.json` | JSON 설정 템플릿 | Azure 연동 정보 (엔드포인트, 인증) 입력 |
| `install-guide.pdf` | 설치 매뉴얼 | 병원 IT 담당자용 가이드 |
| `cert-bundle.pfx` | TLS 인증서 번들 | ISV 발급 클라이언트 인증서 (mTLS 옵션) |

> MSI 선택 이유: Windows Server 표준 설치 포맷, GPO 일괄 배포 가능, 롤백/복구 MSI 표준 지원, Azure Arc Run Command 호환

### 1-2. 설치 후 생성되는 Windows 서비스

| 서비스 이름 | 실행 파일 | 역할 |
|---|---|---|
| `MedicalAI PII Masker` | `pii-masking-service.exe` | EMR/PACS 데이터 수신 후 환자 식별정보 마스킹 |
| `MedicalAI Queue Agent` | `rabbitmq-producer.exe` | 마스킹 완료 데이터를 Azure로 전송 (AMQP-over-TLS) |
| `MedicalAI Config Sync` | `config-sync.exe` | Azure Key Vault에서 설정값 동기화 (주기적 polling) |

> 각 서비스는 전용 로컬 서비스 계정으로 실행 (관리자 권한 미부여 — §164.312(a)(1) 최소 권한 원칙)

---

## 2. MSI 빌드 구성

### 2-1. 빌드 흐름

```
ISV 개발팀 (.NET 8 프로젝트 × 3)
  └─ dotnet publish --self-contained -r win-x64
      ├─ pii-masking-service.exe
      ├─ rabbitmq-producer.exe
      └─ config-sync.exe
          ↓
  WiX Toolset (.wxs 정의 파일)
      └─ ServiceInstall / ServiceControl 엘리먼트로 Windows 서비스 등록
          ↓
  wix build MedicalAI.wxs -o MedicalAI-Client-Setup.msi
          ↓
  signtool.exe — 코드 서명 (ISV 코드 서명 인증서)
          ↓
  MedicalAI-Client-Setup.msi (배포 대상)
```

### 2-2. WiX .wxs 핵심 구조 개요

MSI 내에서 Windows 서비스를 등록하는 핵심 WiX 엘리먼트:

| WiX 엘리먼트 | 역할 |
|---|---|
| `ServiceInstall` | Windows 서비스 등록 (이름, 시작 유형, 서비스 계정 지정) |
| `ServiceControl` | 설치 후 서비스 자동 시작 / 제거 시 서비스 중지 |
| `Property` / `CustomAction` | config-template.json 경로, 설치 파라미터 전달 |
| `Component` | 각 exe를 MSI 컴포넌트로 묶음 |

> 참고: Windows Installer SDK — [learn.microsoft.com/en-us/windows/win32/msi/windows-installer-guide](https://learn.microsoft.com/en-us/windows/win32/msi/windows-installer-guide)  
> .NET 8 Windows Service + Installer — [learn.microsoft.com/en-us/dotnet/core/extensions/windows-service-with-installer](https://learn.microsoft.com/en-us/dotnet/core/extensions/windows-service-with-installer)

### 2-3. 코드 서명 (보안 필수)

MSI 배포 전 ISV 코드 서명 인증서로 서명:

```powershell
# signtool.exe (Windows SDK 포함)
signtool.exe sign `
  /fd SHA256 `
  /tr http://timestamp.digicert.com `
  /td SHA256 `
  /f "ISV-CodeSign.pfx" `
  /p "<pfx-password>" `
  "MedicalAI-Client-Setup.msi"

# 서명 검증
signtool.exe verify /pa "MedicalAI-Client-Setup.msi"
```

> 병원 IT팀이 설치 전 MSI 서명 검증 가능 → 무결성 확인 (§164.312(c)(1) 무결성)

---

## 3. 설치 파일 다운로드 경로

> 초기 배포 단계에서는 오프라인 전달. 이후 Azure Marketplace SaaS offer 등록 후 Landing Page를 통한 온라인 배포로 전환 예정.

### 3-1. 초기 단계 — 오프라인 배포

| 전달 방법 | 상세 |
|---|---|
| 보안 USB / 암호화 외장 드라이브 | 오프라인 환경 병원 대상 |
| ISV 전용 SFTP 서버 | 병원 IT팀 계정 발급 후 전달 (TLS 1.2 이상 강제) |
| Azure Blob Storage (Private) | ISV가 SAS URL(단기 유효) 발급, HTTPS 전달 |

### 3-2. Marketplace 등록 후 단계 — Landing Page 연동

Azure Marketplace SaaS offer 구독 완료 시:

1. 고객이 Azure Marketplace에서 MedicalAI SaaS offer 구독
2. Landing Page (`https://portal.medicalai.com/activate`) 리디렉션
3. Entra ID SSO 인증 후 MSI 다운로드 링크 제공
4. Landing Page에서 `config-template.json` 자동 생성 (테넌트 정보 포함)

---

## 4. 설정 파일 템플릿 (config-template.json)

병원별로 개별 발급. Azure 연동 정보 포함.

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

> **중요**: `pskSecretName`은 Azure Key Vault에서 런타임 조회. PSK 평문은 로컬에 저장하지 않음.

---

## 5. MSI 설치 절차

### 5-1. 사전 조건 확인

| 항목 | 요구사항 |
|---|---|
| OS | Windows Server 2019 / 2022 (64-bit) |
| .NET Runtime | .NET 8 이상 (self-contained 빌드 시 불필요) |
| 네트워크 포트 (Outbound) | TCP 443 (HTTPS), TCP 5671 (AMQPS) Azure 방향 허용 |
| VPN 장비 | IKEv2 지원 (Cisco / Palo Alto / FortiGate) |
| 병원 공인 IP | ISV에 사전 통보 (Local Network Gateway 등록용) |
| Entra ID 계정 | Cross-Tenant Sync 또는 Guest 계정 초대 ([04-entra-cross-tenant-sync.md](./04-entra-cross-tenant-sync.md)) |
| MSI 서명 검증 | `signtool.exe verify /pa MedicalAI-Client-Setup.msi` 통과 확인 |

### 5-2. Azure 측 사전 구성 (ISV 담당)

**Step A. Local Network Gateway 등록**

> Azure Portal → Local Network Gateways → + Create

| 항목 | 값 |
|---|---|
| Name | `lng-hospital-us-001` |
| IP address | 병원 공인 IP (사전 수집) |
| Address space | 병원 내부 CIDR (`192.168.10.0/24`) |
| BGP ASN | `65001` |

**Step B. VPN Connection 생성**

> `vpngw-medicalai-hub-us` → Connections → + Add

| 항목 | 값 |
|---|---|
| Connection type | Site-to-site (IPsec) |
| Local network gateway | `lng-hospital-us-001` |
| Shared key (PSK) | Key Vault `kv-medicalai-shared` → Secret `vpn-psk-hospital-us` |
| IPsec Policy | IKEv2 + AES-256 + SHA-256 (HIPAA §164.312(e)(2)(ii)) |

> 상세 IPsec 정책 설정: [hipaa-network.ver4.md §1-3](../Implement_Network/hipaa-network.ver4.md)

**Step C. NSG Rule 추가 (병원 → AKS)**

> Azure Portal → `nsg-snet-aks` → Inbound security rules → + Add

| 항목 | 값 |
|---|---|
| Name | `allow-hospital-us-001-to-aks` |
| Source | `192.168.10.0/24` |
| Destination | `10.2.10.0/24` (AKS Subnet) |
| Destination port ranges | `443, 5671` |
| Protocol | TCP |
| Action | Allow |
| Priority | `200` |

**Step D. Entra ID 계정 구성**

- 상세 절차: [04-entra-cross-tenant-sync.md](./04-entra-cross-tenant-sync.md) 참조

### 5-3. MSI 설치 실행 (msiexec)

병원 IT 담당자가 관리자 권한 PowerShell에서 실행:

```powershell
# 1. MSI 서명 검증 (설치 전 필수)
signtool.exe verify /pa "C:\deploy\MedicalAI-Client-Setup.msi"
# → Successfully verified: ... 확인

# 2. MSI 자동 설치 (비대화형)
msiexec.exe /i "C:\deploy\MedicalAI-Client-Setup.msi" `
  /qn `
  /l*v "C:\ProgramData\MedicalAI\logs\install.log" `
  CONFIGPATH="C:\deploy\config-template.json"

# 파라미터 설명:
# /i    : 설치
# /qn   : 비대화형 (UI 없음, 자동화 배포용)
# /l*v  : 상세 설치 로그 저장
# CONFIGPATH : config-template.json 경로 전달 (CustomAction으로 처리)
```

```powershell
# 3. 설치 완료 후 서비스 상태 확인
Get-Service -Name "MedicalAI*" | Select-Object Name, Status, StartType

# 예상 출력:
# MedicalAI PII Masker     Running  Automatic
# MedicalAI Queue Agent    Running  Automatic
# MedicalAI Config Sync    Running  Automatic
```

```powershell
# 4. 설치 로그 확인
Get-Content "C:\ProgramData\MedicalAI\logs\install.log" -Tail 50
```

### 5-4. MSI 제거 / 업그레이드

```powershell
# 제거 (기존 ProductCode 조회 후)
$productCode = (Get-WmiObject -Class Win32_Product | Where-Object { $_.Name -like "MedicalAI*" }).IdentifyingNumber
msiexec.exe /x $productCode /qn /l*v "C:\ProgramData\MedicalAI\logs\uninstall.log"

# 업그레이드 (MSI Major Upgrade — 기존 버전 자동 제거 후 재설치)
msiexec.exe /i "C:\deploy\MedicalAI-Client-Setup-v2.msi" /qn /l*v "C:\ProgramData\MedicalAI\logs\upgrade.log"
```

---

## 6. Azure Arc 기반 업데이트 관리

### 6-1. Azure Arc 적합성 검증

> 대상: 병원 온프레미스 Windows Server 2019 / 2022

| 검증 항목 | 결과 | 비고 |
|---|---|---|
| Arc-enabled Server 지원 OS | ✅ 적합 | Windows Server 2019/2022 공식 지원 |
| 통신 포트 | ✅ 적합 | TCP 443 Outbound — 기존 VPN 구성에서 이미 허용 |
| Arc endpoint FQDN | ✅ 적합 | `management.azure.com`, `*.guestconfiguration.azure.com` — 443으로 VPN 경유 도달 가능 |
| OS 패치 관리 (Azure Update Manager) | ✅ 적합 | Arc-enabled Server에서 Azure Update Manager 완전 지원 |
| MSI 재배포 (Run Command) | ✅ 적합 | Arc Run Command로 `msiexec.exe` 원격 실행 가능 |
| 설정 컴플라이언스 (Machine Configuration) | ✅ 적합 | HIPAA 드리프트 감지 (서비스 실행 상태, TLS 설정 등) |
| Intune 비사용 환경 | ✅ 적합 | Arc는 Intune 없이 독립 작동 |

> **결론**: Azure Arc는 이 프로젝트에 적합하다. 병원 온프레미스 Windows Server를 Azure Arc에 등록하면 OS 패치, MSI 재배포, 설정 컴플라이언스를 단일 Azure 포털에서 관리 가능.
>
> ⚠️ **주의**: Arc Connected Machine Agent 설치 시 병원 측 방화벽에서 Arc FQDN (`*.arc.azure.com`, `management.azure.com` 등) 에 대한 Outbound 443 허용 필요. 상세 엔드포인트 목록: [learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements](https://learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements)

### 6-2. Arc-enabled Server 등록

> Azure Portal → Azure Arc → Servers → + Add → Add a single server

| 항목 | 값 |
|---|---|
| Subscription | ISV Azure 구독 |
| Resource group | `rg-medicalai-arc` |
| Region | East US |
| OS | Windows |
| Connectivity method | Public endpoint (VPN 경유 HTTPS 443) |

병원 서버에서 Arc 에이전트 설치 스크립트 실행 (Azure Portal에서 자동 생성):

```powershell
# Azure Portal에서 생성된 스크립트 실행 (관리자 권한)
# 스크립트 내용: Connected Machine Agent 다운로드 + 등록
.\OnboardingScript.ps1
```

### 6-3. Azure Update Manager — OS 패치 관리

> Azure Portal → Azure Update Manager → Machines → 병원 Arc 서버 선택

| 기능 | 설정 |
|---|---|
| 패치 일정 | 주 1회 (업무 외 시간) — 유지 관리 기간 설정 |
| 패치 분류 | Critical, Security 자동 적용 |
| 재부팅 정책 | 패치 후 자동 재부팅 (서비스 자동 시작 확인 필요) |
| 패치 결과 로그 | Azure Log Analytics → `law-medicalai-shared` 전송 |

### 6-4. Arc Run Command — MSI 원격 재배포

신규 버전 MSI를 병원 서버에 원격 배포:

> Azure Portal → Azure Arc → Servers → 대상 서버 → Run command → RunPowerShellScript

```powershell
# Arc Run Command에서 실행할 스크립트 (Azure Portal에서 입력)
# 전제: MSI 파일이 Azure Blob Storage SAS URL로 제공되어 있음

$msiBlobUrl = "https://stmedicalaiarchive.blob.core.windows.net/deploy/MedicalAI-Client-Setup-v2.msi?<SAS_TOKEN>"
$msiPath = "C:\deploy\MedicalAI-Client-Setup-v2.msi"

# MSI 다운로드
Invoke-WebRequest -Uri $msiBlobUrl -OutFile $msiPath

# MSI 서명 검증
$sigResult = & signtool.exe verify /pa $msiPath 2>&1
if ($LASTEXITCODE -ne 0) { throw "MSI 서명 검증 실패: $sigResult" }

# MSI 설치
Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /qn /l*v C:\ProgramData\MedicalAI\logs\upgrade.log CONFIGPATH=C:\ProgramData\MedicalAI\config-template.json" -Wait -NoNewWindow

# 서비스 상태 확인
Get-Service -Name "MedicalAI*" | Select-Object Name, Status
```

### 6-5. Arc Machine Configuration — HIPAA 컴플라이언스 드리프트 감지

| 감지 항목 | 정책 기준 | HIPAA 조항 |
|---|---|---|
| Windows 서비스 3종 실행 상태 | Running / Automatic 필수 | §164.312(a)(1) |
| TLS 1.0 / 1.1 비활성화 | Registry 기반 정책 | §164.312(e)(2)(ii) |
| 로그 보존 디렉토리 존재 여부 | `C:\ProgramData\MedicalAI\logs` | §164.312(b) |
| 서비스 계정 권한 | 로컬 서비스 계정, 관리자 그룹 미포함 | §164.312(a)(1) |

> 드리프트 감지 결과는 Azure Policy 컴플라이언스 대시보드에서 확인 가능

---

## 7. Azure 연동 확인

### 7-1. VPN 터널 연결 확인

> Azure Portal → VPN Gateway `vpngw-medicalai-hub-us` → Connections

| 확인 항목 | 정상 상태 |
|---|---|
| Connection status | **Connected** |
| IKE protocol | IKEv2 |
| Ingress / Egress bytes | 0 이상 (트래픽 발생 시) |

```powershell
# 병원 측에서 Azure 내부 IP로 연결 테스트
Test-NetConnection -ComputerName "10.2.10.10" -Port 443
# TcpTestSucceeded: True 확인
```

### 7-2. RabbitMQ 전송 확인

```powershell
Get-Content "C:\ProgramData\MedicalAI\logs\queue-agent.log" -Tail 30 | Select-String "Published|Error"
# [INFO] Published message to amqps://rabbitmq.internal.medicalai.com:5671/ecg.queue (msgId: abc123)
```

### 7-3. Key Vault 접근 확인

```powershell
Get-Content "C:\ProgramData\MedicalAI\logs\config-sync.log" -Tail 10 | Select-String "Synced|Error"
# [INFO] Synced 3 secrets from kv-medicalai-shared
```

---

## 8. 보안 및 HIPAA 요구사항 체크리스트

| 항목 | 구현 방법 | HIPAA 조항 |
|---|---|---|
| 전송 중 암호화 | S2S VPN IPsec AES-256 + TLS 1.2 이상 | §164.312(e)(2)(ii) |
| PSK / 시크릿 로컬 미저장 | Azure Key Vault 런타임 조회 | §164.312(a)(2)(iv) |
| 설치 로그 보존 | 로컬 90일, Azure Log Analytics → Storage Archive 2190일 | §164.312(b) |
| 최소 권한 서비스 계정 | Windows 서비스 전용 로컬 계정, 관리자 권한 미부여 | §164.312(a)(1) |
| 네트워크 접근 제한 | NSG inbound 최소 권한 규칙 (deny-all 포함) | §164.312(e)(1) |
| 클라이언트 인증 | Entra ID Managed Identity 또는 mTLS 인증서 | §164.312(d) |
| MSI 무결성 검증 | 코드 서명 (SHA-256) + 설치 전 signtool verify | §164.312(c)(1) |
| OS 패치 관리 | Azure Arc + Azure Update Manager | §164.312(a)(2)(ii) |
| 설정 컴플라이언스 | Azure Arc Machine Configuration — 드리프트 감지 | §164.306(a)(1) |

---

## 9. 참고 링크

| 목적 | 링크 |
|---|---|
| Windows Installer 개요 | [learn.microsoft.com/en-us/windows/win32/msi/about-windows-installer](https://learn.microsoft.com/en-us/windows/win32/msi/about-windows-installer) |
| Windows Installer 가이드 (ServiceInstall, CustomAction) | [learn.microsoft.com/en-us/windows/win32/msi/windows-installer-guide](https://learn.microsoft.com/en-us/windows/win32/msi/windows-installer-guide) |
| Windows Installer Best Practices | [learn.microsoft.com/en-us/windows/win32/msi/windows-installer-best-practices](https://learn.microsoft.com/en-us/windows/win32/msi/windows-installer-best-practices) |
| msiexec 커맨드라인 레퍼런스 | [learn.microsoft.com/en-us/windows-server/administration/windows-commands/msiexec](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/msiexec) |
| .NET 8 Windows Service + MSI Installer | [learn.microsoft.com/en-us/dotnet/core/extensions/windows-service-with-installer](https://learn.microsoft.com/en-us/dotnet/core/extensions/windows-service-with-installer) |
| 패키징 방식 결정 가이드 (MSI / MSIX / 외부 위치) | [learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/choose-distribution-path) |
| Azure Arc — 서버 네트워크 요구사항 | [learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements](https://learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements) |
| Azure Update Manager 개요 | [learn.microsoft.com/en-us/azure/update-manager/overview](https://learn.microsoft.com/en-us/azure/update-manager/overview) |
| Arc Machine Configuration 개요 | [learn.microsoft.com/en-us/azure/governance/machine-configuration/overview](https://learn.microsoft.com/en-us/azure/governance/machine-configuration/overview) |
| Arc Run Command | [learn.microsoft.com/en-us/azure/azure-arc/servers/run-command](https://learn.microsoft.com/en-us/azure/azure-arc/servers/run-command) |

---

## 10. 문제 해결 (Troubleshooting)

| 증상 | 확인 사항 | 조치 |
|---|---|---|
| VPN Connection 상태 `Not connected` | 병원 VPN 장비 IKEv2 설정, PSK 일치 여부 | [hipaa-network.ver4.md §1-3](../Implement_Network/hipaa-network.ver4.md) IPsec Policy 재확인 |
| RabbitMQ 전송 실패 (TCP 5671 차단) | NSG Rule `allow-hospital-us-001-to-aks`에 Port 5671 허용 여부 | `nsg-snet-aks` Inbound Rule 확인 |
| Key Vault 접근 오류 (403) | Managed Identity에 Key Vault Secrets User 역할 부여 여부 | `kv-medicalai-shared` → Access control (IAM) 확인 |
| MSI 설치 실패 (서명 오류) | `signtool.exe verify /pa` 결과 확인 | ISV에 서명된 최신 MSI 재요청 |
| 서비스 시작 실패 | config-template.json 형식 오류, .NET 버전 미설치 | `C:\ProgramData\MedicalAI\logs\install.log` 확인 |
| Arc 에이전트 등록 실패 | TCP 443 Outbound — Arc FQDN 도달 가능 여부 | 병원 방화벽에서 Arc 엔드포인트 FQDN 허용 확인 |
| Arc Run Command 타임아웃 | MSI 다운로드 시간 초과 (대용량) | Blob SAS URL 유효 기간 확인, 네트워크 대역폭 확인 |
