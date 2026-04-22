# Implementation Guide: Hospital On-Premises Client — PowerShell Installer Universal Deployment

> Scenario: Deploy Windows Services via PowerShell-based installer scripts on hospital servers running Windows Server 2012 R2 or later, and integrate with ISV Azure SaaS backend  
> Network integration reference: [hipaa-network.ver4.md](../Implement_Network/hipaa-network.ver4.md) — S2S VPN + NSG  
> HIPAA standards: §164.312(e)(1) Transmission Security, §164.312(e)(2)(ii) Encryption in Transit, §164.312(b) Audit Controls  
> Version: v3 (2026-04-21)

---

## Deployment Method Selection Criteria

| Item | This Guide (PowerShell Installer) | [Guide 05 (k3s)](./05-windows-installer-client.ver7.md) |
|---|---|---|
| **Supported OS** | Windows Server 2012 R2 or later (universal) | Windows Server 2019 / 2022 only |
| **Runtime** | Windows SCM (Service Control Manager) | k3s (containerd) |
| **Deployment Unit** | ZIP bundle + `Install.ps1` | Container image |
| **Remote Update** | Arc Run Command (`Install.ps1`) | Arc GitOps (Flux) |
| **Hospital IT Skill Required** | Low (standard Windows operations) | High (basic K8s knowledge required) |

> **Selection Criteria**: Apply this guide to hospitals with unclear or mixed OS versions, or Windows-only operations environments.

---

## Overall Architecture

```
Hospital On-Premises (Windows Server)
  └─ MedicalAI-Client.zip bundle (Install.ps1 execution)
      ├─ PII Masking Service (Windows Service — registered via New-Service)
      ├─ RabbitMQ Producer Agent (Windows Service — registered via New-Service)
      └─ Config Sync Service (Windows Service — registered via New-Service)
          └─[S2S VPN — IPsec AES-256]─ Azure VPN Gateway (vpngw-medicalai-hub-us)
              └─ NSG (nsg-snet-aks) — least-privilege access control
                  └─ AKS Microservices (10.2.10.0/24)
                      ├─ RabbitMQ Cluster
                      ├─ MySQL Flexible Server (VNet Integration)
                      └─ AI Analysis Module

Arc-enabled Server (Hospital On-Premises Server)
  └─[HTTPS 443]─ Azure Arc Service
      ├─ Azure Update Manager — OS patch management
      ├─ Machine Configuration — HIPAA drift detection
      └─ Run Command — Install.ps1 remote execution
```

---

## 1. Supported OS Matrix

| OS | PowerShell Version | New-Service Support | Arc Support | HIPAA Patch Management | Notes |
|---|---|---|---|---|---|
| Windows Server 2022 | PS 5.1 / 7.x | ✅ | ✅ | ✅ | **Recommended** |
| Windows Server 2019 | PS 5.1 / 7.x | ✅ | ✅ | ✅ | Supported |
| Windows Server 2016 | PS 5.1 | ✅ | ✅ | ✅ | Supported |
| Windows Server 2012 R2 | PS 4.0+ | ✅ | ✅ Arc ESU | ⚠️ Arc ESU ends 2026-10 | Recommend OS upgrade before contract |
| Windows Server 2012 | PS 4.0+ | ✅ | ✅ Arc ESU | ⚠️ Arc ESU ends 2026-10 | Recommend OS upgrade before contract |
| Windows Server 2008 R2 | PS 2.0 | ⚠️ Limited | ⚠️ Arc ESU ended | ❌ No patches | **HIPAA non-compliant — excluded from support** |

> **Arc ESU**: Windows Server 2012/2012 R2 receive free ESU via Azure Arc. Ends October 2026.  
> **2008 R2 and below**: As of April 2026, deploying PHI processing agents to unpatched OS creates §164.312(a)(2)(ii) violation risk → excluded from support.

---

## 2. Deployment File Structure

### 2-1. Deployment Bundle Files

