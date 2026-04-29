function Get-TestEnvRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Resolve-TestEnvPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }

    return (Join-Path (Get-TestEnvRoot) $Path)
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
        hyperVFeatureName = "Microsoft-Hyper-V-All"
        expectsDefaultSwitch = -not $isServer
        recommendedMinimumMemoryBytes = 8589934592
    }
}

function Assert-SupportedHostOs {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Profile
    )

    if (-not $Profile.supported) {
        throw "Unsupported Windows host OS for Medical AI test_env packaging: $($Profile.caption) $($Profile.version)"
    }
}

function Read-DotEnv {
    param(
        [string]$Path = (Join-Path (Get-TestEnvRoot) ".env")
    )

    $values = @{}
    if (-not (Test-Path $Path)) {
        throw ".env file not found: $Path"
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) {
            return
        }
        $index = $line.IndexOf("=")
        if ($index -lt 1) {
            return
        }
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
        throw "Run this script from an elevated PowerShell session."
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
            featureName = "Hyper-V"
            featureState = if ($role) { if ($role.Installed) { "Enabled" } else { "Disabled" } } else { "Unknown" }
            managementToolsState = if ($powershellFeature) { if ($powershellFeature.Installed) { "Enabled" } else { "Disabled" } } else { "Unknown" }
            moduleAvailable = $moduleAvailable
        }
    }

    $optionalFeature = $null
    try {
        $optionalFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction Stop
    }
    catch {
        return [ordered]@{
            method = "WindowsOptionalFeature"
            featureName = "Microsoft-Hyper-V-All"
            featureState = "Unknown"
            managementToolsState = "Unknown"
            moduleAvailable = $moduleAvailable
            error = $_.Exception.Message
        }
    }

    return [ordered]@{
        method = "WindowsOptionalFeature"
        featureName = "Microsoft-Hyper-V-All"
        featureState = $optionalFeature.State.ToString()
        managementToolsState = $optionalFeature.State.ToString()
        moduleAvailable = $moduleAvailable
    }
}