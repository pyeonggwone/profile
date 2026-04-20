# 구현 가이드: 병원 온프레미스 클라이언트 — MSI 범용 배포 방식

> 적용 시나리오: Windows Server 2012 R2 이상 병원 서버에 MSI 설치 프로그램을 배포하고 ISV Azure SaaS 백엔드와 연동  
> 네트워크 연동 기준: [hipaa-network.ver4.md](../Implement_Network/hipaa-network.ver4.md) — S2S VPN + NSG  
> HIPAA 기준: §164.312(e)(1) 전송 보안, §164.312(e)(2)(ii) 전송 중 암호화, §164.312(b) 감사 통제  
> 버전: v1 (2026-04-20 — MSI 범용 배포 기준 신규 작성)

---

## 배포 방식 선택 기준

| 항목 | 이 가이드 (MSI) | [05 가이드 (k3s)](./05-windows-installer-client.ver6.md) |
|---|---|---|
| **지원 OS** | Windows Server 2012 R2 이상 (범용) | Windows Server 2019 / 2022 전용 |
| **런타임** | Windows SCM (Service Control Manager) | k3s (containerd) |
| **배포 단위** | MSI 패키지 | 컨테이너 이미지 |
| **원격 업데이트** | Arc Run Command (msiexec) | Arc GitOps (Flux) |
| **병원 IT 요구 역량** | 낮음 (표준 Windows 운영) | 높음 (K8s 기본 이해 필요) |

> **선택 기준**: OS 버전이 불명확하거나 혼재하는 병원, Windows 전용 운영 환경, IT 역량이 낮은 병원에 이 가이드를 적용. OS 버전이 2019/2022이고 컨테이너 운영 역량이 있는 병원은 [05 가이드 (k3s)](./05-windows-installer-client.ver6.md) 검토.

---

## 전체 구조

```
병원 온프레미스 (Windows Server)
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
      ├─ Machine Configuration — HIPAA 드리프트 감지
      └─ Run Command — MSI 재배포 (원격 실행)
```

---

## 1. 지원 OS 매트릭스

| OS | MSI 설치 | Arc 지원 | HIPAA 패치 관리 | 비고 |
|---|---|---|---|---|
| Windows Server 2022 | ✅ | ✅ | ✅ | 권장 |
| Windows Server 2019 | ✅ | ✅ | ✅ | 지원 |
| Windows Server 2016 | ✅ | ✅ | ✅ | 지원 |
| Windows Server 2012 R2 | ✅ | ✅ Arc ESU | ⚠️ Arc ESU 2026-10 종료 | 계약 전 OS 업그레이드 권고 |
| Windows Server 2012 | ✅ | ✅ Arc ESU | ⚠️ Arc ESU 2026-10 종료 | 계약 전 OS 업그레이드 권고 |
| Windows Server 2008 R2 | ✅ | ⚠️ Arc ESU 종료 | ❌ 패치 없음 | **HIPAA 준수 불가 — 지원 제외** |
| Windows Server 2008 이하 | ✅ | ❌ | ❌ | **지원 제외** |

> **Arc ESU (Extended Security Updates)**: Windows Server 2012/2012 R2는 Azure Arc를 통해 ESU 무료 제공. 2026년 10월 종료 예정. 계약 시 병원에 OS 업그레이드 일정 요청 권고.  
> **2008 R2 이하**: 현재 시점(2026-04) 기준 패치가 없는 OS에 PHI 처리 에이전트 배포는 §164.312(a)(2)(ii) 위반 소지 → 지원 제외.

---

## 2. 설치 파일 구성

### 2-1. 설치 파일 종류

| 파일명 | 유형 | 용도 |
|---|---|---|
| `MedicalAI-Client-Setup.msi` | WiX Toolset 기반 Windows Installer | 전체 클라이언트 컴포넌트 설치 |
| `config-template.json` | JSON 설정 템플릿 | Azure 연동 정보 (엔드포인트, 인증) |
| `install-guide.pdf` | 설치 매뉴얼 | 병원 IT 담당자용 가이드 |
| `cert-bundle.pfx` | TLS 인증서 번들 | ISV 발급 클라이언트 인증서 (mTLS 옵션) |

### 2-2. 설치 후 생성되는 Windows 서비스

| 서비스 이름 | 실행 파일 | 역할 |
|---|---|---|
| `MedicalAI PII Masker` | `pii-masking-service.exe` | EMR/PACS 데이터 수신 후 환자 식별정보 마스킹 |
| `MedicalAI Queue Agent` | `rabbitmq-producer.exe` | 마스킹 완료 데이터를 Azure로 전송 (AMQP-over-TLS) |
| `MedicalAI Config Sync` | `config-sync.exe` | Azure Key Vault에서 설정값 동기화 (주기적 polling) |

