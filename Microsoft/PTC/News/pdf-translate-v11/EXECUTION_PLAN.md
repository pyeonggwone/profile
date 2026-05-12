# EXECUTION_PLAN.md — pdf-translate-v11 실행계획

이 문서는 `pdf-translate-v11` 을 실제 구현할 때의 실행계획을 정의한다.

목표는 원본 PDF를 번역 PDF로 만드는 것이다. 구현 난이도는 고려하지 않고, 기능별 최적 도구를 연결한다.

## 실행 원칙

- 사용자는 `run-v11.sh` 하나만 실행한다.
- `run-v11.sh` 는 orchestrator다.
- 각 단계는 필요한 언어와 도구로 구현한다.
- 모든 단계는 공통 상태 파일을 읽고 쓴다.
- 원본 PDF는 읽기 전용이다.
- 중간 PDF는 단계별로 생성할 수 있다.
- 최종 PDF만 `output/` 으로 배치한다.

## 전체 단계

```text
00_doctor
01_init_job
02_validate_source_pdf
03_extract_object_manifest
04_render_source_pages
05_extract_text_bbox
06_analyze_fonts
07_detect_tables
08_extract_image_text
09_build_segments
10_translate_segments
11_shape_text
12_layout_text
13_build_draft_pdf
14_restore_pdf_objects
15_optimize_pdf
16_validate_output_pdf
17_render_diff
18_publish_output
```

## 단계별 실행계획

| 순서 | 단계 | 담당 도구 | 목적 | 완료 조건 |
|---|---|---|---|---|
| 00 | doctor | shell | 필수 도구 설치 확인 | 모든 필수 도구 version 확인 |
| 01 | init_job | Python | job-id, work dir, state 초기화 | `state/job.json` 생성 |
| 02 | validate_source_pdf | QPDF | 원본 PDF 구조 검사 | `state/validation.json` 생성, fatal 오류 없음 |
| 03 | extract_object_manifest | pikepdf | object/resource/image/annotation/link/bookmark 목록화 | `state/object-manifest.json` 생성 |
| 04 | render_source_pages | PDFium | 원본 page PNG 생성 | `pages/source/*.png` 생성 |
| 05 | extract_text_bbox | PDFium | text/glyph bbox 추출 | `state/text-bbox.json` 생성 |
| 06 | analyze_fonts | Poppler | font/glyph 상태 분석 | `state/font-report.json` 생성 |
| 07 | detect_tables | pdfplumber | table cell/row/column 추정 | `state/table-layout.json` 생성 |
| 08 | extract_image_text | PaddleOCR | 이미지 안 텍스트 OCR. Azure Vision은 cloud OCR 모드에서 별도 connector로 대체 가능 | `state/ocr-layout.json` 생성 |
| 09 | build_segments | Python | 번역 segment 생성 | `state/segments.json`, `state/segments.sqlite` 생성 |
| 10 | translate_segments | Node | LLM 번역, glossary, TM 적용 | `state/translated.json`, `state/tm.sqlite` 갱신 |
| 11 | shape_text | HarfBuzz | 번역문 glyph shaping | `state/shaped-runs.json` 생성 |
| 12 | layout_text | Pango | 줄바꿈, fallback font, CJK layout | `state/positioned-layout.json` 생성 |
| 13 | build_draft_pdf | Cairo | 새 번역 PDF 초안 생성 | `pdf/draft.pdf` 생성 |
| 14 | restore_pdf_objects | pikepdf | annotation/link/bookmark/metadata 복원 | `pdf/enriched.pdf` 생성 |
| 15 | optimize_pdf | QPDF | 구조 정리, linearization | `pdf/optimized.pdf` 생성 |
| 16 | validate_output_pdf | QPDF | 최종 PDF 구조 검증 | validation 통과 |
| 17 | render_diff | PDFium | 원본/결과 render diff | `state/render-diff.json` 생성 |
| 18 | publish_output | shell | 최종 PDF output 배치 | `output/<stem>_<TARGET>.pdf` 생성 |

## 실행 흐름

