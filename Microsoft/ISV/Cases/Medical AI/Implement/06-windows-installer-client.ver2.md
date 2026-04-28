# 구현 가이드: 병원 온프레미스 클라이언트 — PowerShell Installer 범용 배포 방식

> 적용 시나리오: Windows Server 2012 R2 이상 병원 서버에 PowerShell 기반 설치 스크립트로 Windows Service를 배포하고 ISV Azure SaaS 백엔드와 연동  
> 네트워크 연동 기준: [hipaa-network.ver4.md](../Implement_Network/hipaa-network.ver4.md) — S2S VPN + NSG  
> HIPAA 기준: §164.312(e)(1) 전송 보안, §164.312(e)(2)(ii) 전송 중 암호화, §164.312(b) 감사 통제  
> 버전: v2 (2026-04-20 — WiX 제거, Microsoft 공식 PowerShell + New-Service 방식으로 전환)

---

## WiX → PowerShell Installer 전환 배경

| 항목 | 이전 방식 (v1 — WiX) | 이 가이드 (v2 — PowerShell Installer) |
|---|---|---|
| **패키징 도구** | WiX Toolset (서드파티) | `dotnet publish` + `New-Service` (Microsoft 공식) |
| **배포 단위** | `.msi` (Windows Installer 패키지) | `.zip` 번들 + `Install.ps1` (서명된 PowerShell 스크립트) |
| **서비스 등록** | WiX `ServiceInstall` 엘리먼트 | PowerShell `New-Service` cmdlet (Windows 내장) |
| **서비스 제거** | WiX `ServiceControl` 엘리먼트 | PowerShell `Remove-Service` cmdlet (Windows 내장) |
| **OS 호환성** | Windows Installer 지원 OS 전체 | Windows Server 2012 R2 이상 (PowerShell 4.0+) |
| **Arc Run Command 연동** | `msiexec.exe` 호출 | `Install.ps1` 직접 실행 |