| Filename | Type | Purpose |
|---|---|---|
| `MedicalAI-Client.zip` | ZIP bundle (signed EXE + PS scripts) | Full client component deployment unit |
| `Install.ps1` | Signed PowerShell script | Register and start Windows services via `New-Service` |
| `Uninstall.ps1` | Signed PowerShell script | Remove Windows services via `Remove-Service` |
| `config-template.json` | JSON configuration template | Azure integration info (endpoints, authentication) |
| `install-guide.pdf` | Installation manual | Guide for hospital IT staff |
| `cert-bundle.pfx` | TLS certificate bundle | ISV-issued client certificate (mTLS option) |

> **Packaging rationale**: `New-Service` + PowerShell scripts are Microsoft's official service management method that works across all Windows Server 2012 R2 and later versions. Fully self-contained using only `dotnet publish` + built-in Windows tools, no third-party build tools required.  
> Reference: [learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-create](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-create)

### 2-2. ZIP Bundle Internal Structure

```
MedicalAI-Client.zip
  ├─ pii-masking-service.exe       # .NET 8 self-contained build
  ├─ rabbitmq-producer.exe         # .NET 8 self-contained build
  ├─ config-sync.exe               # .NET 8 self-contained build
  ├─ Install.ps1                   # Service registration script (signed)
  ├─ Uninstall.ps1                 # Service removal script (signed)
  └─ config-template.json          # Azure integration configuration template
```

### 2-3. Windows Services Created After Installation

| Service Name | Executable | Role |
|---|---|---|
| `MedicalAI PII Masker` | `pii-masking-service.exe` | Receives EMR/PACS data and masks patient identifiers |
| `MedicalAI Queue Agent` | `rabbitmq-producer.exe` | Transmits masked data to Azure (AMQP-over-TLS) |
| `MedicalAI Config Sync` | `config-sync.exe` | Synchronizes configuration values from Azure Key Vault (periodic polling) |

> Each service runs under a dedicated local service account (no administrator privileges — §164.312(a)(1) least privilege)

---

## 3. ISV-Side Azure Pre-Configuration

### 3-1. Build Flow (Microsoft Official Tools Only)

```
ISV Development Team (.NET 8 projects × 3)
  └─ dotnet publish --self-contained -r win-x64 --output ./publish
      ├─ pii-masking-service.exe    ← Single executable with .NET Runtime included
      ├─ rabbitmq-producer.exe
      └─ config-sync.exe
          ↓
  signtool.exe (Windows SDK) — EXE code signing (ISV code signing certificate)
          ↓
  Author Install.ps1 / Uninstall.ps1
          ↓
  Set-AuthenticodeSignature (PowerShell) — Sign PS scripts
          ↓
  Compress-Archive (PowerShell) — Create MedicalAI-Client.zip
          ↓
  MedicalAI-Client.zip → Azure Blob Storage (for deployment)
```

> Tools used:  
> - `dotnet publish`: Built into Microsoft .NET SDK  
> - `signtool.exe`: Built into Microsoft Windows SDK  
> - `Set-AuthenticodeSignature`: Microsoft PowerShell built-in cmdlet  
> - `Compress-Archive`: Microsoft PowerShell built-in cmdlet

**EXE Code Signing:**

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

**PowerShell Script Signing (`Set-AuthenticodeSignature`):**

```powershell
# Load ISV code signing certificate
$cert = Get-PfxCertificate -FilePath "ISV-CodeSign.pfx"

# Sign Install.ps1 / Uninstall.ps1
Set-AuthenticodeSignature -FilePath ".\Install.ps1"   -Certificate $cert -TimestampServer "http://timestamp.digicert.com"
Set-AuthenticodeSignature -FilePath ".\Uninstall.ps1" -Certificate $cert -TimestampServer "http://timestamp.digicert.com"

# Verify signature
Get-AuthenticodeSignature -FilePath ".\Install.ps1" | Select-Object -ExpandProperty Status
# Valid
```

**ZIP Bundle Creation:**

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

### 3-2. Install.ps1 Core Structure (Using Microsoft Official New-Service)

