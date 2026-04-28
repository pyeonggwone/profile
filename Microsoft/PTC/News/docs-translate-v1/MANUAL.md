# MANUAL — docs-translate-v1

Markdown docs 번역 도구 운영 매뉴얼입니다.

## 1. 준비

```powershell
Push-Location "C:\Users\v-kimpy\test\profile\Microsoft\PTC\News\docs-translate-v1"
Copy-Item .env.example .env -ErrorAction SilentlyContinue
notepad .env
Pop-Location
```

`.env` 에 OpenAI 또는 Azure OpenAI 설정을 입력합니다.

## 2. 사용법

### 단일 파일

```powershell
uv run --script docs_translate.py run "input\sample.md" -in_lang en -out_lang kr
```

### 디렉토리 배치

```powershell
uv run --script docs_translate.py run input -in_lang en -out_lang kr
```

성공한 원본 파일은 `input/done/` 으로 이동됩니다. 이동을 막으려면 `--no-move-done` 을 사용합니다.

## 3. 단계별 실행

```powershell
uv run --script docs_translate.py extract "input\sample.md"
uv run --script docs_translate.py translate "work\input_sample\segments.json"
uv run --script docs_translate.py apply "input\sample.md" "work\input_sample\translated.json"
```

## 4. 보존 규칙

- fenced code block 은 번역 대상에서 제외
- inline code, URL, Markdown link URL, image path, Liquid/Jinja 변수, `${VAR}`, HTML tag 는 placeholder 로 보호
- link text, heading, paragraph, list item, table cell, blockquote 는 번역 대상
- `glossary.csv` 의 `protected=true` term 은 placeholder 로 보호

## 5. 캐시 초기화

```powershell
Remove-Item work\tm.sqlite -ErrorAction SilentlyContinue
Remove-Item -Recurse work\input_sample -ErrorAction SilentlyContinue
```
