# build.md — pdf-translate-v5 빌드 파이프라인 설계

이 문서는 `pdf-translate-v5` 의 빌드/실행 파이프라인을 정의한다. 여기서 빌드는 소스 컴파일만 의미하지 않고, 원본 PDF를 번역 PDF로 만드는 전체 처리 과정을 의미한다.

구현 난이도는 고려하지 않는다. 각 기능은 품질과 호환성이 가장 좋은 도구에 연결한다.

## 최종 실행 형태

사용자는 하나의 shell script만 실행한다.

```bash
./run-v5.sh input/source.pdf
```

옵션 예시:

```bash
./run-v5.sh --in-lang en --out-lang kr input/source.pdf
./run-v5.sh --ocr local input/source.pdf
./run-v5.sh --ocr azure input/source.pdf
./run-v5.sh --translation-mode openai input/source.pdf
./run-v5.sh --translation-mode azure-openai input/source.pdf
./run-v5.sh --keep-work input/source.pdf
```

현재 구현은 `run-v5.sh` 와 `src/pdf_translate_v5/pipeline.py` 로 동작한다. 고품질 목표 도구가 설치되지 않은 경우에는 실패 대신 `degraded` 상태를 기록하고 가능한 adapter로 진행한다. `--strict` 를 사용하면 권장 도구 누락을 실패로 처리한다.

`run-v5.sh` 는 내부적으로 필요한 언어와 도구를 호출한다.

- QPDF CLI
- Python scripts
- Node scripts
- Java
- PDFium wrapper
- Poppler CLI
- PaddleOCR
- Azure AI Vision
- HarfBuzz
- Pango
- Cairo
- ReportLab
- Ghostscript
- veraPDF

## 파이프라인 개요

```text
01_validate_pdf
02_extract_pdf_objects
03_render_pages
04_extract_text_bbox
05_analyze_fonts
06_detect_tables
07_extract_ocr_text
08_build_translation_units
09_translate
10_shape_translated_text
11_layout_translated_text
12_build_draft_pdf
13_restore_pdf_objects
14_optimize_pdf
15_validate_output
16_render_diff
```

## 단계별 정의

| 단계 | 주 담당 | 입력 | 출력 | 상태 파일 |
|---|---|---|---|---|
| 01_validate_pdf | QPDF | 원본 PDF | validation report | `state/validation.json` |
| 02_extract_pdf_objects | pikepdf | 원본 PDF | object/resource/image manifest | `state/object-manifest.json` |
| 03_render_pages | PDFium | 원본 PDF | page PNG | `state/render-source.json` |
| 04_extract_text_bbox | PDFium | 원본 PDF | text/glyph bbox | `state/text-bbox.json` |
| 05_analyze_fonts | Poppler | 원본 PDF | font/glyph report | `state/font-report.json` |
| 06_detect_tables | pdfplumber | 원본 PDF + text bbox | table layout | `state/table-layout.json` |
| 07_extract_ocr_text | PaddleOCR | page PNG + image objects | OCR text bbox | `state/ocr-layout.json` |
| 08_build_translation_units | Python | text/table/OCR layout | translation segment queue | `state/segments.json`, `state/segments.sqlite` |
| 09_translate | Python | segment queue + glossary + TM | translated segments | `state/translated.json`, `state/tm.sqlite` |
| 10_shape_translated_text | HarfBuzz | translated segments | shaped glyph runs | `state/shaped-runs.json` |
| 11_layout_translated_text | Pango | shaped runs + page constraints | positioned text layout | `state/positioned-layout.json` |
| 12_build_draft_pdf | Cairo | object manifest + positioned layout | draft PDF | `pdf/draft.pdf`, `state/build-report.json` |
| 13_restore_pdf_objects | pikepdf | draft PDF + object manifest | enriched PDF | `pdf/enriched.pdf`, `state/restore-report.json` |
| 14_optimize_pdf | QPDF | enriched PDF | optimized PDF | `pdf/optimized.pdf`, `state/optimize-report.json` |
| 15_validate_output | QPDF | optimized PDF | validation report | `state/output-validation.json` |
| 16_render_diff | PDFium | 원본 PDF + optimized PDF | diff images/report | `state/render-diff.json` |

