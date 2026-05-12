# PDF 엔진 — pdf-translate-v2

`pdf-translate-v2` 는 PDF 의 binary 처리를 직접 하지 않고, `pdf-translate-v1` 의 Rust workspace 가 제공하는 `pdftr` CLI 바이너리를 자식 프로세스로 호출한다.

## v1 의 `pdftr` CLI 인터페이스

`pdf-translate-v1/crates/cli_tools/src/main.rs` 가 정의하는 명령:

| 명령 | 역할 | v2 사용 여부 |
|---|---|---|
| `pdftr inspect <pdf> [--json]` | PDF 메타데이터 + 경고 | 디버그용 (`engine.inspect`) |
| `pdftr text <pdf> [--json]` | 페이지/런 단위 텍스트 추출 | EXTRACT 단계 (`engine.extractPages`) |
| `pdftr render-plan <pdf> <page>` | Canvas viewer 용 render plan | 미사용 |
| `pdftr edit <input> <output> --edits <json>` | EditOperation JSON 적용 → Incremental Update PDF | APPLY 단계 (`engine.applyEdits`) |
| `pdftr roundtrip <pdf>` | 무변경 incremental update 후 prefix 검증 | 미사용 |

## 자동 탐색 순서

`src/pdf/engine.mjs::resolvePdfEngineBin()` 가 다음 순서로 바이너리를 찾는다.

1. `.env` 의 `PDF_ENGINE_BIN`
2. `pdf-engine/target/release/pdftr` (`pdf-engine/` 심볼릭 링크 또는 카피본)
3. `pdf-engine/target/debug/pdftr`
4. `../pdf-translate-v1/target/release/pdftr`
5. `../pdf-translate-v1/target/debug/pdftr`
6. `$PATH` 의 `pdftr`

OS 별 파일명: Linux/macOS = `pdftr`, Windows = `pdftr.exe`.

## EXTRACT — `pdftr text --json`

응답 schema (v1 의 `pdf_analysis::PageText`):

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

v2 의 `flattenSegments()` 가 이를 다음 형태로 평탄화한다:

```json
[
  { "id": 0, "page": 1, "runIndex": 0, "x": 72.0, "y": 720.0, "fontSize": 12.0, "text": "Hello world" }
]
```

빈 텍스트 / 공백만 있는 run 은 제외.

## APPLY — `pdftr edit --edits`

입력 JSON (v1 의 `Vec<EditOperation>`, `serde tag = "type"`):

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
- `AddTextAnnotation` — free-text annotation. 시각화는 v1 이 자동 생성.
- `AddImageJpeg` — JPEG 이미지를 page 에 추가 (`bytesB64`).

v2 는 현재 **`AddText` 만** 사용한다.

`pdftr edit` 는 v1 의 `pdf_incremental::IncrementalWriter::build()` 를 호출하여:

- 원본 PDF 의 byte prefix 를 그대로 보존
- 끝부분에 `xref` + `trailer` + `startxref` + `%%EOF` 의 새 incremental section 추가
- 새 객체 (Content stream, Annotation 등) 를 append

이 방식은 PDF 1.4 이후의 표준 incremental update 절차를 따른다.

## 폰트 제약 (현재)

- v1 의 `EditOperation::AddText` 는 `FontFamily` enum 만 받는다: `Helvetica`, `HelveticaBold`, `TimesRoman`, `Courier`. 모두 Base14 (Latin-1).
- 한글, 일본어, 중국어 등 비-Latin 출력은 PDF Base14 인코딩 범위를 벗어나 깨진다.
- v1 의 `pdf_writer/font.rs` 에 TrueType subset 임베딩 로직이 이미 구현되어 있으나, CLI 표면(`pdftr edit`) 에는 노출되어 있지 않다.
- 해결 방향 (v1 측 변경 필요):
    - `EditOperation` 에 `AddTextEmbedded { font_path, ... }` variant 추가
    - 또는 `--font <ttf>` CLI 옵션으로 모든 `AddText` 의 폰트를 임베디드 폰트로 교체

해결 전까지 한글 PDF 출력은 layout / 인코딩이 깨질 수 있다. `TODO.md` 에 추적.

## 에러 처리

- `pdftr` 의 비-0 종료 코드는 `engine.runEngine()` 이 stdout/stderr 를 합쳐 throw.
- `pipeline.processFile()` 는 EXTRACT/APPLY 단계 실패를 catch 해 `work/<stem>/error.json` 에 기록하고, 다음 PDF 처리를 계속한다.
- v1 이 거부하는 PDF (DRM, 암호화, 손상) 는 EXTRACT 단계에서 실패하며, 원본은 `input/` 에 남는다.

## 빌드 명령 (참고)

`pdf-translate-v1` 디렉토리에서:

```bash
cargo build --release -p pdftr_cli
```

산출물: `pdf-translate-v1/target/release/pdftr` (또는 `.exe`).