> 각 서비스는 전용 로컬 서비스 계정으로 실행 (관리자 권한 미부여 — §164.312(a)(1) 최소 권한)

---

## 3. ISV 측 Azure 사전 구성

### 3-1. VPN 구성

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
| IPsec Policy | IKEv2 + AES-256 + SHA-256 (§164.312(e)(2)(ii)) |

> 상세 IPsec 정책: [hipaa-network.ver4.md §1-3](../Implement_Network/hipaa-network.ver4.md)

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

### 3-2. MSI 패키지 빌드 및 배포 파일 준비

```
ISV 개발팀 (.NET 8 프로젝트 × 3)
  └─ dotnet publish --self-contained -r win-x64
      ├─ pii-masking-service.exe
      ├─ rabbitmq-producer.exe
      └─ config-sync.exe
          ↓
  WiX Toolset (.wxs — ServiceInstall / ServiceControl)
          ↓
  wix build MedicalAI.wxs -o MedicalAI-Client-Setup.msi
          ↓
  signtool.exe — 코드 서명 (ISV 코드 서명 인증서)
          ↓
  MedicalAI-Client-Setup.msi → Azure Blob Storage (배포용)
```

> self-contained 빌드(`--self-contained`)이므로 병원 서버에 .NET Runtime 별도 설치 불필요. OS 버전에 무관하게 동작.

**코드 서명:**

```powershell
signtool.exe sign `
  /fd SHA256 `
  /tr http://timestamp.digicert.com `
  /td SHA256 `
  /f "ISV-CodeSign.pfx" `
  /p "<pfx-password>" `
  "MedicalAI-Client-Setup.msi"
```

### 3-3. 배포 파일 호스팅

| 전달 방법 | 대상 | 비고 |
|---|---|---|
| Azure Blob Storage (Private) + SAS URL | 초기 배포 | SAS URL 유효 기간 단기 설정 (24시간 이내) |
| ISV 전용 SFTP 서버 | 오프라인/폐쇄망 병원 | TLS 1.2 이상 강제 |
| 보안 USB / 암호화 외장 드라이브 | 인터넷 완전 차단 병원 | |
| Azure Marketplace Landing Page | Marketplace 등록 후 | 테넌트 정보 포함 config 자동 생성 |

---

## 4. 병원 서버 측 설치 절차

### 4-1. 사전 조건 확인

| 항목 | 요구사항 |
|---|---|
| OS | Windows Server 2012 R2 이상 (§164.312(a)(2)(ii) 준수 가능 버전) |
| 네트워크 포트 (Outbound) | TCP 443 (HTTPS), TCP 5671 (AMQPS) Azure 방향 허용 |
| VPN 장비 | IKEv2 지원 (Cisco / Palo Alto / FortiGate) |
| 병원 공인 IP | ISV에 사전 통보 |
| MSI 서명 검증 | `signtool.exe verify /pa MedicalAI-Client-Setup.msi` 통과 확인 |

### 4-2. S2S VPN 연결 구성 (병원 네트워크 담당)

병원 VPN 장비에서 IKEv2 터널 구성:

| 항목 | 값 |
|---|---|
| Remote IP | `pip-vpngw-medicalai-hub-us` (ISV 제공) |
| PSK | ISV 제공 (별도 보안 채널로 전달) |
| IKE Version | IKEv2 |
| Encryption | AES-256 / SHA-256 |
| Local CIDR | `192.168.10.0/24` |
| Remote CIDR | `10.2.10.0/24` |

> PSK는 Azure Key Vault에 저장되며 ISV가 조회 후 병원에 전달. 병원 로컬 파일에는 저장하지 않음.

### 4-3. Azure Arc 에이전트 등록 (병원 서버)

> Azure Portal → Azure Arc → Servers → + Add → Add a single server  
> 스크립트 자동 생성 후 병원 서버에서 실행:

```powershell
# 관리자 권한 PowerShell에서 실행
# Azure Portal에서 생성된 스크립트 실행 (Connected Machine Agent 다운로드 + 등록)
.\OnboardingScript.ps1
```

등록 확인:

```powershell
azcmagent show
# Status: Connected
```

### 4-4. MSI 설치 실행

