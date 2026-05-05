# pdf-translate-v2 실행 계획서

이 문서는 `pdf-translate-v2` 디렉토리에서 진행할 빌드 작업의 실행 계획만 정의한다. 실제 코드 구현은 포함하지 않는다.

## 1. 목적

| 항목 | 내용 |
|---|---|
| 베이스 기술 | `pdf-translate-v1` 의 PDF 엔진 (Rust crate 9 개 + 직접 구현 PDF 파서/Writer/Incremental Update) |
| 운영 패턴 | `ppt-translate-v4` 의 input/output/work/done + glossary + .env + 배치 진입 스크립트 |
| 실행 환경 | `epub-translate-v5` 의 WSL/Linux + bash + Node.js 20+ |
| 결과물 | 입력 디렉토리에 PDF 를 떨어뜨리면 자동 번역되어 `output/<stem>_<TARGET>.pdf` 생성 + 원본은 `input/done/` 으로 이동 |

## 2. 베이스 분리 원칙

- `pdf-translate-v1` 은 **수정하지 않는다** (epub-v5 가 epup-v3 를 보존한 방식과 동일).
- `pdf-translate-v2` 는 별도 디렉토리로 신규 생성한다.
- v1 의 Rust crate 들은 v2 에서 path dependency 로 참조하거나, 필요한 모듈만 v2 안으로 복사 이식한다 (선택은 Phase 1 에서 확정).

## 3. 운영 모델 차이 흡수

| 영역 | v1 (현재) | v2 (목표) |
|---|---|---|
| 입력 | HTTP 업로드 | `input/` 폴더 watch + CLI |
| 출력 | HTTP 다운로드 | `output/<stem>_<TARGET>.pdf` |
| 처리 후 | 세션 디렉토리 | `input/done/` 로 자동 이동 |
| 언어 | 없음 | `--in-lang en --out-lang kr` |
| 용어집 | 없음 | `glossary.csv` |
| 캐시 | 세션 단위 격리 | 전역 `work/tm.sqlite` |
| LLM | 미연동 | OpenAI / Azure OpenAI batch |
| 진입 | `cargo run` / `npm run dev` | `./run-translate.sh` |

v1 의 웹 서버와 frontend 는 v2 에서는 **선택 모드** 로 분리한다 (CLI 가 1차, 웹은 2차).

## 4. 디렉토리 설계 (목표)

```
pdf-translate-v2/
├── run-translate.sh          # 진입 스크립트 (epub-v5 패턴)
├── package.json              # Node 진입 (CLI 오케스트레이션 + LLM)
├── .env                      # 사용자 (gitignore)
├── .env.example              # 키/경로 기본값
├── glossary.csv              # 용어집
├── README.md                 # 사용 안내
├── INSTALL.md                # 설치/명령 모음 (epub-v5 와 동일 톤)
├── TODO.md                   # 단계별 작업 추적
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PIPELINE.md
│   ├── FILE-runtime-dirs.md
│   ├── FILE-env.md
│   ├── FILE-glossary-csv.md
│   └── FILE-pdf-engine.md    # v1 엔진 사용 방식
├── src/                      # Node 오케스트레이션
│   ├── index.mjs
│   ├── pipeline.mjs
│   ├── pdf/                  # v1 Rust 엔진 호출 어댑터 (FFI 또는 자식 프로세스)
│   ├── translate/            # LLM batch + TM
│   ├── glossary/
│   ├── tm/                   # SQLite TM
│   └── util/
├── crates/                   # v1 엔진 path 의존 또는 이식
│   └── (v1 의 9 crate 중 필요한 것)
├── pdf-engine/               # v1 의 Rust workspace 빌드 산출물 (cdylib 또는 CLI)
├── input/
│   └── done/
├── output/
└── work/
    ├── tm.sqlite
    └── <stem>/
        ├── segments.json
        ├── translated.json
        └── output.pdf
```

## 5. 실행 환경 (WSL/Linux 기준)

| 항목 | 버전 / 비고 |
|---|---|
| OS | Ubuntu 22.04 LTS (WSL2) |
| Shell | bash |
| Node.js | 20+ (`apt install nodejs` 또는 `nvm`) |
| Rust toolchain | `rustup default stable` (1.78+) |
| C 빌드 도구 | `build-essential`, `pkg-config` |
| 선택 시스템 lib | `libopenjp2-7-dev`, `libjbig2dec0-dev` (v1 의 feature flag 활성화 시) |
| 패키지 관리 | npm (epub-v5 와 동일) |
| 스크립트 | `run-translate.sh` (chmod +x 후 실행) |

