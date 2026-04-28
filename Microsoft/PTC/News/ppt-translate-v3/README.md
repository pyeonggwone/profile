# ppt-translate-v3

PowerPoint COM Automation 기반 PPTX 영문→한국어 번역 도구.
**python-pptx / lxml 미사용**, 100% PowerPoint 엔진 사용.

## 핵심 원칙

- **PowerPoint 엔진 직접 호출** (`pywin32`) — Microsoft 가 만든 그대로
- **In-place 텍스트 치환** — Shape/이미지/SmartArt/차트/애니메이션/마스터 100% 보존
- **Windows native PowerShell + uv** — 가상환경/컨테이너/빌드 없음
- **Translation Memory (SQLite)** — 동일 문장 재번역 안 함

## 환경 요구사항

| 항목 | 버전 |
|------|------|
| OS | Windows 10/11 |
| PowerShell | 7+ (UTF-8 기본) |
| Python | 3.11+ (Windows native, WSL 아님) |
| PowerPoint 데스크톱 | 설치 필수 (Microsoft 365 / 2019 / 2021) |
| uv | 권장 (`winget install astral-sh.uv`) |

## 빠른 시작

```powershell
# 1. uv 설치 (이미 있으면 스킵)
winget install astral-sh.uv

# 2. 환경변수 설정
Copy-Item .env.example .env
# .env 편집: OPENAI_API_KEY 또는 AZURE_OPENAI_*

# 3. 실행 (uv 가 의존성 자동 설치)
uv run ppt_translate.py run input.pptx
```

또는 일반 venv:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ppt_translate.py run input.pptx
```

## 명령

```powershell
# 전체 파이프라인
.\Run-Translate.ps1 input.pptx

# 단계별
uv run ppt_translate.py extract input.pptx
uv run ppt_translate.py translate work\input\segments.json
uv run ppt_translate.py apply input.pptx work\input\translated.json
uv run ppt_translate.py tm import legacy.csv
```

## 파이프라인

```
EXTRACT  : PowerPoint COM 으로 Slide.Shapes 순회 → TextRange 텍스트 수집
TRANSLATE: TM 조회 → 미스만 LLM 배치 호출 → SQLite 저장
APPLY    : 원본 PPTX 복사 → COM 으로 동일 Shape 의 TextRange.Text 만 교체
           (Font.Name 만 한글 폰트로 교체, 다른 서식 유지)
```

## 디렉토리

```
ppt-translate-v3/
├── ppt_translate.py        # 단일 파일 (PEP 723 메타데이터)
├── Run-Translate.ps1       # PowerShell 진입 스크립트
├── requirements.txt        # uv 미사용 시
├── glossary.csv            # 용어집
├── .env.example
├── README.md
├── docs/
│   └── ARCHITECTURE.md
└── work/                   # 런타임 산출물
    └── tm.sqlite
```
