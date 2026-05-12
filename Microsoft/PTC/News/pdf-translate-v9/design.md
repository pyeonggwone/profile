# design

이 문서는 `TODO.md`에 적힌 미구현/부분 구현 항목을 실제로 어떻게 구현할지 정리한다.

`README.md`는 프로젝트 목표, 실행법, 산출물 위치를 설명하는 사용자용 문서로 둔다. 구현 상세, 모듈 경계, 데이터 계약, 우선순위는 이 파일에서 관리한다.

## 문서 역할

```text
README.md   사용자 실행/운영 문서
design.md   구현 설계 문서
TODO.md     선언 대비 미구현 추적 목록
docs/*      세부 주제별 참고 문서
```

README에는 기본 실행법, 환경값, 산출물 위치, 성공/실패 판정법만 남긴다. 내부 schema, 세부 pipeline, crate별 구현 방식, 미구현 예정 기능은 design.md와 TODO.md로 분리한다.

## 구현 원칙

1. 원본 PDF의 비텍스트 객체는 수정하지 않는다.
2. text payload 교체는 raw extraction에서 얻은 `restoreOptions`와 byte range를 기준으로 한다.
3. 지원 범위를 벗어나면 조용히 대체하지 않고 JSON report에 남긴다.
4. 외부 도구 경로와 runtime path는 v9 root 기준 상대 경로를 우선한다.
5. 실행 결과는 `translated`, `partial`, `fallback`, `failed`로 분류한다.
6. `output/validated`에는 검증 통과한 실제 결과만 둔다.

## 구현 우선순위

1. 번역 요청 안정화: provider 분리, chunk retry, 응답 id 검증
2. 결과 분류 정리: validated/rejected 분리, run-summary 확장, report bundle
3. 용어 일관성: CSV 적용 검증, fixed/preserve report, terms DB
4. path/env 적용: INPUT_DIR, OUTPUT_DIR, WORK_DIR, TM_DB_PATH, KEEP_WORK
5. PDF 추출 정확도: font resource, ToUnicode CMap, text state stack, textBlockRange
6. rebuild 정책: 부분 실패 처리, 구조 검증, non-ASCII encoding
7. 운영성: doctor/status/inspect/resume 명령
8. 선택 기능: OCR, fallback font, render validation

## 1. OpenAI/Azure OpenAI

### Provider 분리

현재 `pdf_translate_openai`는 OpenAI public endpoint만 호출한다. provider 중립 config로 바꾼다.

```rust
pub enum LlmProvider {
    OpenAi,
    AzureOpenAi,
}

pub struct TranslateConfig {
    pub provider: LlmProvider,
    pub api_key: String,
    pub model: Option<String>,
    pub azure_endpoint: Option<String>,
    pub azure_deployment: Option<String>,
    pub azure_api_version: Option<String>,
    pub source_lang: String,
    pub target_lang: String,
}
```

선택 규칙:

1. `AZURE_OPENAI_ENDPOINT`와 `AZURE_OPENAI_DEPLOYMENT`가 있으면 Azure OpenAI 사용
2. 아니면 `OPENAI_API_KEY`와 `OPENAI_MODEL`로 OpenAI public 사용
3. 둘 다 없으면 번역 단계 실패

OpenAI public endpoint:

```text
POST https://api.openai.com/v1/chat/completions
Authorization: Bearer <OPENAI_API_KEY>
```

Azure OpenAI endpoint:

```text
POST {AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}
api-key: <AZURE_OPENAI_API_KEY>
```

구현 위치:

- `crates/pdf_translate_openai/src/lib.rs`
- `crates/pdf_cli/src/main.rs`

### Chunk retry/backoff

현재 `OPENAI_CHUNK_SIZE`로 chunk 분리는 되어 있다. 다음 값을 추가한다.

```text
OPENAI_RETRY_MAX=3
OPENAI_RETRY_BASE_MS=1000
OPENAI_TIMEOUT_SECS=120
```

처리 규칙:

1. chunk별 요청 전 `translation-chunk-report-0001.json`에 `running` 기록
2. HTTP 429, 500, 502, 503, 504, timeout은 retry
3. retry delay는 `base * 2^attempt`
4. strict mode에서는 최종 실패 시 pipeline 실패
5. degraded mode에서는 실패 chunk만 source text fallback

산출물:

```text
work/<job>/state/translation-chunk-report-0001.json
work/<job>/state/translation-report.json
```

### Translation completeness 검증

OpenAI 응답은 다음을 검증한다.

- 요청 id가 응답에 모두 있어야 한다.
- 응답 id는 요청 id 안에 있어야 한다.
- 중복 id가 없어야 한다.
- `translated`가 빈 문자열이면 실패다.

검증 함수:

