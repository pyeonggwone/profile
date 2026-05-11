# pdf-translate-v9

## 목표

v9는 원본 PDF 구조를 유지한 상태에서 텍스트 payload만 교체하는 PDF 번역 프로젝트다.

핵심 원칙은 다음과 같다.

```text
텍스트 제외 모든 PDF 객체는 원본 그대로 유지한다.
텍스트는 PDF 내부 text state/operator/font/CMap을 가능한 한 정확히 추출한다.
추출한 상태를 raw JSON으로 저장한다.
raw JSON을 사람이 읽기 좋은 번역용 JSON으로 변환한다.
OpenAI는 사람이 읽기 좋은 JSON의 텍스트만 번역한다.
번역 결과는 다시 PDF 입력용 JSON으로 저장한다.
PDF 복원 시 추출 단계에서 저장한 text state/operator/font/CMap 옵션을 그대로 적용한다.
최종 PDF는 원본 PDF 구조 위에서 텍스트 payload만 교체한다.
```

## 핵심 원칙

```text
비텍스트 객체는 재구성하지 않는다.
이미지, 도형, 표, 배경, page resource, XObject는 원본 PDF object 그대로 유지한다.

텍스트 상태는 새로 만들지 않는다.
추출 단계에서 얻은 text state/operator/font/CMap/matrix/range를 raw JSON에 저장한다.

복원 단계는 raw JSON의 restoreOptions를 그대로 사용한다.
바뀌는 것은 textPayload.replacementEncoded뿐이다.

번역은 decoded text만 대상으로 한다.
OpenAI는 PDF 구조나 operator를 알 필요가 없다.

기존 font/CMap으로 번역문 encoding이 불가능하면 조용히 대체하지 않는다.
실패 상태를 JSON/report에 기록한다.
```

## 사용 도구

| 역할 | 도구 |
|---|---|
| PDF 구조 normalize/reference | qpdf |
| PDF object/stream 직접 처리 | Rust lopdf |
| content stream parser | Rust 자체 구현 |
| CMap/ToUnicode parser | Rust 자체 구현 |
| JSON 저장/변환 | Rust serde, serde_json |
| 상태 DB/Translation Memory | SQLite, Rust rusqlite 또는 sqlx sqlite |
| OpenAI 번역 | OpenAI API |
| 최종 PDF 검증 | qpdf --check |

v9에서는 PDF 처리에 PyMuPDF, ReportLab, pdfminer를 사용하지 않는다.

## 전체 구조

v9의 처리 구조는 다음 순서로 고정한다.

```text
input PDF
  -> qpdf가 PDF stream/object 구조를 풀어 reference 생성
  -> Rust가 원본 PDF와 qpdf reference를 기준으로 text operator/state/font/CMap 추출
  -> Rust가 raw JSON을 사람이 읽기 좋은 번역용 JSON으로 변환
  -> SQLite가 job 상태, step 상태, TM hit/miss를 기록
  -> Rust가 job별 고유명사 후보와 용어집을 저장
  -> OpenAI가 번역용 JSON의 text만 번역
  -> Rust가 번역 결과를 기존 font/CMap 기준 replacementEncoded 로 변환
  -> Rust가 원본 PDF content stream에서 text payload만 교체
  -> qpdf가 최종 PDF를 검증
  -> output PDF
```

도구별 책임은 다음처럼 나눈다.

| 도구 | 책임 | 하지 않는 일 |
|---|---|---|
| qpdf | PDF 구조 풀기, QDF reference 생성, 원본/최종 PDF 검증 | 번역, text payload 교체 로직 |
| Rust lopdf | PDF object tree 읽기/쓰기, content stream 수정 | OpenAI 번역 자체 |
| Rust parser | content stream operator 파싱, text state 추적, CMap decode/encode | PDF 구조 검증 |
| OpenAI | decoded text 번역 | PDF 구조 해석 |

## 디렉토리별 흐름