> **Microsoft 공식 근거**:  
> - `New-Service`: [learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service)  
> - `dotnet publish` Windows Service: [learn.microsoft.com/en-us/dotnet/core/extensions/windows-service](https://learn.microsoft.com/en-us/dotnet/core/extensions/windows-service)  
> - PowerShell 스크립트 서명: [learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-authenticodesignature](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-authenticodesignature)

---

## 배포 방식 선택 기준

| 항목 | 이 가이드 (PowerShell Installer) | [05 가이드 (k3s)](./05-windows-installer-client.ver7.md) |
|---|---|---|
| **지원 OS** | Windows Server 2012 R2 이상 (범용) | Windows Server 2019 / 2022 전용 |
| **런타임** | Windows SCM (Service Control Manager) | k3s (containerd) |
| **배포 단위** | ZIP 번들 + `Install.ps1` | 컨테이너 이미지 |
| **원격 업데이트** | Arc Run Command (`Install.ps1`) | Arc GitOps (Flux) |
| **병원 IT 요구 역량** | 낮음 (표준 Windows 운영) | 높음 (K8s 기본 이해 필요) |

> **선택 기준**: OS 버전이 불명확하거나 혼재하는 병원, Windows 전용 운영 환경에 이 가이드 적용.

---

## 전체 구조

```
병원 온프레미스 (Windows Server)
  └─ MedicalAI-Client.zip 번들 (Install.ps1 실행)
      ├─ PII Masking Service (Windows Service — New-Service 등록)
      ├─ RabbitMQ Producer Agent (Windows Service — New-Service 등록)
      └─ Config Sync Service (Windows Service — New-Service 등록)
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
      └─ Run Command — Install.ps1 원격 실행
```

---

## 1. 지원 OS 매트릭스

| OS | PowerShell 버전 | New-Service 지원 | Arc 지원 | HIPAA 패치 관리 | 비고 |
|---|---|---|---|---|---|
| Windows Server 2022 | PS 5.1 / 7.x | ✅ | ✅ | ✅ | **권장** |
| Windows Server 2019 | PS 5.1 / 7.x | ✅ | ✅ | ✅ | 지원 |
| Windows Server 2016 | PS 5.1 | ✅ | ✅ | ✅ | 지원 |
| Windows Server 2012 R2 | PS 4.0+ | ✅ | ✅ Arc ESU | ⚠️ Arc ESU 2026-10 종료 | 계약 전 OS 업그레이드 권고 |
| Windows Server 2012 | PS 4.0+ | ✅ | ✅ Arc ESU | ⚠️ Arc ESU 2026-10 종료 | 계약 전 OS 업그레이드 권고 |
| Windows Server 2008 R2 | PS 2.0 | ⚠️ 제한적 | ⚠️ Arc ESU 종료 | ❌ 패치 없음 | **HIPAA 준수 불가 — 지원 제외** |

> **Arc ESU**: Windows Server 2012/2012 R2는 Azure Arc를 통해 ESU 무료 제공. 2026년 10월 종료 예정.  
> **2008 R2 이하**: 현재 시점(2026-04) 기준 패치가 없는 OS에 PHI 처리 에이전트 배포는 §164.312(a)(2)(ii) 위반 소지 → 지원 제외.

---

## 2. 배포 파일 구성

### 2-1. 배포 번들 파일 종류

| 파일명 | 유형 | 용도 |
|---|---|---|
| `MedicalAI-Client.zip` | ZIP 번들 (서명된 EXE + PS 스크립트 포함) | 전체 클라이언트 컴포넌트 배포 단위 |
| `Install.ps1` | 서명된 PowerShell 스크립트 | `New-Service`로 Windows 서비스 등록 및 시작 |
| `Uninstall.ps1` | 서명된 PowerShell 스크립트 | `Remove-Service`로 Windows 서비스 제거 |
| `config-template.json` | JSON 설정 템플릿 | Azure 연동 정보 (엔드포인트, 인증) |
| `install-guide.pdf` | 설치 매뉴얼 | 병원 IT 담당자용 가이드 |
| `cert-bundle.pfx` | TLS 인증서 번들 | ISV 발급 클라이언트 인증서 (mTLS 옵션) |

> **패키징 방식 선택 근거**: `New-Service` + PowerShell 스크립트는 Windows Server 2012 R2 이상 전 버전에서 동작하는 Microsoft 공식 서비스 관리 방법. 서드파티 빌드 도구 없이 `dotnet publish` + Windows 내장 도구만으로 완결.  
> 참고: [learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-create](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-create)

### 2-2. ZIP 번들 내부 구조

```
MedicalAI-Client.zip
  ├─ pii-masking-service.exe       # .NET 8 self-contained 빌드
  ├─ rabbitmq-producer.exe         # .NET 8 self-contained 빌드
  ├─ config-sync.exe               # .NET 8 self-contained 빌드
  ├─ Install.ps1                   # 서비스 등록 스크립트 (서명됨)
  ├─ Uninstall.ps1                 # 서비스 제거 스크립트 (서명됨)
  └─ config-template.json          # Azure 연동 설정 템플릿
```

### 2-3. 설치 후 생성되는 Windows 서비스

| 서비스 이름 | 실행 파일 | 역할 |
|---|---|---|
| `MedicalAI PII Masker` | `pii-masking-service.exe` | EMR/PACS 데이터 수신 후 환자 식별정보 마스킹 |
| `MedicalAI Queue Agent` | `rabbitmq-producer.exe` | 마스킹 완료 데이터를 Azure로 전송 (AMQP-over-TLS) |
| `MedicalAI Config Sync` | `config-sync.exe` | Azure Key Vault에서 설정값 동기화 (주기적 polling) |

> 각 서비스는 전용 로컬 서비스 계정으로 실행 (관리자 권한 미부여 — §164.312(a)(1) 최소 권한)

---

## 3. ISV 측 Azure 사전 구성

### 3-1. 빌드 흐름 (Microsoft 공식 도구만 사용)

```
ISV 개발팀 (.NET 8 프로젝트 × 3)
  └─ dotnet publish --self-contained -r win-x64 --output ./publish
      ├─ pii-masking-service.exe    ← .NET Runtime 포함 단일 실행 파일
      ├─ rabbitmq-producer.exe
      └─ config-sync.exe
          ↓
  signtool.exe (Windows SDK) — EXE 코드 서명 (ISV 코드 서명 인증서)
          ↓
  Install.ps1 / Uninstall.ps1 작성
          ↓
  Set-AuthenticodeSignature (PowerShell) — PS 스크립트 서명
          ↓
  Compress-Archive (PowerShell) — MedicalAI-Client.zip 생성
          ↓
  MedicalAI-Client.zip → Azure Blob Storage (배포용)
```

> 사용 도구:  
> - `dotnet publish`: Microsoft .NET SDK 내장  
> - `signtool.exe`: Microsoft Windows SDK 내장  
> - `Set-AuthenticodeSignature`: Microsoft PowerShell 내장 cmdlet  
> - `Compress-Archive`: Microsoft PowerShell 내장 cmdlet

**EXE 코드 서명:**

```powershell
# signtool.exe (Windows SDK)
signtool.exe sign `
  /fd SHA256 `
  /tr http://timestamp.digicert.com `
  /td SHA256 `
  /f "ISV-CodeSign.pfx" `
  /p "<pfx-password>" `
  ".\publish\pii-masking-service.exe" `
  ".\publish\rabbitmq-producer.exe" `
  ".\publish\config-sync.exe"
```

**PowerShell 스크립트 서명 (`Set-AuthenticodeSignature`):**

```powershell
# ISV 코드 서명 인증서 로드
$cert = Get-PfxCertificate -FilePath "ISV-CodeSign.pfx"

# Install.ps1 / Uninstall.ps1 서명
Set-AuthenticodeSignature -FilePath ".\Install.ps1"   -Certificate $cert -TimestampServer "http://timestamp.digicert.com"
Set-AuthenticodeSignature -FilePath ".\Uninstall.ps1" -Certificate $cert -TimestampServer "http://timestamp.digicert.com"

# 서명 검증
Get-AuthenticodeSignature -FilePath ".\Install.ps1" | Select-Object -ExpandProperty Status
# Valid
```

**ZIP 번들 생성:**

```powershell
Compress-Archive -Path `
  ".\publish\pii-masking-service.exe", `
  ".\publish\rabbitmq-producer.exe", `
  ".\publish\config-sync.exe", `
  ".\Install.ps1", `
  ".\Uninstall.ps1", `
  ".\config-template.json" `
  -DestinationPath "MedicalAI-Client.zip"
```

### 3-2. Install.ps1 핵심 구조 (Microsoft 공식 New-Service 사용)

```powershell
#Requires -RunAsAdministrator
param(
    [Parameter(Mandatory=$true)]
    [string]$InstallDir = "C:\Program Files\MedicalAI",
    [string]$ConfigPath = "C:\ProgramData\MedicalAI\config-template.json",
    [string]$LogDir     = "C:\ProgramData\MedicalAI\logs"
)

# 설치 디렉토리 생성
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir     | Out-Null

# 서비스 계정 생성 (전용 로컬 계정 — 관리자 그룹 미포함, §164.312(a)(1))
$svcAccounts = @("svc-medicalai-pii", "svc-medicalai-queue", "svc-medicalai-config")
foreach ($acct in $svcAccounts) {
    $pwd = [System.Web.Security.Membership]::GeneratePassword(24, 4)
    $secPwd = ConvertTo-SecureString $pwd -AsPlainText -Force
    New-LocalUser -Name $acct -Password $secPwd -PasswordNeverExpires -UserMayNotChangePassword | Out-Null
}

# EXE 복사
Copy-Item -Path ".\pii-masking-service.exe" -Destination $InstallDir -Force
Copy-Item -Path ".\rabbitmq-producer.exe"   -Destination $InstallDir -Force
Copy-Item -Path ".\config-sync.exe"         -Destination $InstallDir -Force

# config 파일 배치
Copy-Item -Path ".\config-template.json" -Destination $ConfigPath -Force

# Windows 서비스 등록 — New-Service (Microsoft PowerShell 공식 cmdlet)
New-Service -Name "MedicalAI PII Masker" `
  -BinaryPathName "`"$InstallDir\pii-masking-service.exe`" --config `"$ConfigPath`"" `
  -DisplayName "MedicalAI PII Masking Service" `
  -StartupType Automatic `
  -Description "MedicalAI: EMR/PACS 환자 식별정보 마스킹 서비스 (HIPAA §164.312)"

New-Service -Name "MedicalAI Queue Agent" `
  -BinaryPathName "`"$InstallDir\rabbitmq-producer.exe`" --config `"$ConfigPath`"" `
  -DisplayName "MedicalAI RabbitMQ Producer Agent" `
  -StartupType Automatic `
  -Description "MedicalAI: Azure 전송 에이전트 (AMQP-over-TLS)"

New-Service -Name "MedicalAI Config Sync" `
  -BinaryPathName "`"$InstallDir\config-sync.exe`" --config `"$ConfigPath`"" `
  -DisplayName "MedicalAI Config Sync Service" `
  -StartupType Automatic `
  -Description "MedicalAI: Azure Key Vault 설정 동기화"

# 서비스 시작
Start-Service -Name "MedicalAI PII Masker"
Start-Service -Name "MedicalAI Queue Agent"
Start-Service -Name "MedicalAI Config Sync"

# 설치 결과 로그
$result = Get-Service -Name "MedicalAI*" | Select-Object Name, Status, StartType
$result | Out-File -FilePath "$LogDir\install.log" -Append
Write-Output "설치 완료:"
$result
```

> `New-Service` 공식 문서: [learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service)

### 3-3. Uninstall.ps1 구조

```powershell
#Requires -RunAsAdministrator

$services = @("MedicalAI PII Masker", "MedicalAI Queue Agent", "MedicalAI Config Sync")

foreach ($svc in $services) {
    Stop-Service  -Name $svc -Force -ErrorAction SilentlyContinue
    Remove-Service -Name $svc -ErrorAction SilentlyContinue  # PS 6.0+ / SC.exe 병행
    # Windows Server 2012 R2 (PS 4.0) 호환 대체:
    # sc.exe delete $svc
}

Remove-Item -Path "C:\Program Files\MedicalAI" -Recurse -Force -ErrorAction SilentlyContinue
```

> `Remove-Service`가 없는 PS 4.0/5.0 환경(Server 2012 R2)에서는 `sc.exe delete` 사용 (Windows 내장).

### 3-4. VPN 구성 (ISV 담당)

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

### 3-5. 배포 파일 호스팅

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
| PowerShell | 4.0 이상 (기본 내장) |
| 네트워크 포트 (Outbound) | TCP 443 (HTTPS), TCP 5671 (AMQPS) Azure 방향 허용 |
| VPN 장비 | IKEv2 지원 (Cisco / Palo Alto / FortiGate) |
| 병원 공인 IP | ISV에 사전 통보 |
| 스크립트 서명 검증 | `Get-AuthenticodeSignature Install.ps1` → Status: Valid 확인 |

### 4-2. S2S VPN 연결 구성 (병원 네트워크 담당)

병원 VPN 장비에서 IKEv2 터널 구성:

| 항목 | 값 |
|---|---|
| Remote IP | `pip-vpngw-medicalai-hub-us` (ISV 제공) |
| PSK | ISV 제공 (별도 보안 채널로 전달, 로컬 저장 금지) |
| IKE Version | IKEv2 |
| Encryption | AES-256 / SHA-256 |
| Local CIDR | `192.168.10.0/24` |
| Remote CIDR | `10.2.10.0/24` |

### 4-3. Azure Arc 에이전트 등록 (병원 서버)

> Azure Portal → Azure Arc → Servers → + Add → Add a single server  
> 스크립트 자동 생성 후 병원 서버에서 실행:

```powershell
# 관리자 권한 PowerShell에서 실행
.\OnboardingScript.ps1
```

등록 확인:

```powershell
azcmagent show
# Status: Connected
```

### 4-4. 설치 실행

```powershell
# 1. ZIP 다운로드 (ISV 제공 SAS URL 사용)
$zipUrl  = "https://stmedicalaiarchive.blob.core.windows.net/deploy/MedicalAI-Client.zip?<SAS_TOKEN>"
$zipPath = "C:\deploy\MedicalAI-Client.zip"
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath

# 2. 압축 해제
Expand-Archive -Path $zipPath -DestinationPath "C:\deploy\MedicalAI-Client" -Force

Set-Location "C:\deploy\MedicalAI-Client"

# 3. 스크립트 서명 검증 (설치 전 필수 — §164.312(c)(1))
$sig = Get-AuthenticodeSignature -FilePath ".\Install.ps1"
if ($sig.Status -ne "Valid") { throw "Install.ps1 서명 검증 실패: $($sig.StatusMessage)" }

# 4. 설치 실행
.\Install.ps1 -ConfigPath "C:\deploy\MedicalAI-Client\config-template.json"

# 5. 서비스 상태 확인
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

### 5-1. VPN 터널

> Azure Portal → VPN Gateway `vpngw-medicalai-hub-us` → Connections  
> Connection status: **Connected** 확인

```powershell
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

### 6-1. 신규 버전 원격 배포

> Azure Portal → Azure Arc → Servers → 대상 서버 → Run command → RunPowerShellScript

```powershell
# Arc Run Command에서 실행할 스크립트
$zipBlobUrl = "https://stmedicalaiarchive.blob.core.windows.net/deploy/MedicalAI-Client-v2.zip?<SAS_TOKEN>"
$zipPath    = "C:\deploy\MedicalAI-Client-v2.zip"
$deployDir  = "C:\deploy\MedicalAI-Client-v2"

# ZIP 다운로드
Invoke-WebRequest -Uri $zipBlobUrl -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath $deployDir -Force

Set-Location $deployDir

# 스크립트 서명 검증
$sig = Get-AuthenticodeSignature -FilePath ".\Install.ps1"
if ($sig.Status -ne "Valid") { throw "Install.ps1 서명 검증 실패" }

# 기존 서비스 중지 후 재설치 (Uninstall → Install)
if (Test-Path "C:\deploy\MedicalAI-Client\Uninstall.ps1") {
    & "C:\deploy\MedicalAI-Client\Uninstall.ps1"
}
.\Install.ps1 -ConfigPath "C:\ProgramData\MedicalAI\config-template.json"

# 서비스 상태 확인
Get-Service -Name "MedicalAI*" | Select-Object Name, Status
```

### 6-2. OS 패치 관리 (Azure Update Manager)

> Azure Portal → Azure Update Manager → Machines → 병원 Arc 서버 선택

| 기능 | 설정 |
|---|---|
| 패치 일정 | 주 1회 (업무 외 시간) |
| 패치 분류 | Critical, Security 자동 적용 |
| 재부팅 정책 | 패치 후 자동 재부팅 (서비스 Automatic 설정으로 자동 복구) |
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
| 최소 권한 서비스 계정 | `New-Service` — 전용 로컬 계정, 관리자 권한 미부여 | §164.312(a)(1) |
| 네트워크 접근 제한 | NSG inbound 최소 권한 규칙 | §164.312(e)(1) |
| 클라이언트 인증 | Entra ID Managed Identity 또는 mTLS 인증서 | §164.312(d) |
| 코드 무결성 검증 | `signtool.exe` (EXE) + `Set-AuthenticodeSignature` (PS 스크립트) + 설치 전 `Get-AuthenticodeSignature` | §164.312(c)(1) |
| OS 패치 관리 | Azure Arc + Azure Update Manager | §164.312(a)(2)(ii) |
| 설정 컴플라이언스 | Arc Machine Configuration — 드리프트 감지 | §164.306(a)(1) |
| 구버전 OS 대응 | 2012 R2 이상만 지원, 2008 R2 이하 계약 제외 | §164.312(a)(2)(ii) |

---

## 8. 문제 해결

| 증상 | 확인 사항 | 조치 |
|---|---|---|
| VPN Connection 상태 `Not connected` | 병원 VPN 장비 IKEv2 설정, PSK 일치 여부 | [hipaa-network.ver4.md §1-3](../Implement_Network/hipaa-network.ver4.md) 재확인 |
| RabbitMQ 전송 실패 (TCP 5671 차단) | NSG Rule Port 5671 허용 여부 | `nsg-snet-aks` Inbound Rule 확인 |
| Key Vault 접근 오류 (403) | Managed Identity에 Key Vault Secrets User 역할 부여 여부 | `kv-medicalai-shared` → Access control (IAM) 확인 |
| Install.ps1 서명 검증 실패 | `Get-AuthenticodeSignature` 결과 확인 | ISV에 재서명된 최신 번들 재요청 |
| `New-Service` 실행 오류 | 관리자 권한 여부, 동일 서비스명 중복 등록 여부 | `Get-Service` 확인 후 `Remove-Service`로 중복 제거 |
| 서비스 시작 실패 | config-template.json 형식 오류, Managed Identity 미할당 | `C:\ProgramData\MedicalAI\logs\install.log` 확인 |
| Arc 에이전트 등록 실패 | TCP 443 Outbound — Arc FQDN 도달 가능 여부 | 병원 방화벽에서 Arc 엔드포인트 FQDN 허용 확인 |
| Arc Run Command 타임아웃 | ZIP 다운로드 시간 초과 | Blob SAS URL 유효 기간 확인, 대역폭 확인 |
| 2012 R2 Arc ESU 만료 임박 | OS 버전 및 ESU 만료일 확인 | 병원에 OS 업그레이드 일정 협의 |

---

## 9. 참고 링크

| 목적 | 링크 |
|---|---|
| New-Service cmdlet | [learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service) |
| Remove-Service cmdlet | [learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/remove-service](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/remove-service) |
| sc.exe create (구버전 OS 호환) | [learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-create](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-create) |
| Set-AuthenticodeSignature | [learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-authenticodesignature](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-authenticodesignature) |
| .NET 8 Worker Service (Windows Service) | [learn.microsoft.com/en-us/dotnet/core/extensions/windows-service](https://learn.microsoft.com/en-us/dotnet/core/extensions/windows-service) |
| dotnet publish 옵션 | [learn.microsoft.com/en-us/dotnet/core/tools/dotnet-publish](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-publish) |
| Azure Arc — 서버 네트워크 요구사항 | [learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements](https://learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements) |
| Azure Arc ESU (Windows Server 2012) | [learn.microsoft.com/en-us/azure/azure-arc/servers/deliver-extended-security-updates](https://learn.microsoft.com/en-us/azure/azure-arc/servers/deliver-extended-security-updates) |
| Azure Update Manager 개요 | [learn.microsoft.com/en-us/azure/update-manager/overview](https://learn.microsoft.com/en-us/azure/update-manager/overview) |
| Arc Run Command | [learn.microsoft.com/en-us/azure/azure-arc/servers/run-command](https://learn.microsoft.com/en-us/azure/azure-arc/servers/run-command) |
| Arc Machine Configuration 개요 | [learn.microsoft.com/en-us/azure/governance/machine-configuration/overview](https://learn.microsoft.com/en-us/azure/governance/machine-configuration/overview) |
