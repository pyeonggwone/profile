
# MANUAL — ppt-translate-v4

PowerPoint COM 기반 PPT/PPTX 다국어 번역 도구의 운영 매뉴얼.
uv run --script ppt_translate.py -in_lang en -out_lang kr run input
---

## 1. 사전 준비 (최초 1회)

### 1.1 필수 환경

| 항목 | 확인 명령 / 비고 |
|---|---|
| Windows 10/11 | `winver` |
| PowerShell 7+ | `pwsh --version` |
| Python 3.11+ (Windows native) | `python --version` (WSL 불가) |
| PowerPoint 데스크톱 앱 | 설치 필수 (Microsoft 365 권장) |
| uv | `uv --version` |

### 1.2 uv 설치

```pwsh
winget install astral-sh.uv
```

설치 후 새 PowerShell 창을 열거나 `Path` 갱신:

```pwsh
$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe;$env:Path"
```

### 1.3 프로젝트 위치

```
C:\Users\v-kimpy\test\profile\Microsoft\PTC\News\ppt-translate-v4\
```

### 1.4 환경변수 설정 (`.env`)

```pwsh
Push-Location "C:\Users\v-kimpy\test\profile\Microsoft\PTC\News\ppt-translate-v4"
Copy-Item .env.example .env -ErrorAction SilentlyContinue
notepad .env
Pop-Location
```

`.env` 에 아래 중 하나 선택해 입력:

**A. Azure OpenAI (권장)**
```
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=<deployment-name>
```

**B. OpenAI**
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 1.5 디렉토리 구조

```
ppt-translate-v4/
├── input/          # 번역할 .pptx 를 여기에 둠
│   └── done/       # 번역 완료된 원본이 자동 이동되는 곳
├── output/         # 번역된 결과물 _KR.pptx
├── work/           # 중간 산출물 (segments.json, translated.json, tm.sqlite)
├── glossary.csv    # 용어집 (원하면 편집)
├── .env            # API 키
└── ppt_translate.py
```

---

## 2. 사용법

### 2.1 기본 사용 — 한 줄로 끝

1. 번역할 PPTX 를 `input\` 에 복사 (여러 개 가능)
2. PowerShell 7 에서 실행:

**A. 단일 파일**
```pwsh
Push-Location "C:\Users\v-kimpy\test\profile\Microsoft\PTC\News\ppt-translate-v4"
$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe;$env:Path"

uv run --script ppt_translate.py -in_lang en -out_lang kr run "input\<파일명>.pptx"

Pop-Location
```

**B. `input\` 안의 모든 .pptx / .ppt 일괄 처리** ⭐
```pwsh
Push-Location "C:\Users\v-kimpy\test\profile\Microsoft\PTC\News\ppt-translate-v4"
$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe;$env:Path"

uv run --script ppt_translate.py -in_lang en -out_lang kr run input

Pop-Location
```

자동 처리 (각 파일마다):
- EXTRACT → TRANSLATE → APPLY → 결과는 `output\<파일명>_KR.pptx`
- 잔여 영문 자동 검증 및 재번역 (최대 2회)
- 성공 시 원본 → `input\done\` 으로 즉시 이동 후 다음 파일 처리
- 한 파일 실패해도 다음 파일 계속 진행, 종료 시 실패 목록 출력

### 2.2 옵션

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `-in_lang, --in-lang en/kr/ch/jp` | `en` | 입력 언어. 대소문자 구분 없음 |
| `-out_lang, --out-lang en/kr/ch/jp` | `kr` | 출력 언어. 대소문자 구분 없음 |
| `-lang, --lang en/kr/ch/jp` | `kr` | 호환용 출력 언어 옵션 |
| `--output PATH` | `<원본>_KR.pptx` | 출력 경로 |
| `--no-verify` | (verify on) | 잔여 영문 자동 재번역 비활성화 |
| `--no-move-done` | (move on) | 입력 파일을 `done/` 으로 이동하지 않음 |

예:
```pwsh
uv run --script ppt_translate.py -in_lang en -out_lang jp run "input\foo.pptx" --no-move-done
```

### 2.3 단계별 실행

```pwsh
# 추출만
uv run --script ppt_translate.py extract "input\foo.pptx" --out "work\foo\segments.json"

