# TODO

pdf-translate-v5의 남은 기능 구현 항목이다. 각 항목은 어떤 도구로 어떤 기능을 구현할지 기준으로 정리한다.

## 1. PDF 구조 검증과 최종 정리

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| QPDF | 원본 PDF xref, object stream, encryption, syntax 검사 구현 | `state/validation.json` |
| QPDF | 결과 PDF 구조 검사 구현 | `state/output-validation.json` |
| QPDF | 최종 PDF linearization 구현 | `pdf/optimized.pdf` |
| veraPDF | PDF/A validation 구현 | `state/pdfa-report.json` |
| Python | QPDF, pikepdf, veraPDF 결과를 하나의 validation summary로 통합 | `state/quality-report.json` |

## 2. OCR 텍스트 추출과 병합

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| PaddleOCR | page render image에서 이미지 안 텍스트 bbox 추출 구현 | `state/ocr-layout.json` |
| Azure AI Vision | cloud OCR 결과를 v5 OCR schema로 정규화 | `state/ocr-layout.json` |
| pikepdf | PDF image object 목록과 image bbox 후보 추출 | `state/object-manifest.json` |
| Python | PDF text bbox와 OCR bbox 중복 제거 고도화 | `state/segments.json` |
| Python | OCR segment를 번역 queue에 병합하고 origin을 보존 | `state/segments.sqlite` |

## 3. 번역 segment 품질

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| Python | glossary CSV를 segment 전처리에 적용 | `state/segments.json` |
| SQLite | Translation Memory exact match와 normalized match 구현 | `work/tm.sqlite` |
| OpenAI | batch translation retry, backoff, partial failure 처리 구현 | `state/translated.json` |
| Azure OpenAI | deployment 기반 batch translation retry 처리 구현 | `state/translated.json` |
| Python | 빈 번역, 과도하게 긴 번역, source-copy fallback 감지 | `state/translation-quality.json` |

## 4. 텍스트 shaping과 layout

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| HarfBuzz | glyph advance width를 layout 단계의 width 판단에 연결 | `state/shaped-runs.json` |
| Pango | bbox보다 긴 번역문에 대한 font-size 축소 구현 | `state/positioned-layout.json` |
| Pango | bbox 확장 가능 영역 계산과 line height 조정 구현 | `state/positioned-layout.json` |
| Pango | CJK word-char wrapping과 긴 단어 분할 정책 고도화 | `state/positioned-layout.json` |
| Python | overflow item을 page, segment, bbox 단위로 기록 | `state/quality-report.json` |

## 5. Font mapping과 glyph 보존

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| Poppler | 원본 font embedding, subset, encoding 분석 결과 확장 | `state/font-report.json` |
| Pango | source font family를 target fallback font family로 mapping | `state/font-map.json` |
| HarfBuzz | missing glyph 감지와 replacement glyph 기록 | `state/shaped-runs.json` |
| Cairo | bold, italic, color, opacity를 drawing 단계에 반영 | `pdf/draft.pdf` |
| Python | font substitution 결과를 quality summary에 포함 | `state/quality-report.json` |

## 6. Vector drawing 재생성

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| PyMuPDF | 원본 PDF의 rect, line, curve, stroke, fill drawing command 추출 | `state/vector-layout.json` |
| Cairo | 추출한 vector path를 새 PDF page에 재생성 | `pdf/draft.pdf` |
| Cairo | fill color, stroke color, line width, dash pattern 반영 | `pdf/draft.pdf` |
| Python | text, image, vector object의 z-order 정렬 구현 | `state/page-compose.json` |
| PDFium | vector 재생성 전후 render diff 측정 | `state/render-diff.json` |

## 7. 이미지 보존과 재배치

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| pikepdf | 원본 image XObject 추출과 metadata 기록 | `objects/images/` |
| Pillow | image format, alpha, size 정보 정규화 | `state/image-layout.json` |
| Cairo | image를 원본 bbox 기준으로 새 PDF에 drawing | `pdf/draft.pdf` |
| Python | image 위 OCR 번역 텍스트 overlay 순서 계산 | `state/page-compose.json` |
| PDFium | image 누락과 위치 변경 render diff 기록 | `state/render-diff.json` |

## 8. Table 구조 보존

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| pdfplumber | table cell, row, column 추정 결과 정규화 | `state/table-layout.json` |
| Python | table cell별 translation segment 생성 | `state/segments.json` |
| Pango | cell bbox 안에서 번역문 line break 계산 | `state/positioned-layout.json` |
| Cairo | table border와 cell background 재생성 | `pdf/draft.pdf` |
| Python | cell overflow와 table 구조 깨짐을 quality report에 기록 | `state/quality-report.json` |

## 9. PDF object 복원

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| pikepdf | document metadata와 XMP metadata 복원 고도화 | `pdf/enriched.pdf` |
| pikepdf | bookmark outline 추출과 output page target 복원 | `pdf/enriched.pdf` |
| pikepdf | external URL link annotation 복원 | `pdf/enriched.pdf` |
| pikepdf | internal page link annotation 좌표 변환과 복원 | `pdf/enriched.pdf` |
| pikepdf | attachment와 embedded file 보존 | `pdf/enriched.pdf` |

## 10. Form과 annotation 처리

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| Apache PDFBox | AcroForm field tree 추출 | `state/form-layout.json` |
| Apache PDFBox | widget annotation과 appearance stream 추출 | `state/form-layout.json` |
| Apache PDFBox | output PDF에 form field 재생성 | `pdf/enriched.pdf` |
| pikepdf | non-form annotation subtype별 복원 | `pdf/enriched.pdf` |
| Python | form 복원 실패 항목을 quality report에 기록 | `state/quality-report.json` |

## 11. 구조 태그와 접근성

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| pikepdf | tagged PDF 여부와 structure tree 존재 여부 감지 | `state/structure-report.json` |
| pikepdf | logical structure tree 보존 가능 항목 추출 | `state/structure-report.json` |
| Python | 새 PDF의 page content와 structure tag mapping 정책 구현 | `state/structure-map.json` |
| pikepdf | 보존 가능한 structure entry를 output PDF에 복원 | `pdf/enriched.pdf` |
| Python | 보존 불가 tag를 quality report에 기록 | `state/quality-report.json` |

## 12. 품질 검증

| 도구 | 구현할 기능 | 산출물 |
|---|---|---|
| PDFium | 원본과 결과 PDF를 같은 scale로 render | `pages/source/`, `pages/output/` |
| Pillow | page별 pixel diff와 threshold 판정 구현 | `state/render-diff.json` |
| Python | source segment와 output segment의 text coverage 계산 | `state/text-coverage.json` |
| Python | OCR segment coverage 계산 | `state/ocr-coverage.json` |
| Python | validation, render diff, text coverage, OCR coverage를 통합 판정 | `state/quality-report.json` |