# 요구사항 인덱스

## 프로젝트 목표

Markdown docs 파일을 구조 보존 방식으로 번역한다. 코드, URL, 변수, HTML tag, protected glossary term 은 보존하고, heading/paragraph/list/table/link text 중심으로 번역한다.

## 비기능 요구사항

- Python 3.11+
- `uv run --script` 우선, `python` fallback 가능
- 동일 입력은 TM 캐시 우선
- 한 파일 실패가 배치 전체를 중단하지 않음
- 입력 원본은 직접 수정하지 않음

## 파일별 역할

| 파일/디렉토리 | 역할 |
|---|---|
| `docs_translate.py` | EXTRACT / TRANSLATE / APPLY / CLI |
| `Run-Translate.ps1` | PowerShell thin wrapper |
| `.env.example` | LLM 및 번역 설정 템플릿 |
| `glossary.csv` | 용어집 및 protected term |
| `input/` | 사용자 입력 |
| `output/` | 번역 결과 |
| `work/` | 중간 산출물 및 TM |

## 구현 우선순위

1. `.md` 단일 파일 번역
2. 디렉토리 배치 번역
3. 보호 토큰 검증
4. TM/glossary
5. Markdown 요소별 APPLY 안정화
6. MDX/HTML/frontmatter value 확장
