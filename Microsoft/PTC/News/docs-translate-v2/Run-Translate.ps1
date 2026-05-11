#requires -Version 7

<#
.SYNOPSIS
  docs-translate-v2 진입 스크립트.

.DESCRIPTION
  Microsoft Word COM Automation 기반 .docx/.doc 번역 도구를 실행한다.
  uv 가 설치되어 있으면 uv 로 실행, 아니면 시스템 python 으로 실행한다.
  첫 인자가 .docx/.doc 파일이면 run 명령으로 자동 라우팅한다.
#>
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'docs_translate.py'

if (-not (Test-Path $script)) {
    throw "docs_translate.py 를 찾을 수 없음: $script"
}

if ($Args.Count -ge 1 -and ($Args[0].ToLower().EndsWith('.docx') -or $Args[0].ToLower().EndsWith('.doc'))) {
    $Args = @('run') + $Args
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "[uv] $script $($Args -join ' ')" -ForegroundColor Cyan
    & uv run --script $script @Args
} else {
    Write-Host "[python] $script $($Args -join ' ')" -ForegroundColor Cyan
    & python $script @Args
}

exit $LASTEXITCODE
