#requires -Version 7

<#
.SYNOPSIS
  ppt-translate-v3 진입 스크립트.

.DESCRIPTION
  uv 가 설치되어 있으면 uv 로 실행, 아니면 시스템 python 으로 실행한다.
  PowerPoint 데스크톱 앱이 설치된 Windows 에서만 동작한다.

.EXAMPLE
  .\Run-Translate.ps1 input.pptx
  .\Run-Translate.ps1 extract input.pptx
#>
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'ppt_translate.py'

if (-not (Test-Path $script)) {
    throw "ppt_translate.py 를 찾을 수 없음: $script"
}

# 첫 인자가 .pptx 파일이면 'run' 명령으로 자동 라우팅
if ($Args.Count -ge 1 -and $Args[0].ToLower().EndsWith('.pptx')) {
    $Args = @('run') + $Args
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "[uv] $script $($Args -join ' ')" -ForegroundColor Cyan
    & uv run $script @Args
} else {
    Write-Host "[python] $script $($Args -join ' ')" -ForegroundColor Cyan
    & python $script @Args
}

exit $LASTEXITCODE