```text
input/
  번역할 PDF 배치

work/<job>/source/
  원본 PDF binary 복사본과 sha256 기록

work/<job>/qpdf/
  qpdf --qdf 결과와 qpdf --check 결과 저장

work/<job>/state/
  raw-pdf-text-state.json
  readable-text-state.json
  proper-noun-candidates.json
  job-terms.json
  translation-input.json
  translation-results.json
  translation-error.json
  pdf-input-text-state.json
  rebuild-report.json
  validation-report.json

work/db/
  state.sqlite
  tm.sqlite
  terms.sqlite

work/<job>/pdf/
  Rust가 text payload만 교체한 rebuilt.pdf 저장

work/<job>/reports/
  decode/encode/rebuild 실패 상세 report 저장

output/
  qpdf 검증을 통과한 최종 PDF만 publish
```

## 데이터 변환 체인

```text
raw-pdf-text-state.json
  PDF 내부 text operator/state/font/CMap/range를 추출한 원본 상태 JSON

readable-text-state.json
  raw JSON의 encoded text를 decoded text로 변환한 번역용 JSON

proper-noun-candidates.json / job-terms.json
  job별 고유명사 후보와 확정 용어집 JSON

glossary.csv
  작업 간 번역 일관성을 유지하기 위한 CSV 용어집

state.sqlite / tm.sqlite / terms.sqlite
  job 상태, pipeline 상태, Translation Memory, term memory 보조 저장소

translation-input.json
  OpenAI에 보낼 id/text chunk JSON

translation-input-chunk-0001.json ...
  OpenAI 요청 단위로 나눈 청크 입력 JSON

translation-results.json
  OpenAI가 반환한 id/translated JSON

pdf-input-text-state.json
  raw restoreOptions + translated text + replacementEncoded 를 결합한 복원용 JSON

rebuilt.pdf
  원본 PDF 구조 위에서 text payload만 교체한 PDF

run-summary.json
  최종 실행이 completed-ok인지 completed-degraded인지 판단할 수 있는 요약 JSON
```

## 복원 기준

복원 단계에서 새 text state를 만들지 않는다.

```text
restoreOptions = 추출 단계에서 저장한 원본 text state/operator/font/CMap/range
textPayload.replacementEncoded = 번역 결과를 기존 font/CMap 기준으로 다시 encode한 payload
```

복원은 다음 교체만 수행한다.

```text
encodedOriginal -> replacementEncoded
```

비텍스트 object, non-text operator, image, path, XObject, page resource는 수정 대상이 아니다.

## 파이프라인 단계

```text
01_init_job
02_qpdf_reference
03_extract_raw_pdf_text_state
04_convert_raw_to_readable_text_state
05_extract_and_apply_job_terms
06_translate_readable_text_state
07_convert_translation_to_pdf_input_state
08_rebuild_pdf_with_extracted_options
09_qpdf_validate_output
10_publish_output
```

## 구현 프로젝트 구조

현재 v9는 Rust workspace로 구현한다. 디렉토리별 README는 설계 설명이고, 실제 구현은 `Cargo.toml`과 각 crate의 `src` 아래에 둔다.