```powershell
# 1. MSI 서명 검증 (설치 전 필수)
signtool.exe verify /pa "C:\deploy\MedicalAI-Client-Setup.msi"
# → Successfully verified: ... 확인

# 2. config-template.json 배치 (ISV 제공 파일)
# C:\deploy\config-template.json

# 3. MSI 자동 설치 (비대화형)
msiexec.exe /i "C:\deploy\MedicalAI-Client-Setup.msi" `
  /qn `
  /l*v "C:\ProgramData\MedicalAI\logs\install.log" `
  CONFIGPATH="C:\deploy\config-template.json"

# 4. 설치 완료 후 서비스 상태 확인
Get-Service -Name "MedicalAI*" | Select-Object Name, Status, StartType
# MedicalAI PII Masker     Running  Automatic
# MedicalAI Queue Agent    Running  Automatic
# MedicalAI Config Sync    Running  Automatic
```

### 4-5. 설정 파일 (config-template.json)

병원별 개별 발급. ISV가 Landing Page 또는 SFTP로 제공:

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

> `pskSecretName`은 Azure Key Vault에서 런타임 조회. PSK 평문은 로컬에 저장하지 않음. (§164.312(a)(2)(iv))

---

## 5. Azure 연동 확인

### 5-1. VPN 터널 확인

> Azure Portal → VPN Gateway `vpngw-medicalai-hub-us` → Connections  
> Connection status: **Connected** 확인

```powershell
# 병원 측에서 Azure 내부 IP로 연결 테스트
Test-NetConnection -ComputerName "10.2.10.10" -Port 443
# TcpTestSucceeded: True 확인
```

### 5-2. RabbitMQ 전송 확인

```powershell
Get-Content "C:\ProgramData\MedicalAI\logs\queue-agent.log" -Tail 30 | Select-String "Published|Error"
# [INFO] Published message to amqps://rabbitmq.internal.medicalai.com:5671/ecg.queue
```

### 5-3. Key Vault 접근 확인

```powershell
Get-Content "C:\ProgramData\MedicalAI\logs\config-sync.log" -Tail 10 | Select-String "Synced|Error"
# [INFO] Synced 3 secrets from kv-medicalai-shared
```

---

## 6. 원격 업데이트 — Arc Run Command

### 6-1. MSI 업그레이드 원격 배포

> Azure Portal → Azure Arc → Servers → 대상 서버 → Run command → RunPowerShellScript

```powershell
# Arc Run Command에서 실행할 스크립트
$msiBlobUrl = "https://stmedicalaiarchive.blob.core.windows.net/deploy/MedicalAI-Client-Setup-v2.msi?<SAS_TOKEN>"
$msiPath = "C:\deploy\MedicalAI-Client-Setup-v2.msi"

# MSI 다운로드
Invoke-WebRequest -Uri $msiBlobUrl -OutFile $msiPath

# 서명 검증
$sigResult = & signtool.exe verify /pa $msiPath 2>&1
if ($LASTEXITCODE -ne 0) { throw "MSI 서명 검증 실패: $sigResult" }

# MSI 업그레이드 설치
Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /qn /l*v C:\ProgramData\MedicalAI\logs\upgrade.log CONFIGPATH=C:\ProgramData\MedicalAI\config-template.json" -Wait -NoNewWindow

