[CmdletBinding()]
param(
    [string]$InstallRoot = "C:\ProgramData\MedicalAI"
)

$ErrorActionPreference = "Stop"

$PayloadRoot = Join-Path $InstallRoot "payload"
$InstallScript = Join-Path $PayloadRoot "Install-MedicalAI.ps1"

try {
    Unregister-ScheduledTask -TaskName "MedicalAI-Install-Resume" -Confirm:$false -ErrorAction SilentlyContinue
} catch {
}

Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $InstallScript,
    "-InstallRoot", $InstallRoot
) -Verb RunAs
