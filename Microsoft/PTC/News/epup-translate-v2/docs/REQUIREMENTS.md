# 요구사항 인덱스

epub-translate-v2 (Linux / AlmaLinux 9) 의 파일별 요구사항 명세.

## 프로젝트 목표 (Why)

`epub-translate-v1` 의 Linux 포팅. 동일한 운영 컨벤션·파이프라인을 유지하되,
PowerShell 진입을 bash 로 교체하고 AlmaLinux 9 환경에서 동작을 보증한다.

## 비기능 요구사항

- **OS**: AlmaLinux 9.x (RHEL 9 계열 호환). 다른 배포판은 best-effort.
- **런타임**: Node.js 20+ (`dnf module install nodejs:20`).
- **네이티브 빌드**: `better-sqlite3` 가 네이티브 모듈이므로 `gcc-c++`, `make`, `python3` 필요.
- **LLM**: `.env` 기반. OpenAI 또는 Azure OpenAI 둘 다 지원 (`AZURE_OPENAI_DEPLOYMENT` 가 설정되면 Azure 우선).
- **재현성**: `temperature=0`, TM 캐시 우선.
- **격리**: 작업 산출물은 모두 `work/<stem>/` 하위. 입력은 변경하지 않고 `input/done/` 으로 이동.
- **에러 정책**: per-file 단위 격리. 한 파일 실패가 배치 전체를 중단시키지 않음.
- **DRM**: `META-INF/encryption.xml` 감지 또는 epub.js 파싱 실패 시 해당 파일 skip + 로그.
- **응답 언어**: 사용자 출력 한국어, 코드/JSON 키 영어.
- **TM 독립**: `work/tm.sqlite` 자체 보유 (다른 프로젝트와 공유 안 함).

## 파일별 요구사항

| 파일/디렉토리 | 역할 |
|---|---|
| `epub_translate.mjs` | EXTRACT / TRANSLATE / APPLY / CLI 단일 파일 |
| `run-translate.sh` | bash thin wrapper. node 미존재 시 에러, node_modules 없으면 `npm install` 자동 |
| `package.json` | 의존성 (epubjs, jszip, cheerio, jsdom, openai, better-sqlite3, dotenv, commander, picocolors) |
| `.env`, `.env.example` | LLM 키 + 번역 설정 |
| `glossary.csv` | 글로벌 용어집 (`term, translation, protected`) |
| `INSTALL.md` | AlmaLinux 9 설치 명령 순서 |
| `input/`, `input/done/`, `output/`, `work/` | 런타임 디렉토리 |

## 번역 단위

- inline 텍스트 노드 1개 = 번역 입력 1건.
- 같은 `<p>` 안에 `<em>foo</em> bar` 가 있으면 `"foo"` 와 `" bar"` 두 건으로 분리 → 서식 100% 보존.
- skip 태그: `script`, `style`, `code`, `pre`, `kbd`, `samp`, `tt`.
- skip 패턴: 공백/숫자/기호만, URL, email.

## 파일별 dict.json

- 형식: `{ "<원문 고유명사>": "<번역>", ... }`
- LLM 응답 schema: `{"translations": [...], "proper_nouns": [{"src": "...", "tgt": "..."}]}`
- 매 batch 후 dict.json 누적 → 다음 batch 의 system prompt 에 "File dictionary" 섹션으로 주입
- 우선순위: glossary.csv > dict.json (LLM 프롬프트에서 glossary 가 위에 위치)

## CLI

```
run <file|dir> [--output PATH] [--no-move-done]
extract <epub>
translate <segments.json>
apply <epub> <translated.json> [--output PATH]
tm import <csv>
```

전역 옵션: `--in-lang en|kr|jp|ch`, `--out-lang en|kr|jp|ch`

첫 인자가 `.epub` 파일/디렉토리이면 자동으로 `run` 으로 라우팅.

## v1 과의 차이

- 진입 스크립트: `Run-Translate.ps1` → `run-translate.sh`
- 폰트 기본값: `맑은 고딕` → `Noto Sans CJK KR` (Linux 표준 한글 폰트, 단 EPUB 출력에 직접 사용하지 않으므로 메타 정보용)
- INSTALL.md 가 dnf/bash 명령으로 작성됨
- 핵심 `.mjs` 코드는 OS 비의존 (그대로 재사용)