```powershell
#Requires -RunAsAdministrator
param(
    [Parameter(Mandatory=$true)]
    [string]$InstallDir = "C:\Program Files\MedicalAI",
    [string]$ConfigPath = "C:\ProgramData\MedicalAI\config-template.json",
    [string]$LogDir     = "C:\ProgramData\MedicalAI\logs"
)

# Create installation directories
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir     | Out-Null

# Create service accounts (dedicated local accounts — not in Administrators group, §164.312(a)(1))
$svcAccounts = @("svc-medicalai-pii", "svc-medicalai-queue", "svc-medicalai-config")
foreach ($acct in $svcAccounts) {
    $pwd = [System.Web.Security.Membership]::GeneratePassword(24, 4)
    $secPwd = ConvertTo-SecureString $pwd -AsPlainText -Force
    New-LocalUser -Name $acct -Password $secPwd -PasswordNeverExpires -UserMayNotChangePassword | Out-Null
}

# Copy executables
Copy-Item -Path ".\pii-masking-service.exe" -Destination $InstallDir -Force
Copy-Item -Path ".\rabbitmq-producer.exe"   -Destination $InstallDir -Force
Copy-Item -Path ".\config-sync.exe"         -Destination $InstallDir -Force

# Place config file
Copy-Item -Path ".\config-template.json" -Destination $ConfigPath -Force

# Register Windows services — New-Service (Microsoft PowerShell official cmdlet)
New-Service -Name "MedicalAI PII Masker" `
  -BinaryPathName "`"$InstallDir\pii-masking-service.exe`" --config `"$ConfigPath`"" `
  -DisplayName "MedicalAI PII Masking Service" `
  -StartupType Automatic `
  -Description "MedicalAI: EMR/PACS patient identifier masking service (HIPAA §164.312)"

New-Service -Name "MedicalAI Queue Agent" `
  -BinaryPathName "`"$InstallDir\rabbitmq-producer.exe`" --config `"$ConfigPath`"" `
  -DisplayName "MedicalAI RabbitMQ Producer Agent" `
  -StartupType Automatic `
  -Description "MedicalAI: Azure transmission agent (AMQP-over-TLS)"

New-Service -Name "MedicalAI Config Sync" `
  -BinaryPathName "`"$InstallDir\config-sync.exe`" --config `"$ConfigPath`"" `
  -DisplayName "MedicalAI Config Sync Service" `
  -StartupType Automatic `
  -Description "MedicalAI: Azure Key Vault configuration synchronization"

# Start services
Start-Service -Name "MedicalAI PII Masker"
Start-Service -Name "MedicalAI Queue Agent"
Start-Service -Name "MedicalAI Config Sync"

# Log installation result
$result = Get-Service -Name "MedicalAI*" | Select-Object Name, Status, StartType
$result | Out-File -FilePath "$LogDir\install.log" -Append
Write-Output "Installation complete:"
$result
```

> `New-Service` official documentation: [learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service)

### 3-3. Uninstall.ps1 Structure

```powershell
#Requires -RunAsAdministrator

$services = @("MedicalAI PII Masker", "MedicalAI Queue Agent", "MedicalAI Config Sync")

foreach ($svc in $services) {
    Stop-Service  -Name $svc -Force -ErrorAction SilentlyContinue
    Remove-Service -Name $svc -ErrorAction SilentlyContinue  # PS 6.0+ / SC.exe fallback
    # Windows Server 2012 R2 (PS 4.0) compatible alternative:
    # sc.exe delete $svc
}

