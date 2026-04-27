[CmdletBinding()]
param(
    [string]$RockyIsoUrl,
    [string]$VhdxSourcePath,
    [switch]$SkipIsoDownload,
    [switch]$BuildInstaller,
    [switch]$SkipLargeAssetCheck
)

. "$PSScriptRoot\common.ps1"

$ErrorActionPreference = "Stop"

$testEnvRoot = Get-TestEnvRoot
$installerRoot = Join-Path $testEnvRoot "installer"
$assetsRoot = Join-Path $installerRoot "assets"
$isoRoot = Join-Path $assetsRoot "iso"
$rockyRoot = Join-Path $assetsRoot "rocky9"
$imagesRoot = Join-Path $assetsRoot "images"
$k3sRoot = Join-Path $assetsRoot "k3s"
$rpmRoot = Join-Path $assetsRoot "rpms"
$logsRoot = Join-Path $assetsRoot "logs"
$hostProfile = Get-HostOsProfile
Assert-SupportedHostOs -Profile $hostProfile
$windowsProfileRoot = Join-Path $assetsRoot "windows\$($hostProfile.profileId)"

New-Item -ItemType Directory -Force -Path $isoRoot, $rockyRoot, $imagesRoot, $k3sRoot, $rpmRoot, $logsRoot, $windowsProfileRoot | Out-Null

$envValues = Read-DotEnv
if ([string]::IsNullOrWhiteSpace($RockyIsoUrl)) {
    $RockyIsoUrl = $envValues.ROCKY_ISO_URL
}
$isoPath = Resolve-TestEnvPath $envValues.ROCKY_ISO_PATH
$isoDirectory = Split-Path -Parent $isoPath
New-Item -ItemType Directory -Force -Path $isoDirectory | Out-Null

$profileManifest = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    purpose = "Medical AI test_env installer asset profile"
    hostProfile = $hostProfile
    packageProfileId = $hostProfile.profileId
    packageProfileAssetRoot = "assets/windows/$($hostProfile.profileId)"
    rockyIsoPath = $envValues.ROCKY_ISO_PATH
    rockyIsoUrl = $RockyIsoUrl
    pythonVersion = $envValues.PYTHON_VERSION
    pythonBaseImage = $envValues.PYTHON_BASE_IMAGE
    k3sVersion = $envValues.K3S_VERSION
    k3sInstallScriptUrl = $envValues.K3S_INSTALL_SCRIPT_URL
    k3sBinaryUrl = $envValues.K3S_BINARY_URL
    requiredInstallerAsset = "assets/rocky9/medicalai-rocky9-k3s.vhdx"
    notes = @(
        "The installer package is prepared for the detected Windows host profile.",
        "Use a Windows Server profile for the final customer package when the target server is Windows Server."
    )
}
$profileManifestPath = Join-Path $assetsRoot "HostProfile.json"
$profileManifest | ConvertTo-Json -Depth 8 | Set-Content -Path $profileManifestPath -Encoding UTF8

Write-Host "Detected host OS profile: $($hostProfile.profileId)"
Write-Host "OS: $($hostProfile.caption) $($hostProfile.version)"
Write-Host "Host profile manifest: $profileManifestPath"

if (-not $SkipIsoDownload) {
    if (Test-Path -Path $isoPath -PathType Leaf) {
        Write-Host "Rocky ISO already exists. Skipping ISO download: $isoPath"
    }
    else {
        Write-Host "Downloading Rocky Linux minimal ISO from official mirror."
        Write-Host "Source: $RockyIsoUrl"
        Write-Host "Target: $isoPath"
        Invoke-WebRequest -Uri $RockyIsoUrl -OutFile $isoPath
    }
}
else {
    Write-Host "Skipping ISO download because -SkipIsoDownload was specified."
}

$targetVhdxPath = Join-Path $rockyRoot "medicalai-rocky9-k3s.vhdx"
if ([string]::IsNullOrWhiteSpace($VhdxSourcePath)) {
    $vmPath = Resolve-TestEnvPath $envValues.WINDOWS_VM_PATH
    $VhdxSourcePath = Join-Path $vmPath "$($envValues.WINDOWS_VM_NAME)\Virtual Hard Disks\$($envValues.WINDOWS_VM_NAME).vhdx"
}

if (Test-Path $VhdxSourcePath) {
    Write-Host "Copying prepared Rocky VHDX into installer assets."
    Copy-Item -Path $VhdxSourcePath -Destination $targetVhdxPath -Force
}
else {
    Write-Warning "Prepared Rocky VHDX was not found: $VhdxSourcePath"
    Write-Warning "Create and prepare the VM first, then run this script again or pass -VhdxSourcePath."
}

if ($BuildInstaller) {
    $buildScript = Join-Path $installerRoot "Build-Installer.ps1"
    if ($SkipLargeAssetCheck) {
        & $buildScript -SkipLargeAssetCheck
    }
    else {
        & $buildScript
    }
}

Write-Host "Installer asset preparation completed."
Write-Host "ISO: $isoPath"
Write-Host "VHDX asset: $targetVhdxPath"
Write-Host "Images asset directory: $imagesRoot"
Write-Host "k3s asset directory: $k3sRoot"
Write-Host "RPM asset directory: $rpmRoot"
Write-Host "Windows profile asset directory: $windowsProfileRoot"