. "$PSScriptRoot\common.ps1"

Assert-Administrator

$envValues = Read-DotEnv
$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$hyperVFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All

Write-Host "Medical AI test_env host prerequisite check"
Write-Host "OS: $($os.Caption) $($os.Version)"
Write-Host "Target host: $($envValues.WINDOWS_HOST_TARGET)"
Write-Host "Hyper-V feature: $($hyperVFeature.State)"
Write-Host "Hypervisor present: $($computer.HypervisorPresent)"

if ($os.Caption -notmatch "Windows 11") {
    Write-Warning "This test_env is designed for Windows 11 Hyper-V. Current OS is $($os.Caption)."
}

if ($hyperVFeature.State -ne "Enabled") {
    Write-Warning "Hyper-V is not enabled. Run Enable-HyperV.ps1 and reboot if required."
}

if (-not (Test-Path $envValues.ROCKY_ISO_PATH)) {
    Write-Warning "Rocky Linux ISO was not found at: $($envValues.ROCKY_ISO_PATH)"
    Write-Warning "Download Rocky Linux 9.5 x86_64 DVD ISO and update ROCKY_ISO_PATH in .env."
}

Write-Host "Prerequisite check completed."