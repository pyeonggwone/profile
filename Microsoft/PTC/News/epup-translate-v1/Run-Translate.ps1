#requires -Version 7

<#
.SYNOPSIS
  epub-translate-v1 진입 스크립트.

.DESCRIPTION
  Node.js 20+ 가 필요. 첫 실행 시 npm install 자동 수행.

.EXAMPLE
  .\Run-Translate.ps1 input.epub
  .\Run-Translate.ps1 input
  .\Run-Translate.ps1 extract input.epub
#>
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'epub_translate.mjs'

if (-not (Test-Path $script)) {
    throw "epub_translate.mjs 를 찾을 수 없음: $script"
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js 20+ 가 필요합니다. https://nodejs.org/"
}

# 의존성 설치 확인
$nodeModules = Join-Path $PSScriptRoot 'node_modules'
if (-not (Test-Path $nodeModules)) {
    Write-Host "[npm install] 최초 의존성 설치 중..." -ForegroundColor Yellow
    Push-Location $PSScriptRoot
    try {
        & npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install 실패" }
    }
    finally {
        Pop-Location
    }
}

Write-Host "[node] $script $($Args -join ' ')" -ForegroundColor Cyan
Push-Location $PSScriptRoot
try {
    & node $script @Args
}
finally {
    Pop-Location
}

exit $LASTEXITCODE
