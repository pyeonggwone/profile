# ppt-translate-v4

PowerPoint COM Automation 기반 PPT/PPTX 다국어 번역 도구.
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
uv run --script ppt_translate.py -in_lang en -out_lang kr run input.pptx
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
uv run --script ppt_translate.py -in_lang en -out_lang jp run input.pptx

# 단계별
uv run ppt_translate.py extract input.pptx
uv run ppt_translate.py translate work\input\segments.json -in_lang en -out_lang ch
uv run ppt_translate.py apply input.pptx work\input\translated.json -out_lang ch
uv run ppt_translate.py tm import legacy.csv
```

`-in_lang`/`--in-lang`, `-out_lang`/`--out-lang` 은 대소문자 구분 없이 `en`, `kr`, `ch`, `jp` 중 하나를 사용한다. 명시하지 않으면 기본값은 `-in_lang en`, `-out_lang kr` 이다. 기존 `-lang` 은 호환용으로 `-out_lang` 과 동일하게 동작한다.

## 파이프라인

```
EXTRACT  : PowerPoint COM 으로 Slide.Shapes 순회 → TextRange 텍스트 수집
TRANSLATE: TM 조회 → 미스만 LLM 배치 호출 → SQLite 저장
APPLY    : 원본 PPTX 복사 → COM 으로 동일 Shape 의 TextRange.Text 만 교체
           (Font.Name 만 한글 폰트로 교체, 다른 서식 유지)
```

## 디렉토리

```
ppt-translate-v4/
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
