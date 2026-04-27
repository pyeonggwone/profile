# `Run-Translate.ps1` — 요구사항 명세

PowerShell 7+ 진입 스크립트. 사용자가 가장 자주 쓰는 단일 파일 실행을 1줄로 줄여주는 thin wrapper.

## 책임

1. PowerShell 7 강제 (`#requires -Version 7`).
2. 스크립트 위치 기준으로 `ppt_translate.py` 경로 자동 해석 (`$PSScriptRoot`).
3. 첫 인자가 `.pptx` 파일이면 자동으로 `run` 서브커맨드 prepend.
4. `uv` 가 PATH 에 있으면 `uv run`, 없으면 `python` fallback.
5. `$LASTEXITCODE` 그대로 propagate.
6. `$ErrorActionPreference = 'Stop'` 으로 cmdlet 실패 시 즉시 throw.

## 비책임 (하지 말아야 할 것)

- 작업 디렉토리(cwd) 변경 금지. 호출자가 `Push-Location` 책임짐 (그래야 `.env`, `work/`, `glossary.csv` 가 의도한 위치에서 해석됨).
- 환경변수 자동 주입 금지 (`OPENAI_API_KEY` 등은 `.env` 가 담당).
- uv 자동 설치 금지.

## 동작 예

```powershell
.\Run-Translate.ps1 input\foo.pptx        # → uv run ppt_translate.py run input\foo.pptx
.\Run-Translate.ps1 extract input\foo.pptx
.\Run-Translate.ps1 run input              # 디렉토리 배치
```

## 인터페이스

```powershell
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)
```

`ValueFromRemainingArguments` 로 PowerShell 의 매개변수 파싱 우회 → typer 가 그대로 받게 함.

## 테스트 체크리스트

- [ ] `.\Run-Translate.ps1` (인자 없음) → typer help 출력
- [ ] `.\Run-Translate.ps1 input\x.pptx` → run 자동 prepend
- [ ] `.\Run-Translate.ps1 tm import legacy.csv` → tm import 그대로 전달
- [ ] uv 미설치 환경에서 python fallback
- [ ] 비-zero exit code propagate