Remove-Item -Path "C:\Program Files\MedicalAI" -Recurse -Force -ErrorAction SilentlyContinue
```

> On PS 4.0/5.0 environments (Server 2012 R2) where `Remove-Service` is unavailable, use `sc.exe delete` (Windows built-in).

### 3-4. VPN Configuration (ISV Responsibility)

**Step A. Register Local Network Gateway**

> Azure Portal → Local Network Gateways → + Create

| Item | Value |
|---|---|
| Name | `lng-hospital-us-001` |
| IP address | Hospital public IP (collected in advance) |
| Address space | Hospital internal CIDR (`192.168.10.0/24`) |
| BGP ASN | `65001` |

**Step B. Create VPN Connection**

> `vpngw-medicalai-hub-us` → Connections → + Add

| Item | Value |
|---|---|
| Connection type | Site-to-site (IPsec) |
| Local network gateway | `lng-hospital-us-001` |
| Shared key (PSK) | Key Vault `kv-medicalai-shared` → Secret `vpn-psk-hospital-us` |
| IPsec Policy | IKEv2 + AES-256 + SHA-256 (§164.312(e)(2)(ii)) |

> Detailed IPsec policy: [hipaa-network.ver4.md §1-3](../Implement_Network/hipaa-network.ver4.md)

**Step C. Add NSG Rule (Hospital → AKS)**

> Azure Portal → `nsg-snet-aks` → Inbound security rules → + Add

| Item | Value |
|---|---|
| Name | `allow-hospital-us-001-to-aks` |
| Source | `192.168.10.0/24` |
| Destination | `10.2.10.0/24` (AKS Subnet) |
| Destination port ranges | `443, 5671` |
| Protocol | TCP |
| Action | Allow |
| Priority | `200` |

### 3-5. Deployment File Hosting

| Delivery Method | Target | Notes |
|---|---|---|
| Azure Blob Storage (Private) + SAS URL | Initial deployment | Set short SAS URL expiry (within 24 hours) |
| ISV dedicated SFTP server | Offline / air-gapped hospitals | Enforce TLS 1.2 or higher |
| Secure USB / encrypted external drive | Fully internet-isolated hospitals | |
| Azure Marketplace Landing Page | After Marketplace registration | Auto-generate config with tenant info |

---

## 4. Hospital Server Installation Procedure

### 4-1. Prerequisites

| Item | Requirement |
|---|---|
| OS | Windows Server 2012 R2 or later (§164.312(a)(2)(ii) compliant versions) |
| PowerShell | 4.0 or later (built-in) |
| Network ports (Outbound) | TCP 443 (HTTPS), TCP 5671 (AMQPS) to Azure allowed |
| VPN appliance | IKEv2 support (Cisco / Palo Alto / FortiGate) |
| Hospital public IP | Provide to ISV in advance |
| Script signature verification | `Get-AuthenticodeSignature Install.ps1` → Status: Valid confirmed |

### 4-2. S2S VPN Connection Configuration (Hospital Network Team)

Configure IKEv2 tunnel on hospital VPN appliance:

| Item | Value |
|---|---|
| Remote IP | `pip-vpngw-medicalai-hub-us` (provided by ISV) |
| PSK | Provided by ISV (delivered via secure channel, do not store locally) |
| IKE Version | IKEv2 |
| Encryption | AES-256 / SHA-256 |
| Local CIDR | `192.168.10.0/24` |
| Remote CIDR | `10.2.10.0/24` |

### 4-3. Azure Arc Agent Registration (Hospital Server)

> Azure Portal → Azure Arc → Servers → + Add → Add a single server  
> Auto-generate script and run on the hospital server:

```powershell
# Run in administrator PowerShell
.\OnboardingScript.ps1
```

Verify registration:

```powershell
azcmagent show
# Status: Connected
```

### 4-4. Run Installation

```powershell
# 1. Download ZIP (using ISV-provided SAS URL)
$zipUrl  = "https://stmedicalaiarchive.blob.core.windows.net/deploy/MedicalAI-Client.zip?<SAS_TOKEN>"
$zipPath = "C:\deploy\MedicalAI-Client.zip"
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath

# 2. Extract archive
Expand-Archive -Path $zipPath -DestinationPath "C:\deploy\MedicalAI-Client" -Force

Set-Location "C:\deploy\MedicalAI-Client"

# 3. Verify script signature (required before installation — §164.312(c)(1))
$sig = Get-AuthenticodeSignature -FilePath ".\Install.ps1"
if ($sig.Status -ne "Valid") { throw "Install.ps1 signature verification failed: $($sig.StatusMessage)" }

# 4. Run installation
.\Install.ps1 -ConfigPath "C:\deploy\MedicalAI-Client\config-template.json"

