# 구현 현황

이 문서는 pdf-translate-v11에서 지금까지 실제로 구현된 내용만 정리한다.

## 실행 구조

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| 단일 실행 진입점 구현 | Bash | `run-v11.sh` |
| Python pipeline module 실행 연결 | Bash, Python | `python -m pdf_translate_v11.pipeline` |
| job id 생성과 작업 디렉터리 생성 | Python | `work/<job-id>/` |
| 단계별 state 저장 구조 구현 | Python, JSON | `work/<job-id>/state/*.json` |
| 중간 PDF 저장 구조 구현 | Python | `work/<job-id>/pdf/` |
| 최종 PDF 출력 구조 구현 | Python | `output/<stem>_KR.pdf` |

## Pipeline 단계

| 단계 | 구현 내용 | 산출물 |
|---|---|---|
| `01_init_job` | job metadata 생성 | `state/job.json` |
| `02_validate_source_pdf` | 원본 PDF validation 실행 | `state/validation.json` |
| `03_extract_object_manifest` | PDF object manifest 생성 | `state/object-manifest.json` |
| `04_render_source_pages` | 원본 page render image 생성 | `pages/source/*.png`, `state/render-source.json` |
| `05_extract_text_bbox` | PDF text bbox 추출 | `state/text-bbox.json` |
| `06_analyze_fonts` | font report 생성 | `state/font-report.json` |
| `07_detect_tables` | table layout report 생성 | `state/table-layout.json` |
| `08_extract_image_text` | OCR layout schema 생성 | `state/ocr-layout.json` |
| `09_build_segments` | translation segment 생성 | `state/segments.json`, `state/segments.sqlite` |
| `10_translate_segments` | translation state 생성 | `state/translated.json` |
| `11_shape_text` | glyph shaping 실행 | `state/shaped-runs.json` |
| `12_layout_text` | positioned text layout 생성 | `state/positioned-layout.json` |
| `13_build_draft_pdf` | 새 PDF 초안 생성 | `pdf/draft.pdf`, `state/build-report.json` |
| `14_restore_pdf_objects` | metadata/root entry/page annotation 복원 | `pdf/enriched.pdf`, `state/restore-report.json` |
| `15_optimize_pdf` | optimized PDF 생성 | `pdf/optimized.pdf`, `state/optimize-report.json` |
| `16_validate_output_pdf` | 결과 PDF validation 실행 | `state/output-validation.json` |
| `17_render_diff` | 원본/결과 render diff 생성 | `state/render-diff.json`, `state/quality-report.json` |
| `18_publish_output` | 최종 PDF output 배치 | `output/<stem>_KR.pdf`, `state/publish-report.json` |

## PDF validation

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| QPDF CLI 감지 | Python, `shutil.which` | `doctor` report |
| QPDF 사용 가능 시 `qpdf --check` 실행 | QPDF | `state/validation.json`, `state/output-validation.json` |
| QPDF 미사용 시 pikepdf validation fallback 실행 | pikepdf | `state/validation.json`, `state/output-validation.json` |
| PyMuPDF validation fallback 구현 | PyMuPDF | `state/validation.json`, `state/output-validation.json` |

## PDF object 분석과 복원

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| PDF page count 추출 | pikepdf | `state/object-manifest.json` |
| PDF object count 추출 | pikepdf | `state/object-manifest.json` |
| document info metadata 추출 | pikepdf | `state/object-manifest.json` |
| root key 목록 추출 | pikepdf | `state/object-manifest.json` |
| page annotation count 추출 | pikepdf | `state/object-manifest.json` |
| draft PDF에 docinfo 복원 | pikepdf | `pdf/enriched.pdf` |
| root entry 일부 복원 | pikepdf | `pdf/enriched.pdf` |
| page annotation 일부 복원 | pikepdf | `pdf/enriched.pdf` |

## Page render와 text bbox

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| 원본 PDF page PNG render | PDFium | `pages/source/*.png` |
| 결과 PDF page PNG render | PDFium | `pages/output/*.png` |
| PDFium 미사용 시 PyMuPDF render fallback | PyMuPDF | `pages/source/*.png`, `pages/output/*.png` |
| PDF text line bbox 추출 | PDFium | `state/text-bbox.json` |
| text style metadata 보강 | PyMuPDF | `state/text-bbox.json` |
| page width/height 기록 | PDFium | `state/text-bbox.json` |

## Font와 table 분석

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| `pdffonts` 실행 결과 저장 | Poppler | `state/font-report.json` |
| Poppler 미사용 시 degraded font report 생성 | Python | `state/font-report.json` |
| table 후보 추출 | pdfplumber | `state/table-layout.json` |
| pdfplumber 미사용 시 degraded table report 생성 | Python | `state/table-layout.json` |

## OCR 처리

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| OCR mode schema 구현 | Python | `state/ocr-layout.json` |
| OCR off mode 구현 | Python | `state/ocr-layout.json` |
| PaddleOCR local connector 구현 | PaddleOCR | `state/ocr-layout.json` |
| Azure AI Vision OCR connector 구현 | Azure AI Vision REST API | `state/ocr-layout.json` |
| OCR item page/bbox/text schema 정규화 | Python | `state/ocr-layout.json` |
| OCR item과 PDF text 중복 제거 | Python | `state/segments.json` |
| OCR item을 translation segment에 병합 | Python | `state/segments.json` |

