# TODO

v9 프로젝트에 문서, `.env`, 디렉토리 구조, crate README로 선언되어 있으나 아직 구현이 없거나 부분 구현 상태인 항목이다.

## 1. OpenAI/Azure OpenAI

- [x] Azure OpenAI provider 구현
  - 선언 위치: `.env`의 `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`
  - 현재 상태: OpenAI public endpoint와 Azure OpenAI endpoint/deployment/api-version 기반 호출을 provider 설정으로 선택한다.
  - 필요 구현: Azure OpenAI endpoint/deployment/api-version 기반 URL 생성, Azure key header 처리, provider 선택 로직 추가.

- [x] OpenAI chunk retry/backoff 구현
  - 선언 위치: chunk 기반 번역 구조와 degraded fallback 동작
  - 현재 상태: `OPENAI_CHUNK_SIZE`, `OPENAI_RETRY_MAX`, `OPENAI_RETRY_BASE_MS`, `OPENAI_TIMEOUT_SECS` 기준으로 chunk별 retry/backoff와 report를 생성한다.
  - 필요 구현: HTTP 429/5xx retry, chunk별 retry count, retry report 저장.

- [x] 번역 응답 completeness 검증 구현
  - 선언 위치: `docs/validation/README.md`의 `translation id 매칭 확인`
  - 현재 상태: 요청 id와 응답 id set을 비교하고 missing/unknown/duplicate id를 `translation-report.json` 및 chunk report에 기록한다.
  - 필요 구현: 요청 id와 응답 id set 비교, 누락 id fallback 또는 실패 처리, `translation-report.json` 저장.

## 2. CSV/용어 일관성

- [x] term-application-report.json 구현
  - 선언 위치: `docs/terms/README.md`
  - 현재 상태: `term-application-report.json`에 `fixed`/`preserve` 위반 항목을 기록한다.
  - 필요 구현: 번역 결과에서 `fixed`/`preserve` 용어 적용 여부 검사, 위반 항목 report 저장.

- [x] preserve/fixed 용어 강제 후처리 구현
  - 선언 위치: `docs/terms/README.md`, OpenAI prompt의 `Preserve terms`, `Fixed translations`
  - 현재 상태: `TERM_ENFORCEMENT` 기준으로 `fixed` 용어 후처리와 `preserve`/`fixed` 검증을 수행한다. `preserve`는 안전한 자동 복원이 불가능하면 report/strict 실패로 처리한다.
  - 필요 구현: `mode=preserve` 원문 유지, `mode=fixed` 지정 번역어 적용, 충돌/부분 매칭 처리.

- [x] term memory SQLite 구현
  - 선언 위치: `README.md`의 `terms.sqlite`, `docs/database/README.md`의 `term memory`
  - 현재 상태: `TERMS_DB_PATH` 또는 기본 `work/terms.sqlite`에 term memory table을 생성하고 job terms를 저장한다.
  - 필요 구현: job 간 공유 term memory table, CSV import/export, job term merge 우선순위 정의.

## 3. SQLite 상태/Translation Memory

- [x] `TM_DB_PATH` 별도 DB 적용
  - 선언 위치: `.env`의 `TM_DB_PATH=work/tm.sqlite`, `README.md`의 `tm.sqlite`
  - 현재 상태: Translation Memory 조회/저장은 `TM_DB_PATH` 기준 DB를 사용한다.
  - 필요 구현: `TM_DB_PATH` 기준 별도 TM DB 또는 문서/환경값 정리.

- [x] artifact index 기록 연결
  - 선언 위치: `src/pipeline/README.md`, `src/state_store/README.md`의 artifact index
  - 현재 상태: pipeline step별 주요 산출물을 artifact index에 기록한다.
  - 필요 구현: 각 산출물 생성 시 artifact kind/path 기록.

- [x] validation event index 구현
  - 선언 위치: `docs/database/README.md`, `src/state_store/README.md`
  - 현재 상태: `validation_events` table을 생성하고 encode/rebuild/qpdf/raw extraction issue를 index로 기록한다.
  - 필요 구현: validation_events table, issue count/status/path 저장.

- [x] resume cursor 구현
  - 선언 위치: `src/state_store/README.md`
  - 현재 상태: `resume <job>` command가 step별 기존 산출물을 확인하고 이미 생성된 step을 skip한다.
  - 필요 구현: `resume` command 또는 step skip 로직, 기존 artifact 신뢰성 검증.

## 4. 입력/출력 디렉토리 운영

- [x] `INPUT_DIR`, `OUTPUT_DIR`, `WORK_DIR` 적용
  - 선언 위치: `.env`
  - 현재 상태: env 값 기준 path를 구성하며 상대 경로는 v9 root 기준으로 처리한다.
  - 필요 구현: env 값 기준 path 구성, 상대 경로는 v9 root 기준 처리.