# 5. Verify service status
Get-Service -Name "MedicalAI*" | Select-Object Name, Status, StartType
# MedicalAI PII Masker     Running  Automatic
# MedicalAI Queue Agent    Running  Automatic
# MedicalAI Config Sync    Running  Automatic
```

### 4-5. Configuration File (config-template.json)

Issued per hospital. Provided by ISV via Landing Page or SFTP:

```json
{
  "tenant": {
    "hospitalId": "hospital-us-001",
    "tenantId": "<HOSPITAL_ENTRA_TENANT_ID>",
    "region": "eastus"
  },
  "network": {
    "vpnMode": "s2s",
    "azureVpnGatewayIp": "<pip-vpngw-medicalai-hub-us public IP>",
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
    "serverCertThumbprint": "<ISV CA certificate thumbprint>"
  },
  "logging": {
    "logLevel": "Info",
    "localLogPath": "C:\\ProgramData\\MedicalAI\\logs",
    "retentionDays": 90
  }
}
```

> `pskSecretName` is retrieved at runtime from Azure Key Vault. PSK plaintext is never stored locally. (§164.312(a)(2)(iv))

---

## 5. Azure Integration Verification

### 5-1. VPN Tunnel

> Azure Portal → VPN Gateway `vpngw-medicalai-hub-us` → Connections  
> Confirm Connection status: **Connected**

```powershell
Test-NetConnection -ComputerName "10.2.10.10" -Port 443
# TcpTestSucceeded: True
```

### 5-2. RabbitMQ Transmission Verification

```powershell
Get-Content "C:\ProgramData\MedicalAI\logs\queue-agent.log" -Tail 30 | Select-String "Published|Error"
# [INFO] Published message to amqps://rabbitmq.internal.medicalai.com:5671/ecg.queue
```

### 5-3. Key Vault Access Verification

```powershell
Get-Content "C:\ProgramData\MedicalAI\logs\config-sync.log" -Tail 10 | Select-String "Synced|Error"
# [INFO] Synced 3 secrets from kv-medicalai-shared
```

---

## 6. Remote Updates — Arc Run Command

### 6-1. Remote Deployment of New Version

> Azure Portal → Azure Arc → Servers → Target server → Run command → RunPowerShellScript

```powershell
# Script to run via Arc Run Command
$zipBlobUrl = "https://stmedicalaiarchive.blob.core.windows.net/deploy/MedicalAI-Client-v2.zip?<SAS_TOKEN>"
$zipPath    = "C:\deploy\MedicalAI-Client-v2.zip"
$deployDir  = "C:\deploy\MedicalAI-Client-v2"

# Download ZIP
Invoke-WebRequest -Uri $zipBlobUrl -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath $deployDir -Force

Set-Location $deployDir

# Verify script signature
$sig = Get-AuthenticodeSignature -FilePath ".\Install.ps1"
if ($sig.Status -ne "Valid") { throw "Install.ps1 signature verification failed" }

# Stop existing services and reinstall (Uninstall → Install)
if (Test-Path "C:\deploy\MedicalAI-Client\Uninstall.ps1") {
    & "C:\deploy\MedicalAI-Client\Uninstall.ps1"
}
.\Install.ps1 -ConfigPath "C:\ProgramData\MedicalAI\config-template.json"

