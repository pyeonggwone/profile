# Delivery Roadmap 설계

## 목적

`epub-translate-v4`를 실제 구현할 때의 단계, 산출물, 완료 기준을 정의한다.

## Phase 0. 설계 고정

### 목표

README와 build 설계 문서를 기준으로 범위와 구조를 확정한다.

### 산출물

- `README.md`
- `build/BUILD.md`
- 각 실행계획 디렉터리의 `DESIGN.md`
- `TODO.md` 초안

### 완료 기준

- 포맷별 adapter 경계가 명확하다.
- 변환 기반 구현이 아니라 native adapter 구현 방향이 유지된다.

## Phase 1. Project Skeleton

### 목표

Node.js 기반 프로젝트 skeleton과 CLI를 만든다.

### 구현 대상

- `package.json`
- `.env.example`
- `run-translate.sh`
- `src/index.mjs`
- `src/pipeline.mjs`
- 기본 `input`, `output`, `work`, `ebook-metadata` 디렉터리

### 완료 기준

- CLI 실행 시 input scan과 summary log가 동작한다.

## Phase 2. Format Detection

### 목표

지원 포맷을 감지하고 adapter로 routing한다.

### 구현 대상

- `src/formats/detect.mjs`
- extension check
- header/signature check
- unsupported handling

### 완료 기준

- `epub`, `azw3`, `mobi`, `kfx` 후보 파일을 구분한다.

## Phase 3. Common Translation Engine

### 목표

포맷과 무관한 segment 번역 엔진을 만든다.

### 구현 대상

- glossary loader
- masker
- TM
- LLM batch caller
- token usage aggregation

### 완료 기준

- mock segment 배열로 번역 결과와 usage를 만들 수 있다.

## Phase 4. EPUB Adapter MVP

### 목표

v3 수준의 EPUB 번역을 v4 adapter 구조에서 재현한다.

### 구현 대상

- EPUB reader
- XHTML text extractor
- EPUB writer
- language metadata update

### 완료 기준

- `.epub` 입력이 `.epub` output으로 번역 저장된다.

## Phase 5. Metadata JSON MVP

### 목표

책별 metadata JSON을 생성한다.

### 구현 대상

- metadata extractor
- word count
- token usage writer
- success/failed/skipped status 저장

### 완료 기준

- 처리한 책마다 `ebook-metadata/{stem}.json`이 생성된다.

## Phase 6. AZW3 MVP

### 목표

AZW3 native 처리의 최소 성공 경로를 만든다.

### 구현 대상

- AZW3 reader 초안
- text payload 추출
- writer 초안
- output validation

### 완료 기준

- 비DRM AZW3 샘플에서 번역 output이 생성된다.

## Phase 7. MOBI MVP

### 목표

MOBI native 처리의 최소 성공 경로를 만든다.

### 구현 대상

- MOBI reader 초안
- text record 추출
- writer 초안
- output validation

### 완료 기준

- 비DRM MOBI 샘플에서 번역 output이 생성된다.

## Phase 8. KFX Investigation MVP

### 목표

KFX 처리 가능 범위를 분석하고 가능한 샘플에서 최소 처리 경로를 만든다.

### 구현 대상

- KFX signature detection
- fragment listing
- text fragment 후보 추출
- 처리 가능/불가 reason 기록

### 완료 기준

- KFX 샘플에 대해 성공 또는 명확한 skip metadata를 생성한다.

## Phase 9. Preservation Hardening

### 목표

각 포맷의 원본 보존 품질을 높인다.

### 구현 대상

- metadata preservation
- navigation/TOC preservation
- resource preservation
- offset/checksum/index 갱신 안정화
- output reopen validation 강화

### 완료 기준

- 포맷별 TODO 항목이 실제 검증 기준으로 전환된다.

## Phase 10. Regression Suite

### 목표

샘플 기반 회귀 테스트와 검증 자동화를 만든다.

### 구현 대상

- fixture tests
- metadata schema tests
- output reopen tests
- known limitation 문서화

### 완료 기준

- 주요 포맷별 MVP 테스트가 반복 실행 가능하다.
