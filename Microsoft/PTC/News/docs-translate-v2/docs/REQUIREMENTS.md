# 요구사항 인덱스

## 프로젝트 목표

`ppt-translate-v4`와 동일한 운영 방식으로 Word docs 파일을 번역한다. Microsoft Word 데스크톱 엔진(COM Automation)을 직접 호출하여 원본 DOC/DOCX를 복사하고, 복사본의 텍스트만 치환해 포맷을 최대한 보존한다.

## 비기능 요구사항

- Windows native 환경 필수
- Microsoft Word 데스크톱 앱 필수
- Python 3.11+
- `uv run --script` 우선
- 입력 원본은 직접 수정하지 않음
- 파일 단위 실패 격리
- TM(SQLite) 사용

## 파일별 역할

| 파일/디렉토리 | 역할 |
|---|---|
| `docs_translate.py` | EXTRACT / TRANSLATE / APPLY / CLI |
| `Run-Translate.ps1` | PowerShell thin wrapper |
| `.env.example` | LLM 및 번역 설정 템플릿 |
| `glossary.csv` | 용어집 및 protected term |
| `input/` | `.docx`, `.doc` 입력 |
| `output/` | 번역 결과 |
| `work/` | 중간 산출물 및 TM |

## 명시적 비대상

- Markdown `.md` 번역
- PDF 번역
- Word 없이 OOXML 직접 조작하는 방식
