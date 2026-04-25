[CmdletBinding()]
param(
    [switch]$SkipLargeAssetCheck
)

$ErrorActionPreference = "Stop"

$InstallerRoot = $PSScriptRoot
$TestEnvRoot = Resolve-Path (Join-Path $InstallerRoot "..")
$WorkRoot = Join-Path $InstallerRoot "_work"
$PackageRoot = Join-Path $WorkRoot "package"
$PayloadRoot = Join-Path $PackageRoot "payload"
$OutputRoot = Join-Path $InstallerRoot "output"
$InnoScript = Join-Path $InstallerRoot "MedicalAIInstaller.iss"

function Find-Iscc {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "Inno Setup compiler was not found. Install Inno Setup 6 or add ISCC.exe to PATH."
}

function Assert-LargeAssets {
    $requiredAssets = @(
        "assets\rocky9\medicalai-rocky9-k3s.vhdx"
    )

    $recommendedAssets = @(
        "assets\images\data-sender.tar",
        "assets\images\pii-processor.tar",
        "assets\images\remote-update-agent.tar",
        "assets\images\medicalai-monitor.tar"
    )

    foreach ($asset in $requiredAssets) {
        $path = Join-Path $InstallerRoot $asset
        if (-not (Test-Path $path)) {
            throw "Required installer asset is missing: $asset. Use -SkipLargeAssetCheck only for packaging flow tests."
        }
    }

    foreach ($asset in $recommendedAssets) {
        $path = Join-Path $InstallerRoot $asset
        if (-not (Test-Path $path)) {
            Write-Warning "Recommended offline image is missing: $asset"
        }
    }
}

if (-not $SkipLargeAssetCheck) {
    Assert-LargeAssets
}

if (Test-Path $WorkRoot) {
    Remove-Item -Recurse -Force $WorkRoot
}
New-Item -ItemType Directory -Force -Path $PayloadRoot, $OutputRoot | Out-Null

$excludeNames = @("installer", "generated", "_work", "output")
Get-ChildItem -Path $TestEnvRoot | Where-Object { $excludeNames -notcontains $_.Name } | ForEach-Object {
    $destination = Join-Path $PayloadRoot $_.Name
    Copy-Item -Path $_.FullName -Destination $destination -Recurse -Force
}

Copy-Item -Path (Join-Path $InstallerRoot "payload\*") -Destination $PayloadRoot -Recurse -Force
Copy-Item -Path (Join-Path $InstallerRoot "assets") -Destination (Join-Path $PayloadRoot "assets") -Recurse -Force

$buildInfo = [ordered]@{
    product = "Medical AI Local Runtime"
    builtAt = (Get-Date).ToUniversalTime().ToString("o")
    sourceRoot = $TestEnvRoot.Path
    skipLargeAssetCheck = [bool]$SkipLargeAssetCheck
}
$buildInfo | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $PayloadRoot "InstallerBuildInfo.json") -Encoding UTF8

$iscc = Find-Iscc
Write-Host "Using Inno Setup compiler: $iscc"
& $iscc "/DSourceDir=$PackageRoot" "/DOutputDir=$OutputRoot" $InnoScript

$installerExe = Join-Path $OutputRoot "MedicalAI-Installer.exe"
if (-not (Test-Path $installerExe)) {
    throw "Installer build completed but output was not found: $installerExe"
}

Write-Host "Installer created: $installerExe"
