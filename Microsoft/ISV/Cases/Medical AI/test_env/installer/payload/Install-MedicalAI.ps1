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
$HostProfilePath = Join-Path $AssetsRoot "HostProfile.json"

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

function Get-HostOsProfile {
    $os = Get-CimInstance Win32_OperatingSystem
    $computer = Get-CimInstance Win32_ComputerSystem
    $caption = $os.Caption
    $profileId = "unsupported-windows"
    $isSupported = $false
    $isServer = $os.ProductType -ne 1

    if ($caption -match "Windows Server 2022") {
        $profileId = "windows-server-2022"
        $isSupported = $true
    }
    elseif ($caption -match "Windows Server 2019") {
        $profileId = "windows-server-2019"
        $isSupported = $true
    }
    elseif ($caption -match "Windows 11") {
        $profileId = "windows-11"
        $isSupported = $true
    }

    return [ordered]@{
        profileId = $profileId
        supported = $isSupported
        isServer = $isServer
        caption = $caption
        version = $os.Version
        buildNumber = $os.BuildNumber
        architecture = $os.OSArchitecture
        computerName = $computer.Name
    }
}

function Assert-HostProfileMatchesPackage {
    $currentProfile = Get-HostOsProfile
    if (-not $currentProfile.supported) {
        throw "Unsupported Windows host OS for Medical AI installer: $($currentProfile.caption) $($currentProfile.version)"
    }

    if (-not (Test-Path $HostProfilePath)) {
        Write-InstallLog "Embedded HostProfile.json was not found. Continuing with current OS profile: $($currentProfile.profileId)."
        return
    }

    $packageProfile = Get-Content -Path $HostProfilePath -Raw | ConvertFrom-Json
    $packageProfileId = $packageProfile.packageProfileId
    if ([string]::IsNullOrWhiteSpace($packageProfileId)) {
        $packageProfileId = $packageProfile.hostProfile.profileId
    }

    Write-InstallLog "Current host OS profile: $($currentProfile.profileId) ($($currentProfile.caption) $($currentProfile.version))."
    Write-InstallLog "Package host OS profile: $packageProfileId."

    if ($packageProfileId -ne $currentProfile.profileId) {
        throw "Installer package profile '$packageProfileId' does not match current host profile '$($currentProfile.profileId)'. Rebuild the installer on the target OS profile."
    }
}

function Get-HyperVHostState {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Profile
    )

    $moduleAvailable = $null -ne (Get-Command Get-VM -ErrorAction SilentlyContinue)

    if ($Profile.isServer -and (Get-Command Get-WindowsFeature -ErrorAction SilentlyContinue)) {
        $role = Get-WindowsFeature -Name Hyper-V -ErrorAction SilentlyContinue
        $powershellFeature = Get-WindowsFeature -Name Hyper-V-PowerShell -ErrorAction SilentlyContinue

        return [ordered]@{
            method = "WindowsFeature"
            featureState = if ($role) { if ($role.Installed) { "Enabled" } else { "Disabled" } } else { "Unknown" }
            managementToolsState = if ($powershellFeature) { if ($powershellFeature.Installed) { "Enabled" } else { "Disabled" } } else { "Unknown" }
            moduleAvailable = $moduleAvailable
        }
    }

    $optionalFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction Stop
    return [ordered]@{
        method = "WindowsOptionalFeature"
        featureState = $optionalFeature.State.ToString()
        managementToolsState = $optionalFeature.State.ToString()
        moduleAvailable = $moduleAvailable
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
    $profile = Get-HostOsProfile
    $state = Get-HyperVHostState -Profile $profile

    if ($state.featureState -eq "Enabled" -and $state.moduleAvailable) {
        Write-InstallLog "Hyper-V is already enabled and the Hyper-V PowerShell module is available."
        return $false
    }

    Write-InstallLog "Enabling Hyper-V. Reboot is required before continuing."
    if ($state.method -eq "WindowsFeature") {
        if ($state.featureState -eq "Enabled" -and -not $state.moduleAvailable) {
            Install-WindowsFeature -Name Hyper-V-PowerShell | Out-Null
        }
        else {
            Install-WindowsFeature -Name Hyper-V -IncludeManagementTools | Out-Null
        }
    }
    else {
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All -NoRestart | Out-Null
    }
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
Assert-HostProfileMatchesPackage

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
