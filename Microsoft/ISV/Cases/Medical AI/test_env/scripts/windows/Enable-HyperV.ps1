. "$PSScriptRoot\common.ps1"

Assert-Administrator

$feature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All
if ($feature.State -eq "Enabled") {
    Write-Host "Hyper-V is already enabled."
    return
}

Write-Host "Enabling Hyper-V. A reboot may be required."
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All -NoRestart
Write-Host "Hyper-V enable command completed. Reboot Windows if the feature state is not Enabled."