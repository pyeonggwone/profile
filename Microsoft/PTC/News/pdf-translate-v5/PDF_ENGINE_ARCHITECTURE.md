# pdf-translate-v5 PDF 엔진 설계

이 문서는 `pdf-translate-v5` 에서 목표로 삼을 PDF 처리 엔진 구성을 정리한다. 구현 난이도는 고려하지 않고, PDF 번역/재생성 품질과 호환성을 기준으로 기능별 주 담당 엔진을 하나씩 분리한다.

Adobe / Apryse 계열은 제외한다.

## 목표

v5의 목표는 PyMuPDF 단일 파이프라인에서 벗어나, PDF 처리 기능을 역할별로 나누어 가장 적합한 엔진에 연결하는 것이다.

핵심 방향:

- 원본 PDF 위에 번역문을 덧씌우지 않는다.
- 새 PDF를 생성한다.
- 원본의 구조, 이미지, 도형, 표, 주석, 링크, bookmark를 최대한 보존한다.
- 텍스트 누락을 막는다.
- 이미지 안 텍스트는 OCR로 보완한다.
- 최종 결과는 render diff로 검증한다.
- 구현 난이도보다 품질과 호환성을 우선한다.

## 기능별 주 담당 엔진

| 기능 | 주 담당 엔진/도구 | 담당 범위 | 선택 이유 |
|---|---|---|---|
| PDF 파일 무결성 검사 | QPDF | xref, object stream, encryption, syntax 오류 확인 | PDF 구조 검증과 손상 PDF 감지에 강하다. |
| PDF 구조 정리 / linearization | QPDF | object 정리, linearization, 구조 검증 | 최종 산출물 정리와 viewer 호환성 개선에 적합하다. |
| PDF object 읽기 | pikepdf | object tree, resource dictionary, XObject, metadata 접근 | Python에서 PDF object를 세밀하게 다루기 좋다. |
| resource 보존 | pikepdf | font resource, image resource, annotation resource 식별 | 원본 object 보존 중심 처리에 적합하다. |
| 이미지 object 추출 | pikepdf | image XObject 추출 | 원본 image stream을 재압축 없이 다루기 좋다. |
| 이미지 원본 보존 / 재삽입 | pikepdf | image stream 보존, 새 PDF 연결 | 이미지 품질 손실을 줄이기 좋다. |
| annotation 복사 | pikepdf | annotation object 읽기/복사 | PDF object 수준으로 주석을 보존하기 좋다. |
| link 복사 | pikepdf | link annotation, URI/action object 보존 | 링크 정보를 object 단위로 다루기 좋다. |
| outline/bookmark 복사 | pikepdf | document outline tree 복사 | bookmark 구조 보존에 적합하다. |
| PDF page 렌더링 | PDFium | page rasterization | 실제 viewer 계열과 가까운 렌더링 결과를 얻기 좋다. |
| 텍스트 bbox 추출 | PDFium | glyph/text bbox, 좌표, page 기준 text 위치 | 렌더링 기준과 bbox 기준을 맞추기 좋다. |
| render diff 품질 검증 | PDFium | 원본/결과 PDF를 동일 렌더러로 이미지화 | 누락, 겹침, 깨짐을 자동 비교하기 좋다. |
| vector path 추출 | PDFium | path, rect, curve, stroke/fill 정보 추출 | 렌더링 기준에 가까운 vector 정보를 얻기 좋다. |
| font / glyph 상태 분석 | Poppler | font embedding, glyph 위치, substitution 분석 | font 문제와 glyph mapping 상태 관찰에 강하다. |
| 표 구조 인식 | pdfplumber | table cell, row, column 추정 | 텍스트 bbox와 선 정보를 함께 분석하기 좋다. |
| 새 PDF 문서 생성 | Cairo | PDF surface 생성, shaped text drawing | Pango layout 결과를 직접 PDF로 출력하기 좋다. |
| 번역문 glyph shaping | HarfBuzz | glyph shaping, ligature, script 처리 | 다국어 shaping 품질이 좋다. |
| 번역문 줄바꿈 / layout | Pango | line breaking, fallback font, CJK layout | 한글/중국어/일본어 줄바꿈과 font fallback에 강하다. |
| CJK 텍스트 drawing | Cairo | Pango layout 결과를 PDF surface에 drawing | shaped text와 vector drawing을 PDF로 출력하기 좋다. |
| vector drawing 재생성 | Cairo | path, stroke, fill, curve 재구성 | 원본 vector drawing을 새 PDF에 다시 그리기 좋다. |
| form / AcroForm 처리 | Apache PDFBox | form field, widget annotation, appearance stream 처리 | PDF form 처리에 강하다. |
| 로컬 OCR | PaddleOCR | 이미지 안 텍스트 추출 | 로컬 실행 기준 OCR 품질이 좋다. |
| 클라우드 OCR | Azure AI Vision | 이미지/문서 텍스트 인식 | 운영형 OCR과 문서 이미지 인식 품질이 좋다. |
| PDF 강한 재압축 | Ghostscript | 이미지 재압축, 파일 크기 감소 | 강한 압축에 유리하다. 단, 품질 손실 가능성이 있다. |
| PDF/A 검증 | veraPDF | PDF/A 표준 검증 | PDF/A 검증에 특화되어 있다. |

## v5 권장 파이프라인

