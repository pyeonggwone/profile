. "$PSScriptRoot\common.ps1"

Assert-Administrator

$profile = Get-HostOsProfile
Assert-SupportedHostOs -Profile $profile
$state = Get-HyperVHostState -Profile $profile

if ($state.featureState -eq "Enabled" -and $state.moduleAvailable) {
    Write-Host "Hyper-V is already enabled and the Hyper-V PowerShell module is available."
    return
}

Write-Host "Enabling Hyper-V. A reboot may be required."

if ($state.method -eq "WindowsFeature") {
    if ($state.featureState -eq "Enabled" -and -not $state.moduleAvailable) {
        Write-Host "Hyper-V role is enabled, but Hyper-V PowerShell module is missing. Installing management tools."
        Install-WindowsFeature -Name Hyper-V-PowerShell | Out-Host
    }
    else {
        Install-WindowsFeature -Name Hyper-V -IncludeManagementTools | Out-Host
    }
}
elseif ($state.method -eq "WindowsOptionalFeature") {
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All -NoRestart | Out-Host
}
else {
    throw "Unable to determine the correct Hyper-V enable method for this host."
}

Write-Host "Hyper-V enable command completed. Reboot Windows if the feature state is not Enabled."