```rust
fn validate_translation_results(request: &TranslationInput, response: &TranslationResults) -> TranslationValidationReport
```

## 2. CSV/용어 일관성

### CSV contract

기본 CSV:

```csv
term,translation,mode
IDC,,preserve
Personal Computing Device,개인용 컴퓨팅 디바이스,fixed
```

허용 header alias:

```text
term: term, source, source_term
translation: translation, target, target_term
mode: mode
```

merge 우선순위:

1. 기존 `job-terms.json` 수동 수정 값
2. `glossary.csv`
3. 자동 추출 preserve 후보

현재는 2와 3 병합만 되어 있으므로, 기존 `job-terms.json`을 읽어 수동 수정 값을 우선하는 로직을 추가한다.

### Term application report

산출물:

```text
work/<job>/state/term-application-report.json
```

검증 규칙:

- `preserve`: source에 term이 있으면 translated에도 같은 term이 있어야 한다.
- `fixed`: source에 term이 있으면 translated에는 translation이 있어야 한다.
- 위반 항목은 item id, term, mode, expected, actual을 기록한다.

초기 정책은 `report-only`로 둔다. 강제 치환은 문장을 망칠 수 있으므로 별도 옵션으로 분리한다.

```text
TERM_ENFORCEMENT=off|report-only|strict
```

### terms.sqlite

term memory는 Translation Memory와 분리한다.