```text
INPUT PDF
  │
  ▼
QPDF
  - PDF 무결성 검사
  - encryption / xref / object stream 확인
  │
  ▼
pikepdf
  - object/resource/image/annotation/link/bookmark 분석
  - 원본 보존 대상 추출
  │
  ▼
PDFium
  - page 렌더링
  - text bbox 추출
  - vector path 추출
  │
  ▼
Poppler
  - font/glyph 상태 분석
  - font substitution 문제 확인
  │
  ▼
pdfplumber
  - table cell/row/column 구조 인식
  │
  ▼
PaddleOCR
  - local mode 이미지 안 텍스트 추출
  │
  ▼
Azure AI Vision
  - azure mode 이미지 안 텍스트 추출
  - 스캔 PDF 보완
  │
  ▼
LLM Translation
  - glossary 보호
  - Translation Memory 적용
  - 원문/번역문 mapping 유지
  │
  ▼
HarfBuzz
  - 번역문 glyph shaping
  │
  ▼
Pango
  - 줄바꿈
  - fallback font
  - CJK layout
  │
  ▼
ReportLab
  - 새 PDF 문서 생성
  - page/image/text 배치
  │
  ▼
Cairo
  - vector drawing 재생성
  - shaped text drawing
  │
  ▼
pikepdf
  - annotation/link/bookmark 복사
  - metadata/resource 정리
  │
  ▼
QPDF
  - 구조 정리
  - linearization
  - 최종 validation
  │
  ▼
PDFium render diff
  - 원본/결과 page 이미지 비교
  - 누락/겹침/깨짐 검사
  │
  ▼
OUTPUT PDF
```

## 기능별 데이터 흐름

| 단계 | 입력 | 처리 | 출력 |
|---|---|---|---|
| QPDF 검사 | 원본 PDF | 구조 오류, encryption, xref 확인 | validation report |
| pikepdf object 분석 | 원본 PDF | resource, image, annotation, link, outline 추출 | object manifest |
| PDFium text 추출 | 원본 PDF | text/glyph bbox 추출 | text layout JSON |
| PDFium render | 원본 PDF | page image 생성 | baseline PNG |
| Poppler font 분석 | 원본 PDF | font/glyph 상태 확인 | font report |
| pdfplumber table 분석 | text layout + 원본 PDF | table 구조 추정 | table layout JSON |
| OCR | page image / image object | 이미지 안 텍스트 추출 | OCR text layout JSON |
| Translation | text layout JSON | 번역 / glossary / TM | translated layout JSON |
| HarfBuzz shaping | translated text | glyph shaping | shaped glyph runs |
| Pango layout | shaped text | line breaking / fallback font | positioned text layout |
| Cairo 생성 | object manifest + layout | 새 PDF 생성 | draft output PDF |
| pikepdf 후처리 | draft PDF + object manifest | annotation/link/bookmark 복사 | enriched output PDF |
| QPDF 최종 정리 | enriched output PDF | 구조 정리 / linearization | optimized output PDF |
| PDFium 검증 | 원본 PDF + 결과 PDF | render diff | quality report |

## v4와 v5의 차이

| 항목 | v4 | v5 목표 |
|---|---|---|
| PDF 처리 방식 | PyMuPDF 단일 경로 중심 | 기능별 엔진 분리 |
| PDF 구조 분석 | PyMuPDF 중심 | QPDF 검사와 pikepdf object manifest를 단계별로 분리 |
| bbox 추출 | PyMuPDF `get_text("dict")` | PDFium 기준 bbox |
| 도형 처리 | PyMuPDF `get_drawings()` | PDFium 추출 + Cairo 재생성 |
| 새 PDF 생성 | PyMuPDF `new_page()` | Cairo PDF surface 생성, ReportLab fallback |
| text layout | PyMuPDF `insert_textbox()` + custom wrapping | HarfBuzz shaping, Pango layout, Cairo drawing을 단계별로 분리 |
| 이미지 안 텍스트 | 미구현 | PaddleOCR local mode, Azure AI Vision azure mode |
| annotation/link/bookmark | 미구현 | pikepdf |
| form 처리 | 미구현 | Apache PDFBox |
| 최종 정리 | PyMuPDF clean/deflate | QPDF 중심, Ghostscript 선택 |
| 품질 검증 | self-test 중심 | PDFium render diff |

## 제외

- Adobe PDF Services
- Apryse
- 상용 SDK 전제 구조
- 원본 위 whiteout overlay를 기본으로 하는 구조

## 결론

v5는 PyMuPDF 단일 엔진으로 모든 기능을 처리하는 구조가 아니라, 기능별로 품질이 강한 엔진을 분리 연결하는 구조를 목표로 한다.

최종 기준:

```text
QPDF        -> 구조 검사 / 최종 정리
pikepdf     -> PDF object 보존
PDFium      -> bbox 추출 / 렌더링 / render diff
Poppler     -> font/glyph 분석
pdfplumber  -> 표 구조 인식
HarfBuzz    -> glyph shaping
Pango       -> text layout
Cairo       -> shaped text/vector drawing 출력
ReportLab   -> 새 PDF 문서 생성
PaddleOCR   -> 로컬 OCR
Azure Vision -> 클라우드 OCR
Apache PDFBox -> form 처리
Ghostscript -> 선택적 강한 재압축
veraPDF     -> PDF/A 검증
```