```text
pdf-translate-v9/
├── README.md
├── Cargo.toml
├── crates/
│   ├── README.md
│   ├── pdf_cli/              CLI와 pipeline 실행
│   ├── pdf_qpdf/             qpdf adapter
│   ├── pdf_core/             lopdf object/stream 접근
│   ├── pdf_text_state/       text operator/state 추출
│   ├── pdf_cmap/             decode/encode
│   ├── pdf_terms/            고유명사/용어집
│   ├── pdf_state_db/         SQLite 상태 DB
│   ├── pdf_rebuild/          payload 교체
│   ├── pdf_translate_openai/ OpenAI adapter
│   ├── pdf_models/           JSON model
│   └── pdf_reports/          JSON report writer
├── docs/
│   ├── README.md
│   ├── architecture/README.md
│   ├── database/README.md
│   ├── json-state/README.md
│   ├── openai/README.md
│   ├── qpdf/README.md
│   ├── rust/README.md
│   ├── terms/README.md
│   └── validation/README.md
├── input/
│   ├── README.md
│   ├── ready/README.md
│   ├── done/README.md
│   └── failed/README.md
├── output/
│   ├── README.md
│   ├── validated/README.md
│   ├── rejected/README.md
│   └── reports/README.md
├── work/
│   ├── README.md
│   ├── jobs/README.md
│   ├── db/
│   │   ├── README.md
│   │   ├── sqlite/README.md
│   │   ├── schema/README.md
│   │   ├── state/README.md
│   │   ├── tm/README.md
│   │   ├── terms/README.md
│   │   └── backup/README.md
│   ├── source/README.md
│   ├── qpdf/
│   │   ├── README.md
│   │   ├── reference/README.md
│   │   ├── check-source/README.md
│   │   └── check-output/README.md
│   ├── state/
│   │   ├── README.md
│   │   ├── raw/README.md
│   │   ├── readable/README.md
│   │   ├── translation/README.md
│   │   ├── terms/README.md
│   │   ├── pdf-input/README.md
│   │   └── validation/README.md
│   ├── pdf/
│   │   ├── README.md
│   │   ├── rebuilt/README.md
│   │   ├── normalized/README.md
│   │   └── failed/README.md
│   └── reports/
│       ├── README.md
│       ├── decode/README.md
│       ├── encode/README.md
│       ├── qpdf/README.md
│       ├── rebuild/README.md
│       ├── summary/README.md
│       ├── terms/README.md
│       └── translation/README.md
└── src/
    ├── README.md
    ├── pipeline/README.md
    ├── qpdf/README.md
    ├── pdf_reader/README.md
    ├── content_parser/README.md
    ├── text_state/README.md
    ├── cmap/README.md
    ├── readable/README.md
    ├── state_store/README.md
    ├── translate/README.md
    ├── terms/README.md
    ├── rebuild/README.md
    ├── models/README.md
    ├── report/README.md
    └── publish/README.md
```

  ## 실행 전제

  ```text
  Rust cargo/rustc 필요
  qpdf 필요
  WSL에서 실행할 경우 WSL 안에 Linux용 qpdf 필요
  OPENAI_API_KEY 필요
  ```

  현재 환경에 `cargo`와 `rustc`가 없으면 빌드 검증은 실행할 수 없다. 이 경우 구현 파일은 유지하고 Rust 설치 후 `cargo check`로 검증한다.

프로젝트 루트의 `.env`는 실행 시 자동으로 읽는다. 이미 OS 환경변수에 값이 있으면 OS 환경변수를 우선한다.

```text
SOURCE_LANG=en
TARGET_LANG=ko
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=...
OCR_MODE=off
OCR_PAGES=1
AZURE_VISION_ENDPOINT=...
AZURE_VISION_KEY=...
FONT_FALLBACK_MODE=off
```

qpdf 실행 파일은 v9 프로젝트 내부 상대경로에서만 자동으로 탐색한다. 전역 package manager로 설치하지 않는다.

탐색 순서:

```text
QPDF_BIN                 상대경로면 v9 루트 기준
tools/qpdf/bin/qpdf
tools/qpdf/qpdf
tools/qpdf/bin/qpdf.exe
tools/qpdf/qpdf.exe
tools/bin/qpdf
tools/bin/qpdf.exe
```

qpdf를 사용할 때는 실행 파일을 `tools/qpdf/bin/` 아래에 둔다.

```text
tools/qpdf/bin/qpdf      Linux/WSL 실행 파일
tools/qpdf/bin/qpdf.exe  Windows 실행 파일
```

이 파일이 없으면 qpdf 단계는 실패한다. v9는 OS root, `/usr/bin`, package manager, PATH의 qpdf를 사용하지 않는다.

단, `.env`에서 `ALLOW_DEGRADED=true`이고 `STRICT_TOOLS=false`이면 qpdf reference/check 단계는 report에 skip 사유를 남기고 계속 진행한다.

Windows용 `qpdf.exe`를 `tools/qpdf/bin/qpdf.exe`에 두고 WSL에서 실행하면 내부 실행 인자는 Windows 형식으로 변환하되 report에는 v9 root 기준 상대경로를 기록한다.

## 실행 방식

기본 실행은 `input` 폴더 바로 아래의 모든 PDF를 파일명 순서대로 처리한다.

```powershell
cargo run -p pdf_cli --
```

동일한 기본 batch 처리를 명시하려면 다음처럼 실행한다.

```powershell
cargo run -p pdf_cli -- run
```

특정 파일이나 특정 디렉토리만 처리할 수도 있다. 기본 사용은 `input` 폴더에 PDF를 넣고 `run`만 실행하는 방식이다.

```powershell
cargo run -p pdf_cli -- run .\input\sample.pdf
cargo run -p pdf_cli -- run .\input
```