- [x] input/ready, input/done, input/failed workflow 구현
  - 선언 위치: `input/ready/README.md`, `input/done/README.md`, `input/failed/README.md`
  - 현재 상태: `input/ready`가 있으면 ready queue를 우선 처리하고 `INPUT_ARCHIVE_MODE=copy|move|off`에 따라 done/failed로 보낸다.
  - 필요 구현: ready queue 처리, 성공 PDF done 이동, 실패 PDF failed 이동 또는 copy 정책.

- [x] output/rejected, output/reports publish 구현
  - 선언 위치: `output/rejected/README.md`, `output/reports/README.md`
  - 현재 상태: degraded/failed 결과는 `output/rejected`, report bundle은 `output/reports/<job>`에 publish한다.
  - 필요 구현: 실패/rejected PDF 분리, 최종 report bundle output/reports 복사.

- [x] `KEEP_WORK` 적용
  - 선언 위치: `.env`
  - 현재 상태: `KEEP_WORK=false`이고 translated 성공 결과일 때 source/qpdf/pdf 중간 디렉토리를 정리한다.
  - 필요 구현: `KEEP_WORK=false`일 때 성공 job의 중간 파일 정리 정책.

## 5. qpdf/검증

- [x] qpdf 설치/존재 사전 진단 command 구현
  - 선언 위치: README의 project-local qpdf 정책, tools/qpdf README 구조
  - 현재 상태: `doctor` command가 project-local qpdf 후보 경로와 실행 가능 여부를 사전 진단한다.
  - 필요 구현: `doctor` 또는 `check-tools` command로 후보 경로, 권한, 실행 가능 여부를 사전 출력.

- [x] raw JSON completeness 검증 구현
  - 선언 위치: `docs/validation/README.md`
  - 현재 상태: `raw-completeness-report.json`에 page/content/run count, decoded/font/ToUnicode 누락 count를 기록한다.
  - 필요 구현: page/content/run count, decoded text 누락, font/toUnicode 누락 report.

- [x] replacementEncoded 생성 검증 report 분리
  - 선언 위치: `docs/validation/README.md`, `work/reports/encode/README.md`
  - 현재 상태: `encode-report.json`에 method별 count와 실패 issue를 분리 저장한다.
  - 필요 구현: `encode-report.json` 생성, 실패 원인별 count 저장.

- [x] publish gate 엄격화
  - 선언 위치: `docs/validation/README.md`의 `검증 실패 PDF는 output으로 publish하지 않는다`
  - 현재 상태: degraded/fallback/failed 결과는 `output/rejected`로 분리하고 validated에는 통과 결과만 둔다.
  - 필요 구현: `output/validated`와 `output/rejected` 분리, degraded fallback은 rejected로 이동.

## 6. PDF text state/CMap/ToUnicode

- [x] 실제 ToUnicode CMap parsing 구현
  - 선언 위치: README의 `ToUnicode CMap parsing`, `CMap/ToUnicode parser`
  - 현재 상태: font resource의 ToUnicode stream을 읽어 `bfchar`/`bfrange` parser로 decode에 사용한다.
  - 필요 구현: PDF font resource의 ToUnicode stream 탐색, bfchar/bfrange parsing, CID to Unicode mapping.

- [x] font resource 상세 추출 구현
  - 선언 위치: README raw JSON 예시의 `fontObjectRef`, `subtype`, `baseFont`, `encoding`, `toUnicodeRef`
  - 현재 상태: page resource `/Font` dictionary에서 object ref, subtype, baseFont, encoding, ToUnicode ref를 추출한다.
  - 필요 구현: page resources font dictionary lookup, object ref/subtype/baseFont/encoding/toUnicodeRef 저장.

- [x] qpdf reference 기반 extraction 보강
  - 선언 위치: README와 pipeline 문서의 `source.pdf, source.qdf.pdf` 기준 추출
  - 현재 상태: raw extraction은 원본 PDF byte range를 기준으로 유지하고 `qdf-reference-report.json`에 qdf path와 content stream xref 목록을 debug/reference artifact로 저장한다.
  - 필요 구현: qdf reference와 원본 stream mapping, object/debug reference 저장.

- [x] complex text operators 상태 갱신 구현
  - 선언 위치: README 추출 대상 `Td`, `TD`, `T*`, `'`, `"`, `q`, `Q`, `cm`
  - 현재 상태: `q`, `Q`, `Td`, `TD`, `T*`와 quote text operator 기본 처리를 추가했다. `cm` 누적 CTM은 아직 제한적이다.
  - 필요 구현: text/graphics state stack, line movement, quote operators의 word/char spacing 처리.

- [x] textBlockRange 구현
  - 선언 위치: raw JSON schema의 `textBlockRange`
  - 현재 상태: `BT`/`ET` token byte range를 text run에 저장한다.
  - 필요 구현: BT/ET block byte range 추적 저장.

- [x] matrix 기반 layout 정보 계산 구현
  - 선언 위치: README의 `matrix 기반 layout 정보 계산`
  - 현재 상태: text matrix, font size, horizontal scaling 기반 `estimatedWidth`와 추정 bbox를 저장한다.
  - 필요 구현: glyph advance 추정, font size/matrix 기반 bbox, line/page 좌표 저장.