## Segment와 translation state

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| PDF text bbox를 translation segment로 변환 | Python | `state/segments.json` |
| OCR text를 translation segment로 변환 | Python | `state/segments.json` |
| segment origin 기록 | Python | `state/segments.json` |
| segment queue SQLite 저장 | SQLite | `state/segments.sqlite` |
| Translation Memory table 생성 | SQLite | `work/tm.sqlite` |
| source-copy translation mode 구현 | Python | `state/translated.json` |
| OpenAI translation connector 구현 | OpenAI SDK | `state/translated.json` |
| Azure OpenAI translation connector 구현 | OpenAI SDK | `state/translated.json` |
| translation stats 생성 | Python | `state/translated.json` |

## Glyph shaping

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| font path 선택 구현 | Python | `state/shaped-runs.json` |
| glyph id 생성 | HarfBuzz, `uharfbuzz` | `state/shaped-runs.json` |
| glyph cluster 기록 | HarfBuzz, `uharfbuzz` | `state/shaped-runs.json` |
| glyph advance/offset 계산 | HarfBuzz, `uharfbuzz` | `state/shaped-runs.json` |
| shaped/degraded count 기록 | Python | `state/shaped-runs.json` |

## Text layout

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| system site-packages 기반 `gi` binding 감지 | Python | `doctor` report |
| Pango layout 생성 | Pango, PangoCairo | `state/positioned-layout.json` |
| line wrapping 계산 | Pango | `state/positioned-layout.json` |
| line metrics 기록 | Pango | `state/positioned-layout.json` |
| measured width/height 기록 | Pango | `state/positioned-layout.json` |
| overflow item count 기록 | Python | `state/positioned-layout.json` |
| Pango 미사용 시 custom width wrapper fallback | Python | `state/positioned-layout.json` |

## PDF 생성

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| PDF surface 생성 | Cairo | `pdf/draft.pdf` |
| Pango layout 결과를 PDF에 drawing | Cairo, PangoCairo | `pdf/draft.pdf` |
| text color 반영 | Cairo | `pdf/draft.pdf` |
| page size 반영 | Cairo | `pdf/draft.pdf` |
| Cairo 실패 시 ReportLab fallback | ReportLab | `pdf/draft.pdf` |
| ReportLab 실패 시 PyMuPDF fallback | PyMuPDF | `pdf/draft.pdf` |

## PDF optimize

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| QPDF linearize 실행 경로 구현 | QPDF | `pdf/optimized.pdf` |
| QPDF 미사용 시 Ghostscript optimize fallback 실행 | Ghostscript | `pdf/optimized.pdf` |
| Ghostscript 실패 시 enriched PDF copy fallback | Python | `pdf/optimized.pdf` |
| optimize 결과 report 생성 | Python | `state/optimize-report.json` |

## Quality report

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| 원본/결과 page render diff 계산 | PDFium, Pillow | `state/render-diff.json` |
| 평균 diff와 최대 diff 계산 | Pillow, Python | `state/render-diff.json` |
| render diff threshold 판정 | Python | `state/quality-report.json` |
| segment origin count 요약 | Python | `state/quality-report.json` |
| translation stats 요약 | Python | `state/quality-report.json` |
| layout status 요약 | Python | `state/quality-report.json` |
| build engine 요약 | Python | `state/quality-report.json` |
| validation status 요약 | Python | `state/quality-report.json` |

## Doctor

| 구현 내용 | 사용 도구 | 산출물 |
|---|---|---|
| CLI command availability 확인 | Python | `doctor` JSON |
| Python module availability 확인 | Python | `doctor` JSON |
| missing required tool 목록 생성 | Python | `doctor` JSON |
| qpdf, pdffonts, gs, java, node, sqlite3 확인 | Python | `doctor` JSON |
| pikepdf, pdfplumber, reportlab, pypdfium2, PyMuPDF, Pillow, numpy, cv2, openai, uharfbuzz, cairo, gi 확인 | Python | `doctor` JSON |

## 검증된 smoke 결과

| 검증 항목 | 결과 | 근거 파일 |
|---|---|---|
| pipeline 완료 | `completed` | `work/phase2-smoke-20260510-101412/state/job.json` |
| HarfBuzz shaping | `shaped=3`, `degraded=0` | `work/phase2-smoke-20260510-101412/state/shaped-runs.json` |
| Pango layout | `pangoLayoutItems=3`, `overflowItems=0` | `work/phase2-smoke-20260510-101412/state/positioned-layout.json` |
| Cairo PDF build | `engine=cairo`, `textLayout=Pango` | `work/phase2-smoke-20260510-101412/state/build-report.json` |
| render diff | `maxMeanDiff=11.530013227513228` | `work/phase2-smoke-20260510-101412/state/quality-report.json` |
| quality report | `status=ok` | `work/phase2-smoke-20260510-101412/state/quality-report.json` |
| final output 생성 | `output/phase2-smoke_KR.pdf` | `work/phase2-smoke-20260510-101412/state/publish-report.json` |

## 현재 구현 결과의 정확한 의미

현재 smoke 검증은 `source-copy` translation 결과로 수행되었다.
즉, 새 PDF 생성 pipeline은 끝까지 동작하지만 실제 OpenAI 번역 결과 PDF를 생성했다고 말할 수는 없다.