이미 생성된 `pdf-input-text-state.json`을 기준으로 rebuild, validation, publish만 다시 수행하려면 `finalize`를 사용한다. 이 명령은 OpenAI 번역을 다시 호출하지 않는다.

```powershell
cargo run -p pdf_cli -- finalize <job>
```

번역 언어와 모델은 `run` 명령에서 지정한다.

```powershell
cargo run -p pdf_cli -- run --source-lang en --target-lang ko --model gpt-4o-mini
```

명령 옵션이 없으면 `.env`의 `SOURCE_LANG`, `TARGET_LANG`, `OPENAI_MODEL`을 사용한다.

OpenAI 요청은 전체 text run을 한 번에 보내지 않는다. PDF 자체는 분할하지 않고, 추출된 readable text item만 page range 기준 part로 나누어 병렬 번역한다. 각 part 안에서는 `.env`의 `OPENAI_CHUNK_SIZE` 단위로 요청한다. 기본값은 100이다.

번역 part 수는 `.env`의 `TRANSLATION_PARALLELISM`으로 지정할 수 있다. `0` 또는 미설정이면 page 수 기준으로 자동 결정한다. 20 page 미만은 3개, 50 page 미만은 5개, 그 외는 10개 part를 사용한다.

실행 중에는 각 pipeline step과 OpenAI chunk 진행 상황을 터미널에 출력한다. timeout 방지를 위해 `.env`의 `OPENAI_RETRY_MAX`, `OPENAI_RETRY_BASE_MS`, `OPENAI_TIMEOUT_SECS`로 retry/backoff와 요청 timeout을 조정한다.

일부 text run이 encode/rebuild에 실패해도 성공한 replacement가 있으면 partial PDF를 `work/<job>/pdf/rebuilt.pdf`로 저장한다. 이 결과는 검증 통과 PDF가 아니므로 `output/validated`가 아니라 `output/rejected`에 publish된다.

작업 일관성 용어집은 `.env`의 `GLOSSARY_PATH`를 사용한다. 상대 경로는 v9 root 기준이며 기본값은 `glossary.csv`다.

CSV 형식:

```csv
term,translation,mode
Personal Computing Device,개인용 컴퓨팅 디바이스,fixed
IDC,,preserve
```

`mode=fixed`는 translation을 그대로 적용하라는 지시이고, `mode=preserve`는 원문 용어를 유지하라는 지시다. CSV 용어는 자동 추출된 고유명사 후보보다 우선한다.

OpenAI 요청이 실패하고 `.env`에서 `ALLOW_DEGRADED=true`, `STRICT_TOOLS=false`이면 `translation-error.json`에 실패 원인을 저장하고 원문 유지 결과를 `translation-results.json`으로 생성한다. 이 degraded 결과는 Translation Memory에 저장하지 않는다.

rebuild가 실패하고 `ALLOW_DEGRADED=true`, `STRICT_TOOLS=false`이면 `rebuild-report.json`에 실패 issue를 저장하고 원본 PDF를 `pdf/rebuilt.pdf`로 복사해 publish 단계까지 진행한다.

OCR은 기본 off다. `OCR_MODE=azure` 또는 `OCR_MODE=force`이면 project-local `pdftoppm` 또는 `mutool`로 `OCR_PAGES` 대상 페이지를 PNG로 렌더링하고 Azure AI Vision Read API를 호출해 `ocr-report.json`에 line text와 bounding box를 저장한다. OCR 결과는 PDF byte range가 없으므로 자동으로 replacement 대상에 병합하지 않는다.

font fallback 설정은 encode 실패 정책에 적용된다. v9는 새 font resource를 PDF에 주입하지 않으므로 기존 font/CMap으로 encode할 수 없는 번역문은 `encode-report.json`에 `FONT_FALLBACK_FONT_MISSING` 또는 `FONT_FALLBACK_EMBED_UNSUPPORTED`로 기록되고 rejected로 분류된다.

batch 실행 중 한 PDF가 실패해도 다음 PDF 처리는 계속 진행한다. 전체 처리가 끝난 뒤 실패한 PDF 목록을 error로 반환한다.

## 01 Init Job

원본 PDF를 작업 폴더에 복사하고 sha256을 기록한다.

산출물:

```text
work/<job>/source/source.pdf
work/<job>/state/job.json
work/<job>/state/pdf-source.json
```

예시:

```json
{
  "source": {
    "name": "sample.pdf",
    "sizeBytes": 123456,
    "sha256": "...",
    "path": "work/<job>/source/source.pdf"
  }
}
```

## 02 qpdf Reference

qpdf로 원본 PDF 구조를 reference용으로 변환하고 검증한다.

```bash
qpdf --qdf --object-streams=disable source.pdf work/<job>/qpdf/source.qdf.pdf
qpdf --check source.pdf
```

산출물:

```text
work/<job>/qpdf/source.qdf.pdf
work/<job>/state/qpdf-check.json
```

qpdf가 없으면 기본적으로 실패한다. `STRICT_TOOLS=false` 및 `ALLOW_DEGRADED=true`인 경우에는 qpdf reference/validation을 skip report로 기록하고 다음 단계로 진행한다.

## 03 Raw PDF Text State 추출

lopdf로 PDF를 열고 content stream을 직접 파싱한다.

추출 대상 operator:

```text
BT, ET
Tf
Tm
Td, TD
T*
Tj, TJ
Tc, Tw, Tz, TL, Tr, Ts
q, Q, cm
```

추출해서 저장할 값:

```text
page number
stream xref
operand range
text block range
operator sequence
text state
font state
font resource reference
encoding
ToUnicode/CMap reference
encoded text payload
matrix
```

산출물:

```text
work/<job>/state/raw-pdf-text-state.json
```

예시:

```json
{
  "pages": [
    {
      "page": 1,
      "contents": [
        {
          "streamXref": 15,
          "textRuns": [
            {
              "id": "p0001-s0015-r00001",
              "restoreOptions": {
                "streamXref": 15,
                "operator": "Tj",
                "operandRange": {
                  "start": 1842,
                  "end": 1878
                },
                "textBlockRange": {
                  "start": 1760,
                  "end": 1900
                },
                "operatorSequence": [
                  { "op": "BT" },
                  { "op": "Tf", "font": "/F1", "size": 10 },
                  { "op": "Tm", "matrix": [1, 0, 0, 1, 72, 720] },
                  { "op": "Tj" },
                  { "op": "ET" }
                ],
                "textState": {
                  "font": "/F1",
                  "fontSize": 10,
                  "textMatrix": [1, 0, 0, 1, 72, 720],
                  "charSpacing": 0,
                  "wordSpacing": 0,
                  "horizontalScaling": 100,
                  "leading": 0,
                  "renderMode": 0,
                  "rise": 0
                },
                "fontState": {
                  "resourceName": "/F1",
                  "fontObjectRef": "9 0 R",
                  "subtype": "/Type0",
                  "baseFont": "...",
                  "encoding": "...",
                  "toUnicodeRef": "12 0 R"
                }
              },
              "textPayload": {
                "encodedOriginal": "<002B0048004F>",
                "decodedOriginal": null,
                "decodedTranslated": null,
                "replacementEncoded": null
              }
            }
          ]
        }
      ]
    }
  ]
}
```

## 04 사람이 읽기 좋은 JSON 변환

raw-pdf-text-state.json을 읽고 encoded text를 사람이 읽을 수 있는 text로 변환한다.

처리:

```text
ToUnicode CMap parsing
Encoding/CID map parsing
Tj/TJ operand decode
TJ spacing 정보 보존
matrix 기반 layout 정보 계산
decode status/confidence 기록
```

산출물:

```text
work/<job>/state/readable-text-state.json
```

예시:

```json
{
  "items": [
    {
      "id": "p0001-s0015-r00001",
      "page": 1,
      "source": "Hello",
      "restoreOptionsRef": {
        "streamXref": 15,
        "operator": "Tj"
      },
      "decode": {
        "method": "ToUnicode",
        "confidence": "high",
        "issues": []
      },
      "layout": {
        "matrix": [1, 0, 0, 1, 72, 720]
      }
    }
  ]
}
```

## 05 OpenAI 번역

readable-text-state.json에서 source만 chunk로 묶어 OpenAI에 보낸다.

입력:

```json
{
  "items": [
    {
      "id": "p0001-s0015-r00001",
      "text": "Hello"
    }
  ]
}
```

출력:

```json
[
  {
    "id": "p0001-s0015-r00001",
    "translated": "안녕하세요"
  }
]
```

산출물:

