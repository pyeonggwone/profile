# docs-translate-v2

Microsoft Word COM Automation 기반 DOC/DOCX 번역 도구입니다.
`ppt-translate-v4`와 같은 방식으로 Office 데스크톱 앱을 직접 열고, 원본 파일을 복사한 뒤 텍스트 Range 만 in-place 치환합니다.

## 핵심 원칙

- **Markdown 번역 도구가 아님** — `.docx`, `.doc` 전용
- **Word 엔진 직접 호출** (`pywin32`) — Microsoft Word 가 읽고 저장하는 파일 사용
- **원본 복사본에 in-place 텍스트 치환** — 표, 이미지, 섹션, 스타일, 머리글/바닥글 등 문서 구조 보존
- **Translation Memory(SQLite)** — 동일 문장 재번역 방지
- **Windows native PowerShell + uv** — Word 데스크톱 COM 호출 필요

## 빠른 시작

```powershell
Copy-Item .env.example .env
# .env 편집: OPENAI_API_KEY 또는 AZURE_OPENAI_* 설정
uv run --script docs_translate.py run input -in_lang en -out_lang kr
```

## 명령

```powershell
uv run --script docs_translate.py run input
uv run --script docs_translate.py run "input\sample.docx" --no-move-done
uv run --script docs_translate.py extract "input\sample.docx"
uv run --script docs_translate.py translate "work\input_sample\segments.json"
uv run --script docs_translate.py apply "input\sample.docx" "work\input_sample\translated.json"
uv run --script docs_translate.py tm import legacy.csv
```

## 디렉토리

```text
docs-translate-v2/
├── docs_translate.py
├── Run-Translate.ps1
├── requirements.txt
├── glossary.csv
├── .env.example
├── input/
│   └── done/
├── output/
└── work/
    └── tm.sqlite
```