# Verify service status
Get-Service -Name "MedicalAI*" | Select-Object Name, Status
```

### 6-2. OS Patch Management (Azure Update Manager)

> Azure Portal → Azure Update Manager → Machines → Select hospital Arc server

| Feature | Setting |
|---|---|
| Patch schedule | Weekly (outside business hours) |
| Patch classification | Critical, Security auto-applied |
| Reboot policy | Auto-reboot after patching (auto-recovered via Automatic startup type) |
| Patch result log | Sent to Azure Log Analytics → `law-medicalai-shared` |

### 6-3. Arc Machine Configuration — HIPAA Drift Detection

| Detection Item | Policy Criteria | HIPAA Clause |
|---|---|---|
| 3 Windows services running state | Running / Automatic required | §164.312(a)(1) |
| TLS 1.0 / 1.1 disabled | Registry-based policy | §164.312(e)(2)(ii) |
| Log retention directory exists | `C:\ProgramData\MedicalAI\logs` | §164.312(b) |
| Service account permissions | Local service account, not in Administrators group | §164.312(a)(1) |

---

## 7. HIPAA Requirements Checklist

| Item | Implementation | HIPAA Clause |
|---|---|---|
| Encryption in transit | S2S VPN IPsec AES-256 + TLS 1.2 or higher | §164.312(e)(2)(ii) |
| No local PSK / secret storage | Azure Key Vault runtime retrieval | §164.312(a)(2)(iv) |
| Installation log retention | Local 90 days, Azure Log Analytics → Storage Archive 2190 days | §164.312(b) |
| Least-privilege service accounts | `New-Service` — dedicated local accounts, no administrator privileges | §164.312(a)(1) |
| Network access restriction | NSG inbound least-privilege rules | §164.312(e)(1) |
| Client authentication | Entra ID Managed Identity or mTLS certificate | §164.312(d) |
| Code integrity verification | `signtool.exe` (EXE) + `Set-AuthenticodeSignature` (PS scripts) + `Get-AuthenticodeSignature` before installation | §164.312(c)(1) |
| OS patch management | Azure Arc + Azure Update Manager | §164.312(a)(2)(ii) |
| Configuration compliance | Arc Machine Configuration — drift detection | §164.306(a)(1) |
| Legacy OS handling | Support 2012 R2 and later only, exclude 2008 R2 and below from contracts | §164.312(a)(2)(ii) |

---

## 8. Troubleshooting

| Symptom | Check | Action |
|---|---|---|
| VPN Connection status `Not connected` | Hospital VPN appliance IKEv2 config, PSK match | Re-verify [hipaa-network.ver4.md §1-3](../Implement_Network/hipaa-network.ver4.md) |
| RabbitMQ transmission failure (TCP 5671 blocked) | NSG Rule Port 5671 allowed | Check `nsg-snet-aks` Inbound Rule |
| Key Vault access error (403) | Key Vault Secrets User role assigned to Managed Identity | Check `kv-medicalai-shared` → Access control (IAM) |
| Install.ps1 signature verification failure | Check `Get-AuthenticodeSignature` result | Request re-signed latest bundle from ISV |
| `New-Service` execution error | Administrator privileges, duplicate service name registered | Check `Get-Service`, remove duplicate with `Remove-Service` |
| Service startup failure | config-template.json format error, Managed Identity not assigned | Check `C:\ProgramData\MedicalAI\logs\install.log` |
| Arc agent registration failure | TCP 443 Outbound — Arc FQDN reachability | Confirm Arc endpoint FQDNs allowed in hospital firewall |
| Arc Run Command timeout | ZIP download timeout | Check Blob SAS URL expiry, verify bandwidth |
| 2012 R2 Arc ESU expiry approaching | Check OS version and ESU expiry date | Coordinate OS upgrade timeline with hospital |

---

## 9. Reference Links

| Purpose | Link |
|---|---|
| New-Service cmdlet | [learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-service) |
| Remove-Service cmdlet | [learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/remove-service](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/remove-service) |
| sc.exe create (legacy OS compatibility) | [learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-create](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/sc-create) |
| Set-AuthenticodeSignature | [learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-authenticodesignature](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-authenticodesignature) |
| .NET 8 Worker Service (Windows Service) | [learn.microsoft.com/en-us/dotnet/core/extensions/windows-service](https://learn.microsoft.com/en-us/dotnet/core/extensions/windows-service) |
| dotnet publish options | [learn.microsoft.com/en-us/dotnet/core/tools/dotnet-publish](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-publish) |
| Azure Arc — Server network requirements | [learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements](https://learn.microsoft.com/en-us/azure/azure-arc/servers/network-requirements) |
| Azure Arc ESU (Windows Server 2012) | [learn.microsoft.com/en-us/azure/azure-arc/servers/deliver-extended-security-updates](https://learn.microsoft.com/en-us/azure/azure-arc/servers/deliver-extended-security-updates) |
| Azure Update Manager overview | [learn.microsoft.com/en-us/azure/update-manager/overview](https://learn.microsoft.com/en-us/azure/update-manager/overview) |
| Arc Run Command | [learn.microsoft.com/en-us/azure/azure-arc/servers/run-command](https://learn.microsoft.com/en-us/azure/azure-arc/servers/run-command) |
| Arc Machine Configuration overview | [learn.microsoft.com/en-us/azure/governance/machine-configuration/overview](https://learn.microsoft.com/en-us/azure/governance/machine-configuration/overview) |