- [x] non-ASCII replacement encoding 구현
  - 선언 위치: 기존 font/CMap 기준 replacementEncoded 생성
  - 현재 상태: 기존 ASCII/literal/TJ 방식 실패 시 font `ToUnicode` 역매핑으로 `replacementEncoded` 생성을 시도하고, 역매핑이 없으면 encode failed 처리한다.
  - 필요 구현: ToUnicode 역매핑, CID/font encoding mapping, 불가능 시 font subset/embed 전략 여부 결정.

## 7. Rebuild/PDF 복원

- [x] 부분 실패 rebuild 산출물 정책 확정
  - 선언 위치: rebuild는 text payload만 교체하고 실패 report 기록
  - 현재 상태: `report.ok=false`이면 validated로 publish하지 않고 degraded mode에서는 source copy fallback을 `output/rejected`로 보낸다.
  - 필요 구현: 부분 성공 PDF 저장 여부, rejected 처리, 실패 run만 원본 유지하는 정책 결정.

- [x] replacement 후 PDF 구조 영향 검증 구현
  - 선언 위치: validation/rebuild report 설계
  - 현재 상태: `structure-report.json`에서 source/rebuilt page count와 hash를 기록하고 qpdf validation report와 함께 publish한다.
  - 필요 구현: stream filter 제거 영향, object length/xref 저장 결과 검증, qpdf normalize 비교.

- [x] output hash/result classification 개선
  - 선언 위치: run-summary/degraded 구분
  - 현재 상태: `classification`, `fallbackUsed`, changed/unchanged count, validated/rejected path를 `run-summary.json`에 저장한다.
  - 필요 구현: translated text count, rebuilt changed bytes, fallback copy 여부를 별도 필드로 저장.

## 8. OCR/Font/Rendering 설정

- [x] OCR 구현
  - 선언 위치: `.env`의 `OCR_MODE`, `AZURE_VISION_ENDPOINT`, `AZURE_VISION_KEY`
  - 현재 상태: `OCR_MODE=azure|force`이면 project-local `pdftoppm` 또는 `mutool`로 지정 페이지를 이미지로 렌더링하고 Azure AI Vision Read API를 호출해 `ocr-report.json`에 OCR line/bounding box 결과를 저장한다. `OCR_PAGES=1`, `OCR_PAGES=1,3`, `OCR_PAGES=all`을 지원한다.
  - 필요 구현: OCR 결과는 PDF 내부 byte range가 없으므로 text payload replacement 대상에 자동 병합하지 않고 supplemental report로만 저장한다.

- [x] font fallback 설정 적용
  - 선언 위치: `.env`의 `FONT_REGULAR`, `FONT_BOLD`, `FONT_FALLBACK`
  - 현재 상태: `FONT_FALLBACK_MODE`와 fallback font path를 encode 실패 처리에 적용한다. 기존 font/CMap으로 encode할 수 없으면 `FONT_FALLBACK_FONT_MISSING` 또는 `FONT_FALLBACK_EMBED_UNSUPPORTED` issue를 `encode-report.json`에 기록하고 rejected로 분류한다.
  - 필요 구현: v9는 추출한 text state/operator/font/CMap을 그대로 적용하는 정책이므로 새 font resource embed/substitution은 수행하지 않는다.

- [x] render validation 구현
  - 선언 위치: `.env`의 `RENDER_SCALE`, validation/report 문서
  - 현재 상태: `RENDER_MODE`가 off가 아니고 project-local `pdftoppm` 또는 `mutool`이 있으면 source/rebuilt 첫 페이지를 렌더링하고 hash 비교 결과를 `render-report.json`에 기록한다.
  - 필요 구현: multi-page image diff와 overlap/blank page 검출 고도화.

## 9. Report/운영성

- [x] 통합 report bundle 생성
  - 선언 위치: `src/report/README.md`, `output/reports/README.md`
  - 현재 상태: 주요 report를 `output/reports/<job>`로 복사한다.
  - 필요 구현: decode/encode/translation/rebuild/qpdf/run-summary를 하나의 report 디렉토리로 publish.

- [x] 실패 원인 분류 표준화
  - 선언 위치: `src/report/README.md`의 qpdf missing, ToUnicode missing, CMap parse failed 등
  - 현재 상태: `ReportIssue`에 `stage`, `code`, `severity`, `recoverable` 필드를 추가하고 encode/rebuild/raw/translation issue에 적용했다.
  - 필요 구현: report issue code enum, severity, stage, item id, recoverability 필드 추가.

- [x] CLI 분석/doctor 명령 구현
  - 선언 위치: 운영상 run-summary와 report를 사람이 확인해야 하는 구조
  - 현재 상태: `doctor`, `status`, `inspect <job>`, `resume <job>` command를 추가했다.
  - 필요 구현: `status`, `doctor`, `inspect <job>` 명령으로 summary, 실패 chunk, missing qpdf, OpenAI 설정 확인.