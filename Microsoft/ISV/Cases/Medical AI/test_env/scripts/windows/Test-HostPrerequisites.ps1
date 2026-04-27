. "$PSScriptRoot\common.ps1"

Assert-Administrator

$envValues = Read-DotEnv
$isoPath = Resolve-TestEnvPath $envValues.ROCKY_ISO_PATH
$hostProfile = Get-HostOsProfile
Assert-SupportedHostOs -Profile $hostProfile
$hyperVState = Get-HyperVHostState -Profile $hostProfile
$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem

Write-Host "Medical AI test_env host prerequisite check"
Write-Host "OS: $($os.Caption) $($os.Version)"
Write-Host "Detected profile: $($hostProfile.profileId)"
Write-Host "Target host: $($envValues.WINDOWS_HOST_TARGET)"
Write-Host "Hyper-V feature method: $($hyperVState.method)"
Write-Host "Hyper-V feature: $($hyperVState.featureState)"
Write-Host "Hyper-V management tools: $($hyperVState.managementToolsState)"
Write-Host "Hyper-V PowerShell module available: $($hyperVState.moduleAvailable)"
Write-Host "Hypervisor present: $($computer.HypervisorPresent)"

if ($hostProfile.isServer -and $envValues.HYPERV_SWITCH_NAME -eq "Default Switch") {
    Write-Warning "Windows Server usually does not provide Hyper-V Default Switch. Create an external switch and update HYPERV_SWITCH_NAME if needed."
}

if ($hyperVState.featureState -ne "Enabled" -or -not $hyperVState.moduleAvailable) {
    Write-Warning "Hyper-V is not enabled. Run Enable-HyperV.ps1 and reboot if required."
}

if (-not (Test-Path $isoPath)) {
    Write-Warning "Rocky Linux ISO was not found at: $isoPath"
    Write-Warning "Download Rocky Linux 9.7 x86_64 minimal ISO and update ROCKY_ISO_PATH in .env if needed."
}

Write-Host "Prerequisite check completed."