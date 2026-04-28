# MANUAL — docs-translate-v2

Word COM 기반 DOC/DOCX 번역 도구 운영 매뉴얼입니다.

## 1. 필수 환경

| 항목 | 요구사항 |
|---|---|
| OS | Windows 10/11 native |
| PowerShell | 7+ |
| Python | 3.11+ Windows native |
| Microsoft Word | 데스크톱 앱 설치 필수 |
| uv | 권장 |

## 2. 사전 준비

```powershell
Push-Location "C:\Users\v-kimpy\test\profile\Microsoft\PTC\News\docs-translate-v2"
Copy-Item .env.example .env -ErrorAction SilentlyContinue
notepad .env
Pop-Location
```

`.env` 에 OpenAI 또는 Azure OpenAI 설정을 입력합니다.

## 3. 기본 사용

1. 번역할 `.docx` 또는 `.doc` 파일을 `input\` 에 복사합니다.
2. 실행합니다.

```powershell
Push-Location "C:\Users\v-kimpy\test\profile\Microsoft\PTC\News\docs-translate-v2"
uv run --script docs_translate.py run input -in_lang en -out_lang kr
Pop-Location
```

성공 시:

- 결과: `output\<파일명>_KR.docx`
- 원본: `input\done\` 으로 이동
- 중간 산출물: `work\<파일명>\segments.json`, `translated.json`

원본 이동 없이 테스트하려면:

```powershell
uv run --script docs_translate.py run input --no-move-done
```

## 4. 단계별 실행

```powershell
uv run --script docs_translate.py extract "input\sample.docx"
uv run --script docs_translate.py translate "work\input_sample\segments.json"
uv run --script docs_translate.py apply "input\sample.docx" "work\input_sample\translated.json"
```

## 5. 보존 방식

- Word COM 으로 문서를 열고 `StoryRanges` 의 paragraph 를 순회합니다.
- 출력 파일은 원본을 복사한 뒤 Word COM 으로 텍스트 Range 만 치환합니다.
- 표, 이미지, 섹션, 페이지 설정, 스타일, 머리글/바닥글 등 문서 구조는 Word 엔진이 유지합니다.
- URL, email, 변수, protected glossary term 은 placeholder 로 보호합니다.

## 6. 제한 사항

- `.md` 번역 도구가 아닙니다.
- 복잡한 field code, TOC, cross-reference 문단은 손상 방지를 위해 일부 skip 될 수 있습니다.
- 한 문단 내부의 일부 bold/italic 같은 세부 run formatting 은 Word Range 치환 특성상 단순화될 수 있습니다. 문단/표/섹션/이미지/스타일 중심의 포맷 보존을 목표로 합니다.