```sql
CREATE TABLE terms (
  term TEXT PRIMARY KEY,
  translation TEXT,
  mode TEXT NOT NULL,
  source TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

`source` 값:

```text
glossary-csv
job-confirmed
auto-candidate
```

## 3. SQLite 상태/Translation Memory

### State DB와 TM DB 분리

현재 translation memory는 `state.sqlite` 내부 table로 저장된다. `TM_DB_PATH`가 선언되어 있으므로 다음처럼 분리한다.

```text
work/db/state.sqlite     job, step, artifact, validation event
work/tm.sqlite           translation memory
work/terms.sqlite        term memory
```

구조:

- `StateDb`: jobs, pipeline_steps, artifacts, validation_events
- `TmDb`: translation_memory
- `TermsDb`: terms

마이그레이션:

1. 기존 `state.sqlite.translation_memory`는 읽기 호환 유지
2. 새 저장은 `TM_DB_PATH`에 수행
3. README와 `.env`를 실제 동작에 맞춘다.

### Artifact index

각 step이 산출물을 만든 직후 `StateDb::add_artifact`를 호출한다.

artifact kind 예:

```text
source-pdf
qdf-pdf
raw-json
readable-json
terms-json
translation-input
translation-results
pdf-input-json
rebuilt-pdf
validation-report
run-summary
published-pdf
```

### Validation events

SQLite schema:

```sql
CREATE TABLE validation_events (
  job_id TEXT NOT NULL,
  stage TEXT NOT NULL,
  severity TEXT NOT NULL,
  code TEXT NOT NULL,
  item_id TEXT,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

모든 JSON report issue는 SQLite에도 index로 저장한다.

### Resume

CLI:

```bash
pdf-translate-v9 resume <job>
```

규칙:

1. `pipeline_steps`에서 마지막 completed step 확인
2. 다음 step부터 실행
3. 이전 산출물이 없거나 hash가 다르면 해당 step부터 재실행
4. OpenAI chunk는 chunk report를 보고 실패 chunk만 재시도

## 4. 입력/출력 디렉토리 운영

### Runtime path 적용

`Paths` 생성 전에 runtime path를 만든다.

```rust
struct RuntimePaths {
    root: PathBuf,
    input_dir: PathBuf,
    output_dir: PathBuf,
    work_dir: PathBuf,
}
```

env:

```text
INPUT_DIR=input
OUTPUT_DIR=output
WORK_DIR=work
```

상대 경로는 v9 root 기준이다.

### input queue

처리 순서:

1. `input/ready/*.pdf`가 있으면 ready queue 처리
2. 없으면 `input/*.pdf` 처리
3. 성공 시 `input/done`으로 이동 또는 복사
4. 실패 시 `input/failed`로 이동 또는 복사

정책:

```text
INPUT_ARCHIVE_MODE=copy|move|off
```

### output 분리

publish 위치:

```text
output/validated   validation_ok=true and degraded=false
output/rejected    validation failed, rebuild failed, degraded fallback
output/reports     report bundle
```

`completed-degraded` 결과는 `validated`에 두지 않는다.

### KEEP_WORK

`KEEP_WORK=false`이면 성공 job은 최소 report만 남기고 중간 파일을 정리한다. 실패 또는 degraded job은 항상 work를 유지한다.

## 5. qpdf/검증

### doctor command

CLI:

```bash
pdf-translate-v9 doctor
```

검사 항목:

- project root
- `.env` load 여부
- qpdf 후보 경로와 실행 가능 여부
- OpenAI/Azure OpenAI provider 설정
- input/output/work path
- glossary.csv 존재와 header
- SQLite open 가능 여부

산출물:

```text
work/doctor-report.json
```

### Validation stages

검증 함수를 분리한다.

```rust
validate_source_pdf()
validate_raw_extraction()
validate_translation_results()
validate_encoding()
validate_rebuild_ranges()
validate_final_pdf()
```

공통 report:

```rust
struct StageReport {
    stage: String,
    ok: bool,
    issues: Vec<ReportIssue>,
}
```

### encode-report.json

`convert_pdf_input`에서 별도 report를 쓴다.

```json
{
  "ok": true,
  "total": 5769,
  "okCount": 5769,
  "failedCount": 0,
  "methods": {
    "reuse-original-encoded": 5769,
    "original-font-cmap": 0
  },
  "issues": []
}
```

## 6. PDF text state/CMap/ToUnicode

### Font resource extraction

`Tf`에서 현재 font resource name을 얻고 page resources의 `/Font` dictionary를 조회한다.

저장할 값:

```text
resourceName
fontObjectRef
subtype
baseFont
encoding
toUnicodeRef
```

필요 API:

```rust
fn get_object_dict(&self, object_id: ObjectId) -> Result<Dictionary>
fn resolve_resource_ref(resources: &Dictionary, category: &str, name: &str) -> Option<ObjectId>
```

### ToUnicode parser

`pdf_cmap`에 ToUnicode parser를 추가한다.

지원 범위 1차:

- `begincodespacerange`
- `beginbfchar`
- `beginbfrange`

API:

```rust
pub struct CMap {
    pub code_to_unicode: BTreeMap<Vec<u8>, String>,
    pub unicode_to_code: BTreeMap<String, Vec<u8>>,
}

pub fn parse_to_unicode_cmap(bytes: &[u8]) -> Result<CMap>
pub fn decode_with_cmap(encoded: &str, cmap: &CMap) -> DecodeResult
pub fn encode_with_cmap(text: &str, cmap: &CMap) -> Result<String>
```

1차 목표는 decode 정확도 향상이다. encode는 역매핑이 있을 때만 허용한다.

### qdf reference 활용

raw extraction은 원본 PDF byte range를 기준으로 유지한다. qdf는 debug/reference로만 사용한다.

구현:

- qdf object/stream snapshot 저장
- 원본 object id와 qdf object hint 연결
- 복원 기준은 원본 stream byte range 유지

### Text/graphics state stack

parser state:

```rust
struct ParserState {
    text: TextState,
    graphics_stack: Vec<GraphicsState>,
    ctm: [f64; 6],
    text_block_start: Option<usize>,
}
```

operator 처리:

- `q`, `Q`: graphics state push/pop
- `cm`: CTM multiply
- `Td`, `TD`, `T*`: line matrix/text matrix update
- `'`: `T*` + `Tj`
- `"`: `Tw` + `Tc` + `T*` + `Tj`

### textBlockRange

`BT` token start와 `ET` token end를 추적한다. 같은 text block 안의 run에는 동일한 `textBlockRange`를 넣는다.

### Layout info

1차 구현은 추정 bbox다.

```rust
pub struct LayoutInfo {
    pub matrix: Option<[f64; 6]>,
    pub bbox: Option<[f64; 4]>,
    pub estimated_width: Option<f64>,
}
```

width 추정:

```text
decoded char count * font_size * 0.5 * horizontal_scaling
```

### Non-ASCII replacement encoding

단계:

1. 원문과 번역문이 같으면 `encodedOriginal` 재사용
2. ASCII면 기존 literal/hex/TJ 방식 사용
3. ToUnicode 역매핑에 모든 문자가 있으면 기존 CMap code로 encode
4. 역매핑이 없으면 encode failed
5. fallback font embed는 별도 mode로 둔다.

## 7. Rebuild/PDF 복원

### Partial failure policy

정책:

```text
STRICT_TOOLS=true:
  하나라도 실패하면 rebuilt.pdf 저장하지 않고 publish 중단

ALLOW_DEGRADED=true:
  성공 replacement는 work/pdf/rebuilt.partial.pdf에 저장
  최종 output은 output/rejected로 publish
  source copy fallback은 work/pdf/fallback-source.pdf로 명시
```

`output/validated`에는 `rebuild.ok=true`, `validation.ok=true`, `degraded=false`만 간다.

### RebuildReport 확장

```rust
pub struct RebuildReport {
    pub ok: bool,
    pub replaced: usize,
    pub failed: Vec<ReportIssue>,
    pub modified_streams: usize,
    pub output_written: bool,
    pub fallback_used: bool,
}
```

### Run summary 확장

```json
{
  "classification": "translated|partial|fallback|failed",
  "fallbackUsed": false,
  "partialOutputPdf": null,
  "rejectedPdf": null,
  "validatedPdf": null
}
```

## 8. OCR/Font/Rendering

### OCR

OCR은 기본 off다. `OCR_MODE=azure` 또는 `OCR_MODE=force`일 때만 실행한다.

pipeline 위치:

```text
03_extract_raw_pdf_text_state
03b_ocr_pages_if_needed
04_convert_raw_to_readable_text_state
```

OCR trigger:

- `OCR_MODE=force`
- `OCR_MODE=azure`
- `OCR_PAGES=1`, `OCR_PAGES=1,3`, `OCR_PAGES=all`

구현은 project-local `pdftoppm` 또는 `mutool`로 source PDF 페이지를 PNG로 렌더링한 뒤 Azure AI Vision Read API에 binary image를 전송한다. `operation-location` header를 polling하고 성공 시 line text와 bounding box를 `ocr-report.json`에 저장한다. `AZURE_VISION_KEY`는 report/log에 쓰지 않는다.

OCR 결과는 PDF 내부 byte range가 없으므로 v9의 text payload replacement 대상에는 포함하지 않는다. overlay PDF를 만들지 않는 한 supplemental report로 둔다.

### Fallback font

fallback font는 기존 text payload 교체만으로 처리할 수 없다. 새 font resource 추가와 content stream operator 삽입은 v9의 `추출한 text state/operator/font/CMap 그대로 복원` 원칙과 충돌하므로 substitution을 수행하지 않는다.

```text
FONT_FALLBACK_MODE=off|embed
```

구현 정책:

1. 기존 font/CMap으로 replacement encoding을 먼저 시도한다.
2. 실패하고 `FONT_FALLBACK_MODE=off`이면 기존 encode failure로 기록한다.
3. fallback mode가 켜졌지만 font path가 없거나 파일이 없으면 `FONT_FALLBACK_FONT_MISSING`을 기록한다.
4. fallback font가 있어도 v9는 새 font embed를 하지 않으므로 `FONT_FALLBACK_EMBED_UNSUPPORTED`를 기록하고 rejected로 분류한다.

### Render validation

qpdf는 render 기능이 없으므로 별도 project-local render tool이 필요하다.

후보:

- poppler `pdftoppm`
- MuPDF `mutool draw`

산출물:

```text
work/<job>/render/source/page-0001.png
work/<job>/render/output/page-0001.png
work/<job>/state/render-report.json
```

검증:

- page count 동일
- render 성공
- blank page 여부
- 큰 diff 비율

## 9. Report/CLI 운영성

### ReportIssue schema

현재 `ReportIssue`는 `id`, `message`만 가진다. 다음 구조로 확장한다.

```rust
pub struct ReportIssue {
    pub id: Option<String>,
    pub stage: Option<String>,
    pub code: String,
    pub severity: String,
    pub message: String,
    pub recoverable: bool,
}
```

code 예:

```text
QPDF_MISSING
OPENAI_RATE_LIMIT
TRANSLATION_ID_MISSING
TO_UNICODE_MISSING
CMAP_PARSE_FAILED
ENCODE_UNSUPPORTED_NON_ASCII
REBUILD_RANGE_MISMATCH
VALIDATION_FAILED
```

### Report bundle

publish 단계에서 report bundle을 생성한다.

```text
output/reports/<job>/run-summary.json
output/reports/<job>/qpdf-check.json
output/reports/<job>/translation-report.json
output/reports/<job>/encode-report.json
output/reports/<job>/rebuild-report.json
output/reports/<job>/validation-report.json
```

### CLI commands

추가 command:

```bash
pdf-translate-v9 doctor
pdf-translate-v9 status
pdf-translate-v9 inspect <job>
pdf-translate-v9 resume <job>
```

`doctor`는 runtime env/tooling 사전 점검, `status`는 job 목록, `inspect`는 특정 job report 요약, `resume`은 중단 job 재시작을 담당한다.

## 완료 기준

전체 구현 완료 판정은 다음 조건을 모두 만족해야 한다.

1. `cargo check` 통과
2. `doctor` 통과 또는 missing tool이 명확히 report됨
3. OpenAI/Azure OpenAI chunk 번역에서 `translation-report.ok=true`
4. `changedTextRuns > 0`인 실제 번역 PDF 생성
5. `rebuild.ok=true`
6. `validation.ok=true`
7. `output/validated`에는 진짜 검증 통과 PDF만 존재
8. degraded/fallback 결과는 `output/rejected`로 분리
9. `run-summary.json`이 translated/partial/fallback/failed를 명확히 표시
10. README, design, TODO가 서로 같은 동작을 설명