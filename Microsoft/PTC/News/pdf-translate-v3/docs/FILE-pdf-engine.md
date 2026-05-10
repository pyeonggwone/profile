# PDF 엔진 — pdf-translate-v3

`pdf-translate-v3` 은 PDF 처리를 외부화된 엔진 CLI로 분리한다. 기본 엔진은 MuPDF/PyMuPDF 이며, 기존 Rust `pdftr` CLI 는 fallback 으로 유지한다.

## 기본 엔진 — PyMuPDF

```env
PDF_ENGINE=pymupdf
PYTHON_BIN=python3
PDF_FONT_PATH=/usr/share/fonts/truetype/nanum/NanumGothic.ttf
```

`src/pdf/pymupdf_engine.py` 가 제공하는 명령:

| 명령 | 역할 | v3 사용 여부 |
|---|---|---|
| `pymupdf_engine.py inspect <pdf> --json` | PDF 메타데이터 + 엔진 버전 | 디버그용 (`engine.inspect`) |
| `pymupdf_engine.py text <pdf> --json` | 페이지/span 단위 텍스트와 bbox 추출 | EXTRACT 단계 (`engine.extractPages`) |
| `pymupdf_engine.py edit <input> <output> --edits <json>` | `FillRect` / `AddTextBoxEmbedded` 적용 | APPLY 단계 (`engine.applyEdits`) |

EXTRACT 응답은 기존 `pdftr text` 와 호환되도록 `page`, `width`, `height`, `runs[]` 형태를 유지한다. PyMuPDF 엔진은 추가로 `top`, `bottom`, `left`, `right`, `width`, `height`, `font`, `color` 를 포함한다.

현재 PyMuPDF 엔진은 span 별로 다음 스타일 정보를 추가한다.

- `color_rgb`: 원본 글자색
- `bg_color`: bbox 주변 픽셀 샘플 기반 배경색
- `bold`, `italic`, `serif`, `monospace`: PyMuPDF font flags 및 font name 기반 스타일 추정
- `flags`: PyMuPDF span flags 원본값

APPLY 단계는 원문 영역을 `FillRect` 로 덮고, 번역문을 `AddTextBoxEmbedded` 로 같은 bbox 영역에 삽입한다. 텍스트가 박스에 들어가지 않으면 font size 를 0.5pt 단위로 줄인다.

테이블과 도형 내부 텍스트는 원본 bbox보다 약간 안쪽만 지우도록 `PDF_ERASE_PADDING` 을 적용한다. 흰색 고정 배경 대신 `bg_color` 를 사용하므로 색상 박스/다이어그램 라벨의 시각적 이질감을 줄인다.

## fallback 엔진 — `pdftr` CLI

`PDF_ENGINE=pdftr` 로 지정하면 Rust workspace 내 `pdftr` CLI 를 사용한다.

## `pdftr` CLI 인터페이스

`crates/cli_tools/src/main.rs` 가 정의하는 명령:

| 명령 | 역할 | v3 사용 여부 |
|---|---|---|
| `pdftr inspect <pdf> [--json]` | PDF 메타데이터 + 경고 | 디버그용 (`engine.inspect`) |
| `pdftr text <pdf> [--json]` | 페이지/런 단위 텍스트 추출 | EXTRACT 단계 (`engine.extractPages`) |
| `pdftr render-plan <pdf> <page>` | Canvas viewer 용 render plan | 미사용 |
| `pdftr edit <input> <output> --edits <json>` | EditOperation JSON 적용 → Incremental Update PDF | APPLY 단계 (`engine.applyEdits`) |
| `pdftr roundtrip <pdf>` | 무변경 incremental update 후 prefix 검증 | 미사용 |

## `pdftr` 자동 탐색 순서

`src/pdf/engine.mjs::resolvePdfEngineBin()` 가 다음 순서로 바이너리를 찾는다.

