[CmdletBinding()]
param(
    [string]$InstallRoot = "C:\ProgramData\MedicalAI"
)

$ErrorActionPreference = "Stop"

$PayloadRoot = Join-Path $InstallRoot "payload"
$StatePath = Join-Path $InstallRoot "install-state.json"
$LogPath = Join-Path $InstallRoot "install.log"
$EnvPath = Join-Path $PayloadRoot ".env"
$AssetsRoot = Join-Path $PayloadRoot "assets"

function Write-InstallLog {
    param([string]$Message)
    $line = "$(Get-Date -Format o) $Message"
    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    Add-Content -Path $LogPath -Value $line
    Write-Host $line
}

function Read-DotEnv {
    param([string]$Path)
    $values = @{}
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        $index = $line.IndexOf("=")
        if ($index -lt 1) { return }
        $key = $line.Substring(0, $index).Trim()
        $value = $line.Substring($index + 1).Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $values[$key] = $value
    }
    return $values
}

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Medical AI installer must run as Administrator."
    }
}

function Save-State {
    param([hashtable]$State)
    $State | ConvertTo-Json -Depth 8 | Set-Content -Path $StatePath -Encoding UTF8
}

function Register-ResumeTask {
    $resumeScript = Join-Path $PayloadRoot "Resume-MedicalAIInstall.ps1"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$resumeScript`" -InstallRoot `"$InstallRoot`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
    Register-ScheduledTask -TaskName "MedicalAI-Install-Resume" -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
}

function Enable-HyperVIfNeeded {
    $feature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All
    if ($feature.State -eq "Enabled") {
        Write-InstallLog "Hyper-V is already enabled."
        return $false
    }

    Write-InstallLog "Enabling Hyper-V. Reboot is required before continuing."
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All -NoRestart | Out-Null
    return $true
}

function Ensure-RequiredAssets {
    $vhdxPath = Join-Path $AssetsRoot "rocky9\medicalai-rocky9-k3s.vhdx"
    if (-not (Test-Path $vhdxPath)) {
        throw "Required prebuilt Rocky Linux VHDX was not found: $vhdxPath"
    }
}

function Start-InstallAfterHyperV {
    param([hashtable]$EnvValues)

    Ensure-RequiredAssets

    $vmName = $EnvValues.WINDOWS_VM_NAME
    $vmPath = $EnvValues.WINDOWS_VM_PATH
    $switchName = $EnvValues.HYPERV_SWITCH_NAME
    $memoryStartupBytes = [int64]$EnvValues.VM_MEMORY_STARTUP_BYTES
    $processorCount = [int]$EnvValues.VM_PROCESSOR_COUNT
    $sourceVhdx = Join-Path $AssetsRoot "rocky9\medicalai-rocky9-k3s.vhdx"
    $targetVmRoot = Join-Path $vmPath $vmName
    $targetVhdRoot = Join-Path $targetVmRoot "Virtual Hard Disks"
    $targetVhdx = Join-Path $targetVhdRoot "$vmName.vhdx"

    if (-not (Get-VMSwitch -Name $switchName -ErrorAction SilentlyContinue)) {
        throw "Hyper-V switch was not found: $switchName. Update HYPERV_SWITCH_NAME in embedded .env."
    }

    if (-not (Get-VM -Name $vmName -ErrorAction SilentlyContinue)) {
        Write-InstallLog "Creating Hyper-V VM: $vmName"
        New-Item -ItemType Directory -Force -Path $targetVhdRoot | Out-Null
        Copy-Item -Path $sourceVhdx -Destination $targetVhdx -Force
        New-VM -Name $vmName -Generation 2 -MemoryStartupBytes $memoryStartupBytes -SwitchName $switchName -Path $vmPath -VHDPath $targetVhdx | Out-Null
        Set-VMProcessor -VMName $vmName -Count $processorCount
        Set-VMMemory -VMName $vmName -DynamicMemoryEnabled $true -MinimumBytes 2147483648 -StartupBytes $memoryStartupBytes -MaximumBytes 4294967296
        Set-VMFirmware -VMName $vmName -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority
    }

    Start-VM -Name $vmName -ErrorAction SilentlyContinue
    Write-InstallLog "VM started: $vmName"

    $monitorUrl = "http://localhost:30090"
    Save-State @{
        phase = "vm_started"
        vmName = $vmName
        monitorUrl = $monitorUrl
        installRoot = $InstallRoot
    }

    Write-InstallLog "Pending integration: run guest-side k3s/image import/deploy commands inside Rocky Linux VM."
    Write-InstallLog "Pending integration: configure Windows portproxy 127.0.0.1:30090 to Rocky Linux VM monitor NodePort."
    & (Join-Path $PayloadRoot "Open-Monitor.ps1") -Url $monitorUrl
}

Assert-Administrator
Write-InstallLog "Medical AI installation started."

if (-not (Test-Path $EnvPath)) {
    throw "Embedded .env was not found: $EnvPath"
}

$envValues = Read-DotEnv -Path $EnvPath

if (Enable-HyperVIfNeeded) {
    Save-State @{
        phase = "hyperv_enabled_reboot_required"
        installRoot = $InstallRoot
    }
    Register-ResumeTask
    Write-InstallLog "Rebooting Windows to complete Hyper-V activation."
    Restart-Computer -Force
    return
}

Start-InstallAfterHyperV -EnvValues $envValues
Write-InstallLog "Medical AI installation bootstrap completed."