```text
run-v11.sh
  │
  ├─ load .env
  ├─ parse args
  ├─ doctor check
  ├─ create job
  ├─ run steps sequentially
  ├─ update state/job.json after each step
  ├─ stop on fatal error
  ├─ write state/error.json on failure
  └─ copy final PDF to output/
```

## 상태 전이

`state/job.json` 의 `status` 값:

| 상태 | 의미 |
|---|---|
| `created` | job 생성됨 |
| `running` | 단계 실행 중 |
| `blocked` | 수동 조치 필요 |
| `failed` | fatal 실패 |
| `completed` | 최종 PDF 생성 완료 |

`currentStep` 은 현재 단계명을 기록한다.

```json
{
  "jobId": "source-20260510-001",
  "status": "running",
  "currentStep": "10_translate_segments"
}
```

## 실패 정책

| 실패 위치 | 정책 |
|---|---|
| doctor 실패 | 중단 |
| 원본 PDF validation 실패 | 중단 |
| object manifest 실패 | 중단 |
| page render 일부 실패 | 중단 또는 해당 page blocked |
| text bbox 일부 누락 | 경고 후 OCR 보완 |
| OCR 일부 실패 | 경고 후 계속 가능 |
| 번역 일부 실패 | segment별 `translated: null`, 품질 검증에서 차단 가능 |
| shaping/layout overflow | quality report 기록 후 기준 초과 시 차단 |
| draft PDF 생성 실패 | 중단 |
| object restore 실패 | 중단 또는 degraded output 표시 |
| final validation 실패 | 중단 |
| render diff 기준 초과 | 차단 또는 수동 검토 |

## 산출물 흐름

```text
input/source.pdf
  │
  ├─ state/validation.json
  ├─ state/object-manifest.json
  ├─ pages/source/page-0001.png
  ├─ state/text-bbox.json
  ├─ state/font-report.json
  ├─ state/table-layout.json
  ├─ state/ocr-layout.json
  ├─ state/segments.json
  ├─ state/translated.json
  ├─ state/shaped-runs.json
  ├─ state/positioned-layout.json
  ├─ pdf/draft.pdf
  ├─ pdf/enriched.pdf
  ├─ pdf/optimized.pdf
  ├─ state/render-diff.json
  └─ output/source_KR.pdf
```

## 구현 순서

품질 우선 구조이지만 구현은 단계별로 검증 가능하게 나눈다.

| 구현 순서 | 범위 | 목표 |
|---|---|---|
| 1 | state schema | 모든 단계가 상태 파일을 공유하는 뼈대 확보 |
| 2 | QPDF validation | 원본 PDF 구조 검사 확보 |
| 3 | pikepdf manifest | 원본 object 분석 기반 확보 |
| 4 | PDFium render | 기준 렌더러 확보 |
| 5 | PDFium text bbox | 기준 좌표 확보 |
| 6 | LLM translation | 번역 데이터 흐름 확보 |
| 7 | HarfBuzz shaping | CJK glyph shaping 품질 확보 |
| 8 | Pango text layout | CJK layout 품질 확보 |
| 9 | Cairo draft PDF | 새 PDF 생성 확보 |
| 10 | pikepdf object restore | annotation/link/bookmark 보존 |
| 11 | QPDF optimize | 최종 PDF 안정화 |
| 12 | PDFium render diff | 자동 품질 검증 |
| 13 | OCR/table/form 확장 | 누락 영역 보완 |

## 완료 기준

v11 실행계획이 완료되었다고 보는 기준:

- `run-v11.sh input/source.pdf` 로 전체 pipeline 실행 가능
- 최종 `output/<stem>_KR.pdf` 생성
- 모든 상태 파일 생성
- QPDF validation 통과
- 필수 text coverage 통과
- render diff report 생성
- 실패 시 단계/원인/복구 가능 여부가 `state/error.json` 에 기록

## 결론

v11 실행계획은 단일 엔진 구현이 아니라, 기능별 최적 도구를 `.sh` 파이프라인으로 연결하는 방식이다. 핵심은 각 단계의 언어가 아니라 공통 상태 schema와 산출물 계약이다.