Windows native PowerShell 패턴(`ppt-translate-v4`)은 v2 에서는 사용하지 않는다 (epub-v5 와 동일하게 WSL/Linux first).

## 6. CLI 인자 설계 (ppt-v4 패턴)

```bash
./run-translate.sh                                # input/ 일괄 처리
./run-translate.sh --in-lang en --out-lang kr
./run-translate.sh --in-lang en --out-lang jp input/sample.pdf
./run-translate.sh extract input/sample.pdf      # 단계별
./run-translate.sh translate work/sample/segments.json --in-lang en --out-lang kr
./run-translate.sh apply input/sample.pdf work/sample/translated.json --out-lang kr
./run-translate.sh tm import legacy.csv
```

언어 코드 표기는 ppt-v4 와 동일: `en`, `kr`, `ch`, `jp` (대소문자 구분 없음).

## 7. 파이프라인 (목표)

```
DETECT   : input/ 의 .pdf 파일 수집 (~$* 임시 파일 제외)
EXTRACT  : v1 의 pdf_reader + pdf_analysis 호출 → 페이지/텍스트 segments JSON 생성
TRANSLATE: TM 조회 → 미스만 LLM batch 호출 → SQLite 저장 → glossary placeholder 처리
APPLY    : v1 의 pdf_incremental + pdf_writer 로 원본 PDF 에 번역 텍스트를 incremental update 로 추가
           (원본 prefix 무손실 보존, EditOperation::AddText 시퀀스로 변환)
DONE     : 성공한 원본 → input/done/ 로 이동 (--keep-input 으로 비활성화 가능)
```

## 8. 단계별 작업 (Phase)

### Phase 0 — 디렉토리 스캐폴드

- [ ] `pdf-translate-v2/` 생성
- [ ] `input/`, `input/done/`, `output/`, `work/`, `docs/`, `src/`, `crates/` 빈 디렉토리 + .gitkeep
- [ ] `.env.example`, `glossary.csv`(헤더만), `README.md`, `INSTALL.md`, `TODO.md` 골격
- [ ] `.gitignore` (`work/`, `input/`, `output/`, `node_modules/`, `.env`, `~$*`)

### Phase 1 — v1 엔진 통합 방식 결정

다음 중 하나를 선택해 PIPELINE 설계에 고정:

- 옵션 A: `crates/` 에 v1 의 9 crate 를 path 의존으로 참조하고 v2 안에 새 binary `pdftr-v2` 생성
- 옵션 B: v1 디렉토리를 그대로 두고 v2 의 `pdf-engine/` 에 v1 의 binary (`pdftr` CLI) 만 빌드 후 자식 프로세스 호출
- 옵션 C: v1 의 핵심 crate 만 v2 로 복사 이식 (분리도 최대, 중복 비용 큼)

권장: **옵션 B** (자식 프로세스). v1 무손실, v2 의 Node 오케스트레이션이 단순. epub-v5 가 Calibre `ebook-convert` 를 자식 프로세스로 호출하는 패턴과 동일.

### Phase 2 — Node 오케스트레이션 뼈대

- [ ] `package.json` 기본 (epub-v5 패턴 복제: commander, dotenv, csv-parse, better-sqlite3, openai)
- [ ] `src/index.mjs` 진입점 + commander CLI 인자
- [ ] `src/pipeline.mjs` DETECT/EXTRACT/TRANSLATE/APPLY/DONE
- [ ] `src/util/lang.mjs` 언어 코드 정규화
- [ ] `src/util/paths.mjs` `<stem>_<TARGET>.pdf` 출력 경로 규칙

### Phase 3 — PDF 엔진 어댑터 (`src/pdf/`)

- [ ] `pdftr-v1` CLI 호출 wrapper (extract/text/edit JSON 파일 인자)
- [ ] `EditOperation` JSON 직렬화 helper
- [ ] segments JSON 스키마 정의 (`page`, `runs[]{x,y,text,font,size}`)

### Phase 4 — Translation Memory (`src/tm/`)

- [ ] `work/tm.sqlite` 스키마 (epub-v5 의 TM 테이블 재사용 가능)
- [ ] `lookup_batch`, `store_batch` 인터페이스
- [ ] `--reset-tm` 옵션

### Phase 5 — Glossary (`src/glossary/`)

- [ ] `glossary.csv` 파서 (epub-v5 의 csv-parse 패턴)
- [ ] placeholder 치환 / 복원

### Phase 6 — LLM batch (`src/translate/`)

