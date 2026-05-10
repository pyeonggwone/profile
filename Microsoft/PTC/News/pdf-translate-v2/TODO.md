# TODO — pdf-translate-v2

PLAN.md 의 Phase 별 진척과 미해결 항목 추적.

## Phase 0 — 디렉토리 스캐폴드

- [x] `pdf-translate-v2/` 생성
- [x] `input/`, `input/done/`, `output/`, `work/`, `docs/`, `src/`, `crates/` 빈 디렉토리 + `.gitkeep`
- [x] `.env.example`, `glossary.csv`(헤더만), `README.md`, `INSTALL.md`, `TODO.md` 골격
- [x] `.gitignore`

## Phase 1 — v1 엔진 통합 방식

- [x] **옵션 B 채택**: `pdf-translate-v1` 의 `pdftr` CLI 를 자식 프로세스로 호출
- [x] PDF_ENGINE_BIN 자동 탐색 순서 정의 (`.env` → `pdf-engine/target/release/pdftr` → `../pdf-translate-v1/target/release/pdftr` → `$PATH`)

## Phase 2 — Node 오케스트레이션 뼈대

- [x] `package.json` (commander, dotenv, csv-parse, better-sqlite3, openai)
- [x] `src/index.mjs` 진입점 + commander CLI
- [x] `src/pipeline.mjs` DETECT/EXTRACT/TRANSLATE/APPLY/DONE
- [x] `src/util/lang.mjs` 언어 코드 정규화 (en/kr/ch/jp)
- [x] `src/util/paths.mjs` `<stem>_<TARGET>.pdf` 출력 경로 규칙
- [x] `src/util/env.mjs`, `src/util/log.mjs`

## Phase 3 — PDF 엔진 어댑터 (`src/pdf/`)

- [x] `src/pdf/engine.mjs` `pdftr` CLI wrapper (extract/text/edit JSON 인자)
- [x] `src/pdf/edits.mjs` `EditOperation` JSON 직렬화 helper
- [x] segments JSON 스키마 정의 (`page`, `runs[]{x,y,text,font,size}`)

## Phase 4 — Translation Memory (`src/tm/`)

- [x] `src/tm/store.mjs` `work/tm.sqlite` 스키마 (epub-v5 와 동일)
- [x] `tmGet`, `tmPut`, `tmDelete`
- [x] `--reset-tm` 옵션

## Phase 5 — Glossary (`src/glossary/`)

- [x] `src/glossary/loader.mjs` glossary.csv 파서
- [x] `src/glossary/masker.mjs` placeholder 치환 / 복원

## Phase 6 — LLM batch (`src/translate/`)

- [x] `src/translate/llm.mjs` OpenAI / Azure OpenAI 분기
- [x] `translateBatch(segments, cfg, glossaryRows)`
- [x] 입출력 토큰 metadata 기록

## Phase 7 — Run script + INSTALL.md

- [x] `run-translate.sh` (epub-v5 init/mkdir 패턴)
- [x] `INSTALL.md`

## Phase 8 — Smoke test

- [ ] 작은 합성 PDF 1 개 input/ 에 두고 전체 파이프라인 실행 (사용자 환경에서 수행)
- [ ] 결과 PDF 가 standard viewer 에서 열리는지 확인
- [ ] `input/done/` 이동 확인
- [ ] `work/tm.sqlite` 에 entry 가 들어가는지 확인

## Phase 9 — 문서화

- [x] `docs/ARCHITECTURE.md`
- [x] `docs/PIPELINE.md`
- [x] `docs/FILE-runtime-dirs.md`
- [x] `docs/FILE-env.md`
- [x] `docs/FILE-glossary-csv.md`
- [x] `docs/FILE-pdf-engine.md`

## 미해결 / 향후

- [ ] 한글 출력 시 v1 엔진의 TrueType 임베딩 경로 노출. 현재 v1 의 `EditOperation::AddText` 는 Base14 폰트만 받으므로, 한글 PDF 출력이 깨질 수 있다. v1 의 `pdf_writer/font.rs` 의 subset 임베딩 API 가 CLI 표면으로 올라와야 함.
- [ ] JPX / JBIG2 디코드를 위한 v1 feature flag 활성화 가이드
- [ ] LLM 응답 placeholder 누락/순서 변경 시 segment 단위 재시도 (현재 batch 단위 fallback)
- [ ] 큰 PDF 의 page 단위 chunk 처리 (메모리 / 토큰 분할)
- [ ] watcher 모드 (`--watch`): 안정화 대기 후 자동 처리
- [ ] 세션 단위 비용 리포트 (input/output/total token) JSON 출력
- [ ] EXTRACT 결과의 동일 라인 좌표 클러스터링 (현재 run 단위, 의미 단위 합치기 필요)
- [ ] 원문 보존 모드 (`PDF_KEEP_ORIGINAL_LANG=true`) 의 layout: 번역문을 어디에 넣을지 정책 필요