1. `.env` 의 `PDF_ENGINE_BIN`
2. `target/release/pdftr` (v3 자체 빌드 산출물)
3. `target/debug/pdftr`
4. `$PATH` 의 `pdftr`

OS 별 파일명: Linux/macOS = `pdftr`, Windows = `pdftr.exe`.

## EXTRACT — `pdftr text --json`

응답 schema (`pdf_analysis::PageText`):

```json
[
  {
    "page": 1,
    "width": 612.0,
    "height": 792.0,
    "runs": [
      {
        "text": "Hello world",
        "x": 72.0,
        "y": 720.0,
        "font_size": 12.0,
        "font_resource": "F1"
      }
    ]
  }
]
```

v3 의 `flattenSegments()` 가 이를 다음 형태로 평탄화한다:

```json
[
  { "id": 0, "page": 1, "runIndex": 0, "x": 72.0, "y": 720.0, "fontSize": 12.0, "text": "Hello world" }
]
```

빈 텍스트 / 공백만 있는 run 은 제외.

## APPLY — `pdftr edit --edits`

입력 JSON (`Vec<EditOperation>`, `serde tag = "type"`):

```json
[
  {
    "type": "AddText",
    "page": 1,
    "x": 72.0,
    "y": 720.0,
    "text": "안녕 세계",
    "font": "Helvetica",
    "size": 12.0,
    "color": [0, 0, 0]
  }
]
```

지원하는 `type`:

- `AddText` — Base14 폰트로 page 의 (x, y) 좌표에 텍스트 직접 추가.
- `AddTextAnnotation` — free-text annotation. 시각화는 자동 생성.
- `AddImageJpeg` — JPEG 이미지를 page 에 추가 (`bytesB64`).

v3 는 현재 **`AddText` 만** 사용한다.

`pdftr edit` 는 `pdf_incremental::IncrementalWriter::build()` 를 호출하여:

- 원본 PDF 의 byte prefix 를 그대로 보존
- 끝부분에 `xref` + `trailer` + `startxref` + `%%EOF` 의 새 incremental section 추가
- 새 객체 (Content stream, Annotation 등) 를 append

이 방식은 PDF 1.4 이후의 표준 incremental update 절차를 따른다.

## 폰트 제약 (현재)

- `EditOperation::AddText` 는 `FontFamily` enum 만 받는다: `Helvetica`, `HelveticaBold`, `TimesRoman`, `Courier`. 모두 Base14 (Latin-1).
- 한글, 일본어, 중국어 등 비-Latin 출력은 PDF Base14 인코딩 범위를 벗어나 깨진다.
- `crates/pdf_writer/font.rs` 에 TrueType subset 임베딩 로직이 이미 구현되어 있으나, CLI 표면(`pdftr edit`) 에는 노출되어 있지 않다.
- 해결 방향 (v3 안에서 작업 가능):
    - `EditOperation` 에 `AddTextEmbedded { font_path, ... }` variant 추가
    - 또는 `--font <ttf>` CLI 옵션으로 모든 `AddText` 의 폰트를 임베디드 폰트로 교체

해결 전까지 한글 PDF 출력은 layout / 인코딩이 깨질 수 있다. `TODO.md` 에 추적.

## 에러 처리

- `pdftr` 의 비-0 종료 코드는 `engine.runEngine()` 이 stdout/stderr 를 합쳐 throw.
- `pipeline.processFile()` 는 EXTRACT/APPLY 단계 실패를 catch 해 `work/<stem>/error.json` 에 기록하고, 다음 PDF 처리를 계속한다.
- 거부되는 PDF (DRM, 암호화, 손상) 는 EXTRACT 단계에서 실패하며, 원본은 `input/` 에 남는다.

## 빌드 명령

```bash
cargo build --release -p pdftr_cli
ls target/release/pdftr
```

`run-translate.sh` 가 첫 실행 시 자동으로 위 명령을 수행한다.