## 상태 저장 규칙

모든 단계는 공통 job 디렉토리 안에서 상태를 읽고 쓴다.

```text
work/<job-id>/
├── state/
├── pages/
├── objects/
├── layout/
├── pdf/
└── reports/
```

### `state/job.json`

전체 job 상태를 관리한다.

```json
{
  "jobId": "source-20260510-001",
  "sourcePdf": "input/source.pdf",
  "sourceLang": "en",
  "targetLang": "kr",
  "status": "running",
  "currentStep": "04_extract_text_bbox",
  "createdAt": "2026-05-10T00:00:00.000Z",
  "updatedAt": "2026-05-10T00:00:00.000Z"
}
```

### `state/artifacts.json`

단계별 산출물 경로를 기록한다.

```json
{
  "sourcePdf": "input/source.pdf",
  "validation": "state/validation.json",
  "objectManifest": "state/object-manifest.json",
  "textBbox": "state/text-bbox.json",
  "tableLayout": "state/table-layout.json",
  "ocrLayout": "state/ocr-layout.json",
  "segments": "state/segments.json",
  "translated": "state/translated.json",
  "positionedLayout": "state/positioned-layout.json",
  "draftPdf": "pdf/draft.pdf",
  "enrichedPdf": "pdf/enriched.pdf",
  "optimizedPdf": "pdf/optimized.pdf",
  "renderDiff": "state/render-diff.json"
}
```

## 상태 파일 형식

| 상태 | 형식 | 이유 |
|---|---|---|
| job 상태 | JSON | 모든 언어에서 읽고 쓰기 쉽다. |
| artifact manifest | JSON | 파일 경로와 단계 산출물 관리에 적합하다. |
| text bbox | JSON | page/line/span/glyph 구조 표현에 적합하다. |
| table layout | JSON | cell/row/column 계층 구조 표현에 적합하다. |
| OCR 결과 | JSON | bbox와 confidence 저장에 적합하다. |
| glossary | CSV | 사람이 편집하기 쉽다. |
| Translation Memory | SQLite | 중복 번역 방지와 조회 성능에 적합하다. |
| segment queue | SQLite 또는 JSONL | 재시도/부분 실패 관리에 적합하다. |
| render image | PNG | render diff 입력에 적합하다. |
| validation report | JSON | 단계별 성공/실패 기록에 적합하다. |

## PDF 산출물 규칙

여러 도구가 같은 PDF를 동시에 직접 수정하지 않는다.

권장 방식:

```text
원본 PDF는 읽기 전용
각 단계는 상태 파일과 중간 산출물을 생성
최종 build 단계에서 draft PDF 생성
후처리 단계에서 enriched/optimized PDF 생성
마지막 산출물만 output/ 으로 복사
```

중간 PDF:

| 파일 | 의미 |
|---|---|
| `pdf/draft.pdf` | Cairo로 생성한 1차 번역 PDF |
| `pdf/enriched.pdf` | annotation/link/bookmark 등 원본 object를 복원한 PDF |
| `pdf/optimized.pdf` | QPDF로 정리한 최종 후보 PDF |
| `output/<stem>_KR.pdf` | 최종 사용자 출력 PDF |

## 단계별 실패 처리

각 단계는 실패 시 다음 파일에 기록한다.

```text
state/error.json
```

예:

```json
{
  "step": "07_extract_ocr_text",
  "tool": "PaddleOCR",
  "message": "OCR failed on page 12",
  "recoverable": true,
  "recordedAt": "2026-05-10T00:00:00.000Z"
}
```

실패 정책:

| 실패 유형 | 처리 |
|---|---|
| PDF 구조 검사 실패 | 중단 |
| 일부 image OCR 실패 | 경고 후 계속 가능 |
| 일부 segment 번역 실패 | `translated: null` 로 기록 후 검토 필요 |
| layout overflow | quality report에 기록 |
| render diff 기준 초과 | 최종 실패 또는 수동 검토 |
| 최종 PDF validation 실패 | 중단 |

## 품질 검증 기준

v5는 결과 PDF를 만든 뒤 반드시 품질 검증을 수행한다.

| 검증 | 담당 | 산출물 |
|---|---|---|
| 구조 검증 | QPDF | `state/output-validation.json` |
| PDF/A 검증 | veraPDF | `state/pdfa-report.json` |
| render diff | PDFium | `state/render-diff.json` |
| 텍스트 누락 검사 | custom script | `state/text-coverage.json` |
| OCR coverage 검사 | OCR 결과 + segment mapping | `state/ocr-coverage.json` |
| layout overflow 검사 | Pango layout report | `state/quality-report.json` |

## 최종 출력 조건

다음 조건을 만족해야 `output/` 으로 최종 PDF를 복사한다.

- QPDF validation 통과
- 필수 text segment coverage 통과
- render diff가 허용 임계값 이하
- layout overflow가 허용 임계값 이하
- output PDF 파일 생성 확인

## 단일 shell script 책임

`run-v5.sh` 의 책임:

1. 입력 PDF 확인
2. job-id 생성
3. work 디렉토리 생성
4. 환경 변수 로드
5. 단계별 command 실행
6. 각 단계 종료 코드 확인
7. `state/job.json` 갱신
8. 실패 시 `state/error.json` 기록
9. 성공 시 최종 PDF를 `output/` 으로 복사

`run-v5.sh` 는 PDF 처리 로직을 직접 구현하지 않는다. 각 단계의 전용 도구와 script를 순서대로 호출하는 orchestrator 역할만 담당한다.

## 결론

v5 build 구조의 핵심은 다음이다.

```text
하나의 .sh 실행
여러 언어/도구 단계 호출
공통 상태 파일로 연결
원본 PDF는 읽기 전용
중간 산출물을 명시적으로 저장
최종 PDF는 조립 후 검증
품질 기준을 통과한 파일만 output/ 배치
```

## 1차 구현 완료 상태

현재 구현된 범위:

| 항목 | 상태 |
|---|---|
| `run-v5.sh` 단일 진입점 | 구현 |
| `doctor` 도구 검사 | 구현 |
| `.env` 자동 복사 | 구현 |
| `bootstrap` 설치 명령 | 구현 |
| job/state/artifact 생성 | 구현 |
| 단계별 JSON 상태 파일 | 구현 |
| SQLite segment queue | 구현 |
| Translation Memory SQLite | 구현 |
| source-copy translation mode | 구현 |
| OpenAI translation mode | 1차 구현 |
| Azure OpenAI translation mode | 1차 구현 |
| PDF validation | QPDF 우선, pikepdf degraded |
| object manifest | pikepdf 우선, PyMuPDF degraded |
| page render | PDFium 우선, PyMuPDF degraded |
| text bbox | PDFium 우선, PyMuPDF style 보강 |
| font report | Poppler `pdffonts` |
| table report | pdfplumber |
| OCR report | PaddleOCR local mode, Azure AI Vision azure mode, 기본 skip |
| OCR segment merge | PDF text와 중복되지 않는 OCR item을 translation segment에 병합 |
| HarfBuzz shaping | `uharfbuzz` 기반 glyph id/advance/offset 생성 |
| Pango layout | system `gi` binding과 PangoCairo 기반 line break/측정 |
| draft PDF 생성 | Cairo 우선, ReportLab fallback, PyMuPDF degraded |
| object restore | pikepdf metadata/root entry/page annotation 복원 |
| optimize | QPDF 우선, Ghostscript degraded |
| render diff | PDFium render, Pillow diff |
| quality report | render diff, layout, build, segment, translation, validation 요약 |