# 서비스 상태 확인
Get-Service -Name "MedicalAI*" | Select-Object Name, Status
```

### 6-2. OS 패치 관리 (Azure Update Manager)

> Azure Portal → Azure Update Manager → Machines → 병원 Arc 서버 선택

| 기능 | 설정 |
|---|---|
| 패치 일정 | 주 1회 (업무 외 시간) |
| 패치 분류 | Critical, Security 자동 적용 |
| 재부팅 정책 | 패치 후 자동 재부팅 (서비스 자동 시작 확인) |
| 패치 결과 로그 | Azure Log Analytics → `law-medicalai-shared` 전송 |

### 6-3. Arc Machine Configuration — HIPAA 드리프트 감지

| 감지 항목 | 정책 기준 | HIPAA 조항 |
|---|---|---|
| Windows 서비스 3종 실행 상태 | Running / Automatic 필수 | §164.312(a)(1) |
| TLS 1.0 / 1.1 비활성화 | Registry 기반 정책 | §164.312(e)(2)(ii) |
| 로그 보존 디렉토리 존재 여부 | `C:\ProgramData\MedicalAI\logs` | §164.312(b) |
| 서비스 계정 권한 | 로컬 서비스 계정, 관리자 그룹 미포함 | §164.312(a)(1) |

---

## 7. HIPAA 요구사항 체크리스트

| 항목 | 구현 방법 | HIPAA 조항 |
|---|---|---|
| 전송 중 암호화 | S2S VPN IPsec AES-256 + TLS 1.2 이상 | §164.312(e)(2)(ii) |
| PSK / 시크릿 로컬 미저장 | Azure Key Vault 런타임 조회 | §164.312(a)(2)(iv) |
| 설치 로그 보존 | 로컬 90일, Azure Log Analytics → Storage Archive 2190일 | §164.312(b) |
| 최소 권한 서비스 계정 | Windows 서비스 전용 로컬 계정, 관리자 권한 미부여 | §164.312(a)(1) |
| 네트워크 접근 제한 | NSG inbound 최소 권한 규칙 | §164.312(e)(1) |
| 클라이언트 인증 | Entra ID Managed Identity 또는 mTLS 인증서 | §164.312(d) |
| MSI 무결성 검증 | 코드 서명 (SHA-256) + 설치 전 signtool verify | §164.312(c)(1) |
| OS 패치 관리 | Azure Arc + Azure Update Manager | §164.312(a)(2)(ii) |
| 설정 컴플라이언스 | Arc Machine Configuration — 드리프트 감지 | §164.306(a)(1) |
| 구버전 OS 대응 | 2012 R2 이상만 지원, 2008 R2 이하 계약 제외 | §164.312(a)(2)(ii) |

---

## 8. 문제 해결

| 증상 | 확인 사항 | 조치 |
|---|---|---|
| VPN Connection 상태 `Not connected` | 병원 VPN 장비 IKEv2 설정, PSK 일치 여부 | [hipaa-network.ver4.md §1-3](../Implement_Network/hipaa-network.ver4.md) IPsec Policy 재확인 |
| RabbitMQ 전송 실패 (TCP 5671 차단) | NSG Rule Port 5671 허용 여부 | `nsg-snet-aks` Inbound Rule 확인 |
| Key Vault 접근 오류 (403) | Managed Identity에 Key Vault Secrets User 역할 부여 여부 | `kv-medicalai-shared` → Access control (IAM) 확인 |
| MSI 설치 실패 (서명 오류) | `signtool.exe verify /pa` 결과 확인 | ISV에 서명된 최신 MSI 재요청 |
| 서비스 시작 실패 | config-template.json 형식 오류 | `C:\ProgramData\MedicalAI\logs\install.log` 확인 |
| Arc 에이전트 등록 실패 | TCP 443 Outbound — Arc FQDN 도달 가능 여부 | 병원 방화벽에서 Arc 엔드포인트 FQDN 허용 확인 |
| Arc Run Command 타임아웃 | MSI 다운로드 시간 초과 | Blob SAS URL 유효 기간 확인, 대역폭 확인 |
| 2012 R2 Arc ESU 만료 임박 | OS 버전 및 ESU 만료일 확인 | 병원에 OS 업그레이드 일정 협의 |

---

## 9. 참고 링크

| 목적 | 링크 |
|---|---|
| Windows Installer 개요 | [learn.microsoft.com/en-us/windows/win32/msi/about-windows-installer](https://learn.microsoft.com/en-us/windows/win32/msi/about-windows-installer) |
| msiexec 커맨드라인 레퍼런스 | [learn.microsoft.com/en-us/windows-server/administration/windows-commands/msiexec](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/msiexec) |
| .NET 8 Windows Service + MSI Installer | [learn.microsoft.com/en-us/dotnet/core/extensions/windows-service-with-installer](https://learn.microsoft.com/en-us/dotnet/core/extensions/windows-service-with-installer) |
| Azure Arc — 서버 네트워크 요구사항 | [learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements](https://learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements) |
| Azure Arc ESU (Windows Server 2012) | [learn.microsoft.com/en-us/azure/azure-arc/servers/deliver-extended-security-updates](https://learn.microsoft.com/en-us/azure/azure-arc/servers/deliver-extended-security-updates) |
| Azure Update Manager 개요 | [learn.microsoft.com/en-us/azure/update-manager/overview](https://learn.microsoft.com/en-us/azure/update-manager/overview) |
| Arc Run Command | [learn.microsoft.com/en-us/azure/azure-arc/servers/run-command](https://learn.microsoft.com/en-us/azure/azure-arc/servers/run-command) |
| Arc Machine Configuration 개요 | [learn.microsoft.com/en-us/azure/governance/machine-configuration/overview](https://learn.microsoft.com/en-us/azure/governance/machine-configuration/overview) |