- [ ] OpenAI / Azure OpenAI 분기 (epub-v5 와 동일 환경변수)
- [ ] `translateBatch(segments, {sourceLang, targetLang, glossary})`
- [ ] 입출력 토큰 metadata 기록

### Phase 7 — Run script + INSTALL.md

- [ ] `run-translate.sh` (epub-v5 의 init/mkdir 패턴 그대로 + Rust 빌드 단계 추가)
- [ ] `INSTALL.md` (apt 패키지 + cargo build + npm install + 실행 명령만)

### Phase 8 — Smoke test

- [ ] 작은 합성 PDF 1 개 input/ 에 두고 전체 파이프라인 실행
- [ ] 결과 PDF 가 표준 viewer (Linux: `evince`, `xdg-open`) 에서 열리는지 확인
- [ ] `input/done/` 이동 확인
- [ ] `work/tm.sqlite` 에 entry 가 들어가는지 확인

### Phase 9 — 문서화

- [ ] `docs/ARCHITECTURE.md` (전체 흐름 다이어그램)
- [ ] `docs/PIPELINE.md` (DETECT→DONE 단계별)
- [ ] `docs/FILE-runtime-dirs.md` (ppt-v4 의 동일 문서 톤)
- [ ] `docs/FILE-env.md`, `docs/FILE-glossary-csv.md`, `docs/FILE-pdf-engine.md`
- [ ] `README.md` 사용자용
- [ ] `TODO.md` 미해결 항목 (TrueType 임베딩으로 한글 폰트 처리, JBIG2/JPX feature 활성화 등)

## 9. .env 변수 (목표)

epub-v5 와 키 이름을 맞춰서 운영자가 두 프로젝트를 같은 패턴으로 관리할 수 있게 한다.

```
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=

SOURCE_LANG=en
TARGET_LANG=kr
BATCH_SIZE=8
MAX_TOKENS=4096
TEMPERATURE=0

WORK_DIR=work
INPUT_DIR=input
OUTPUT_DIR=output
DONE_DIR=input/done
TM_DB_PATH=work/tm.sqlite
GLOSSARY_PATH=glossary.csv

# pdf 전용
PDF_ENGINE_BIN=pdf-engine/target/release/pdftr
PDF_FONT_PATH=                      # 한글 임베딩용 TrueType 경로 (선택)
PDF_KEEP_ORIGINAL_LANG=false        # 원문 유지 모드
```

## 10. 위험 요소와 완화

| 위험 | 영향 | 완화 |
|---|---|---|
| WSL 에서 system OpenJPEG / jbig2dec 미설치 | JPX/JBIG2 이미지가 raw 로 보존됨 | feature 비활성으로 빌드. 설치 가이드만 INSTALL.md 에 명시 |
| PDF 텍스트 추출 품질이 ToUnicode 없으면 떨어짐 | 번역 누락 / 깨짐 | v1 의 ToUnicode CMap 파서가 이미 통합됨 |
| 한글 표시는 Base14 폰트로 불가 | 출력 PDF 가 깨짐 | `PDF_FONT_PATH` 로 TrueType 임베딩 경로 의무화 |
| LLM 비용 | 큰 PDF 에서 비용 폭증 | TM 강제, BATCH_SIZE 제한, glossary 사전 치환 |
| Linux 서명 확장(EOF, 임시파일) | watcher 가 미완료 파일 잡음 | 안정화 대기 (size 동결 N 초) 후 처리 |

## 11. 완료 정의 (DoD)

- `./run-translate.sh` 한 번으로 input/ 의 모든 PDF 가 번역되어 output/ 에 생성된다.
- 원본은 input/done/ 으로 이동된다.
- 동일 문장은 두 번 호출되지 않는다 (TM hit).
- glossary.csv 의 용어는 번역되지 않고 그대로 유지된다.
- 실패한 PDF 는 input/ 에 남고 work/<stem>/error.json 으로 사유가 기록된다.
- README, INSTALL, TODO, docs 가 갖춰져 있다.

## 12. 본 계획서가 다루지 않는 것

- 실제 소스 코드 작성 (Phase 별 작업이 시작되면 추가됨)
- v1 의 웹 viewer 이식 (v2 의 1차 목표가 아님; 2차 단계로 분리)
- DRM / 암호 PDF 의 자동 우회 (지원 안 함; 사용자 password 인자만 전달)
- AZW3/MOBI/KFX 같은 비-PDF 포맷 (epub-v5 의 영역)

## 13. 다음 단계

이 계획서가 승인되면 Phase 0 (디렉토리 스캐폴드) 부터 순차 진행한다.