```text
work/<job>/state/translation-input.json
work/<job>/state/translation-input-part-0001.json
work/<job>/state/translation-input-part-0001-chunk-0001.json
work/<job>/state/translation-results-part-0001.json
work/<job>/state/translation-report-part-0001.json
work/<job>/state/translation-results.json
```

## 06 PDF 입력용 JSON 변환

번역 결과를 raw state와 병합한다.

처리:

```text
id 기준으로 raw-pdf-text-state와 translation-results 병합
decodedTranslated 저장
decodedTranslated가 decodedOriginal과 같으면 encodedOriginal을 replacementEncoded로 그대로 재사용
기존 font/CMap으로 replacementEncoded 생성 시도
encoding 성공/실패 기록
```

현재 구현은 ASCII literal string, ASCII hex string, UTF-16BE BOM hex string, ASCII TJ array를 replacementEncoded로 변환한다. 명시적 CMap mapping이 없는 non-ASCII 재인코딩은 실패로 남긴다.

실패하면 `encode.status=failed`로 표시하고 rebuild 단계에서 해당 run은 실패 처리한다. 원문 유지 항목은 `encode.method=reuse-original-encoded`로 기록한다.

산출물:

```text
work/<job>/state/pdf-input-text-state.json
```

예시:

```json
{
  "textRuns": [
    {
      "id": "p0001-s0015-r00001",
      "restoreOptions": {
        "streamXref": 15,
        "operator": "Tj",
        "operandRange": {
          "start": 1842,
          "end": 1878
        },
        "textState": {},
        "fontState": {}
      },
      "textPayload": {
        "encodedOriginal": "<002B0048004F>",
        "decodedOriginal": "Hello",
        "decodedTranslated": "안녕하세요",
        "replacementEncoded": "<...>"
      },
      "encode": {
        "method": "original-font-cmap",
        "status": "ok"
      }
    }
  ]
}
```

## 07 PDF 복원

원본 PDF를 열고 pdf-input-text-state.json 기준으로 text payload만 교체한다.

처리:

```text
원본 PDF object tree 유지
streamXref로 content stream 찾기
operandRange로 원본 text payload 찾기
restoreOptions의 text state/operator/font/CMap 옵션 그대로 적용
encodedOriginal을 replacementEncoded로 교체
비텍스트 operator/object/resource는 수정하지 않음
```

원본:

```pdf
BT
/F1 10 Tf
1 0 0 1 72 720 Tm
<002B0048004F> Tj
ET
```

복원:

```pdf
BT
/F1 10 Tf
1 0 0 1 72 720 Tm
<replacementEncoded> Tj
ET
```

산출물:

```text
work/<job>/pdf/rebuilt.pdf
work/<job>/state/rebuild-report.json
```

## 08 qpdf 검증

최종 PDF를 qpdf로 검증한다.

```bash
qpdf --check work/<job>/pdf/rebuilt.pdf
```

산출물:

```text
work/<job>/state/validation-report.json
```

## 09 Publish

검증이 통과한 PDF를 output으로 복사한다. degraded mode에서 rebuild 또는 validation이 실패했으면 report에 실패 상태를 남기고 fallback PDF를 output으로 복사할 수 있다.

산출물:

```text
output/<source-name>_V9.pdf
work/<job>/state/run-summary.json
```

## 실패 처리 원칙

| 상황 | 처리 |
|---|---|
| qpdf 없음 | 실패 |
| ToUnicode 없음 | decode failed |
| CMap 해석 실패 | decode failed |
| 사람이 읽는 text 변환 실패 | 번역 제외, report 기록 |
| 기존 font/CMap으로 번역문 encode 불가 | encode failed |
| operandRange 불일치 | rebuild failed |
| qpdf 검증 실패 | 기본 모드에서는 publish 중단, degraded mode에서는 report 기록 후 fallback publish |

## 최종 정의

```text
v9는 qpdf + Rust lopdf 기반 PDF text payload replacement 프로젝트다.

추출 단계에서 text state/operator/font/CMap/range를 raw JSON에 저장한다.
이 raw JSON의 restoreOptions가 복원 단계의 입력 옵션이다.
OpenAI는 decoded text만 번역한다.
복원 단계에서는 restoreOptions를 그대로 적용하고 text payload만 replacementEncoded로 교체한다.
텍스트 제외 모든 PDF 객체는 원본 그대로 유지한다.
```