# 번역만
uv run --script ppt_translate.py translate "work\foo\segments.json" --out "work\foo\translated.json" -in_lang en -out_lang ch

# 적용만
uv run --script ppt_translate.py apply "input\foo.pptx" "work\foo\translated.json" --out "output\foo_CH.pptx" -out_lang ch
```

### 2.4 Translation Memory 가져오기

기존 번역 CSV (`source,target` 형식) 를 TM 에 사전 적재:

```pwsh
uv run --script ppt_translate.py tm import legacy_translations.csv
```

---

## 3. 용어집 편집 (`glossary.csv`)

| 컬럼 | 설명 |
|---|---|
| `term` | 영문 원문 |
| `translation` | 한글 번역 (또는 동일 영문 유지) |
| `protected` | `true` 면 번역하지 않고 원문 그대로 둠 |

예:
```csv
term,translation,protected
Azure,Azure,true
Database Administrator,DBA,false
high availability,고가용성,false
```

**팁**: 제목/소제목이 길어져 슬라이드 디자인이 깨질 때, 긴 용어를 짧은 약어로 등록 (`Artificial Intelligence` → `AI`).

---

## 4. 디자인 보존 기능

- **제목·부제 자동 폰트 축소**: `TextFrame.AutoSize = ppAutoSizeTextToFitShape` 강제 적용
- **길이 제약 번역**: LLM 에 제목은 영문 길이 ×1.0, 부제는 ×1.1 한글 글자수 상한 전달
- **한글 폰트 통일**: 기본 `맑은 고딕` (`.env` 의 `KR_FONT` 로 변경 가능)
- **SmartArt / 표 / 그룹 / 노트** 모두 in-place 치환

---

## 5. 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `pywin32 가 필요합니다` | WSL 에서 실행 중. **Windows native pwsh** 에서 실행 |
| `Permission denied` 출력 파일 | PowerPoint 에서 출력물이 열려있음. 닫고 재실행 |
| 출력에 영문 그대로 남음 | `--verify` (기본) 활성 상태 확인 / TM 캐시 삭제: `Remove-Item work\tm.sqlite` |
| 동일 문장이 매번 동일하게 번역됨 (재시도해도 동일) | TM 캐시 사용 중. 삭제 후 재실행 |
| 제목이 박스 밖으로 넘침 | `glossary.csv` 에 짧은 약어 등록, 또는 PowerPoint 에서 직접 수정 |
| `uv` 명령 없음 | 1.2 절 재확인. `Path` 갱신 |
| 추출 0건 | 원본 PPTX 가 비어있거나 모든 텍스트가 이미지화됨 |

### 5.1 캐시 초기화 후 재번역

```pwsh
Push-Location "C:\Users\v-kimpy\test\profile\Microsoft\PTC\News\ppt-translate-v4"
Remove-Item work\tm.sqlite -ErrorAction SilentlyContinue
Remove-Item -Recurse "work\<파일명>" -ErrorAction SilentlyContinue
# done/ 에서 input/ 으로 원본 복귀
Move-Item "input\done\<파일명>.pptx" "input\" -Force
uv run --script ppt_translate.py run "input\<파일명>.pptx"
Pop-Location
```

### 5.2 PowerPoint 프로세스 정리

번역 중 오류로 PowerPoint COM 프로세스가 남았을 때:

```pwsh
Get-Process POWERPNT -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

## 6. 워크플로우 예시

### 6.1 신규 PPTX 번역

```pwsh
# 1. 파일 배치
Copy-Item "C:\downloads\foo.pptx" "C:\Users\v-kimpy\test\profile\Microsoft\PTC\News\ppt-translate-v4\input\"

# 2. 실행
Push-Location "C:\Users\v-kimpy\test\profile\Microsoft\PTC\News\ppt-translate-v4"
$env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe;$env:Path"
uv run --script ppt_translate.py run "input\foo.pptx"
Pop-Location

# 3. 결과 확인
# output\foo_KR.pptx
```

### 6.2 동일 슬라이드 일부 텍스트만 다시 번역

1. `glossary.csv` 또는 프롬프트 수정
2. `work\<파일명>\` 디렉토리 삭제
3. `tm.sqlite` 에서 해당 문장 삭제 또는 전체 캐시 삭제
4. 6.1 절 재실행
