# Project Foundation 설계

## 목적

프로젝트의 기본 실행 환경, 디렉터리 구조, CLI, 설정 파일의 기준을 정의한다.

## 기준 런타임

초기 구현은 `epup-translate-v3`를 참고해 새 프로젝트로 구성하기 쉽도록 Node.js 기반으로 시작한다.

| 항목 | 기준 |
|---|---|
| Runtime | Node.js 20+ |
| Module format | ESM `.mjs` |
| CLI | `commander` |
| LLM SDK | 공식 `openai` SDK |
| Environment | `.env`, `dotenv` |
| Local DB | SQLite, `better-sqlite3` |
| XML/HTML | `fast-xml-parser`, `parse5` 계열 |

## 기본 디렉터리

```text
epub-translate-v4/
├── README.md
├── TODO.md
├── package.json
├── .env.example
├── glossary.csv
├── run-translate.sh
├── src/
├── input/
│   └── done/
├── output/
├── work/
└── ebook-metadata/
```

## CLI 요구사항

초기 CLI는 다음 동작을 지원한다.

- 기본 실행 시 `input/` 전체 스캔
- 특정 파일 또는 디렉터리 지정 가능
- 지원 포맷만 처리
- 처리 완료 원본은 `input/done/`으로 이동
- 실패 또는 DRM skip 파일은 이동하지 않음
- 결과 요약 로그 출력

## 설정 항목

구현 시 `.env.example`에는 다음 범주를 포함한다.

- OpenAI 또는 Azure OpenAI endpoint/key/model
- source language, target language, target suffix
- batch size
- input/output/work/metadata directory
- DRM skip 정책
- debug log 옵션

## 완료 기준

- 프로젝트 skeleton을 만들 때 필요한 파일과 디렉터리가 확정되어 있다.
- CLI와 환경변수의 최소 범위가 정의되어 있다.
- v3에서 가져올 수 있는 공통 모듈과 새로 만들 모듈의 경계가 분명하다.
