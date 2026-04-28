# docs-translate-v1

Markdown 문서를 구조 보존 방식으로 번역하는 도구입니다. `ppt-translate-v4`의 EXTRACT / TRANSLATE / APPLY 파이프라인을 문서 번역에 맞게 옮겼습니다.

## 핵심 원칙

- 원본 `.md` 파일은 직접 수정하지 않고 `output/` 에 결과를 생성
- fenced code block, inline code, URL, template variable, HTML tag, protected glossary term 보존
- Translation Memory(SQLite) 로 동일 문장 재번역 방지
- `uv run --script` 기반 단일 Python 파일 실행

## 빠른 시작

```powershell
Copy-Item .env.example .env
# .env 편집: OPENAI_API_KEY 또는 AZURE_OPENAI_* 설정
uv run --script docs_translate.py run input -in_lang en -out_lang kr
```

PowerShell wrapper:

```powershell
.\Run-Translate.ps1 run input
.\Run-Translate.ps1 input\sample.md
```

## 명령

```powershell
uv run --script docs_translate.py extract input\sample.md
uv run --script docs_translate.py translate work\input_sample\segments.json
uv run --script docs_translate.py apply input\sample.md work\input_sample\translated.json
uv run --script docs_translate.py tm import legacy.csv
```

## 런타임 디렉토리

```text
input/          # 번역할 .md 파일
input/done/     # 성공 시 이동되는 원본
output/         # 번역 결과
work/           # segments.json, translated.json, tm.sqlite
```
