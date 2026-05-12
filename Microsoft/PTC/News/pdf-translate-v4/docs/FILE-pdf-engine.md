# PDF 엔진 — pdf-translate-v4

`pdf-translate-v4` 는 PyMuPDF rebuild 방식을 기본으로 사용한다. v3 처럼 원본 PDF 위에 흰색 박스와 번역문을 덧씌우지 않고, 새 PDF를 만든 뒤 원본의 비텍스트 요소와 번역 텍스트를 다시 그린다.

## 기본 설정

```env
PDF_ENGINE=pymupdf
PDF_BUILD_MODE=rebuild
PYTHON_BIN=python3
PDF_FONT_PATH=/usr/share/fonts/truetype/nanum/NanumGothic.ttf
PDF_FONT_BOLD_PATH=/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf
```

## 엔진 선택지

현재 v4 코드에 남아 있는 PDF 엔진 선택지는 두 개다.

| 값 | 구현 | 현재 역할 |
|---|---|---|
| `PDF_ENGINE=pymupdf` | `src/pdf/pymupdf_engine.py` | v4 기본 엔진. extract, rebuild, overlay 모두 지원한다. |
| `PDF_ENGINE=pdftr` | `crates/` Rust workspace의 `pdftr` CLI | historical/debug fallback. v3 계열 incremental/overlay 성격이며 v4 rebuild 품질 목표의 주 엔진은 아니다. |

즉 `PDF_ENGINE=pymupdf` 하나만 적은 이유는 “엔진이 하나뿐”이라는 뜻이 아니라, **v4의 기본 경로를 PyMuPDF rebuild로 고정한다**는 의미다.

Rust fallback을 쓰려면 다음처럼 바꾼다.

```env
PDF_ENGINE=pdftr
PDF_ENGINE_BIN=
```

`PDF_ENGINE_BIN` 이 비어 있으면 `run-translate.sh` 가 `target/release/pdftr` 또는 `target/debug/pdftr` 를 찾고, 없으면 `cargo build --release -p pdftr_cli` 를 시도한다.

`PDF_BUILD_MODE=overlay` 로 지정하면 PyMuPDF에서도 v3 방식의 원본 수정 모드로 되돌릴 수 있지만, v4의 기본 목표는 rebuild 이다.

## 기능별 권장 엔진 연결

아래 표는 구현 난이도를 고려하지 않고, PDF 번역/재생성 품질과 호환성을 기준으로 기능별 주 담당 엔진을 하나씩 나눈 것이다. Adobe / Apryse 계열은 제외한다.

| 기능 | 주 담당 엔진/도구 | 연결 이유 | v4 현재 상태 |
|---|---|---|---|
| PDF 파일 무결성 검사 | QPDF | xref, object stream, encryption, syntax 오류 확인에 강하다. | 미연결 |
| PDF object 읽기 / resource 분석 | pikepdf | PDF object tree, resource dictionary, XObject, metadata를 Python에서 세밀하게 다루기 좋다. | 미연결 |
| PDF page 렌더링 | PDFium | 실제 viewer 계열과 가까운 렌더링 결과를 얻기 좋다. | PyMuPDF pixmap 일부 사용 |
| 텍스트 bbox 추출 | PDFium | glyph/text bbox와 렌더링 기준을 맞추기 좋다. | PyMuPDF `get_text("dict")` 사용 |
| font / glyph 상태 분석 | Poppler | font embedding, glyph 위치, substitution 문제 관찰에 강하다. | PyMuPDF span font 정보 사용 |
| 이미지 object 추출 | pikepdf | image XObject를 원본 object에 가깝게 식별하고 꺼내기 좋다. | PyMuPDF image block 복사 |
| 이미지 원본 보존 / 재삽입 | pikepdf | 원본 image stream을 재압축 손실 없이 보존하는 쪽에 적합하다. | PyMuPDF `insert_image()` 사용 |
| vector path 추출 | PDFium | path, rect, curve, stroke/fill 정보를 렌더링 기준에 가깝게 추출하기 좋다. | PyMuPDF `get_drawings()` 사용 |
| vector drawing 재생성 | Cairo | path, stroke, fill, curve를 새 PDF drawing으로 재구성하기 좋다. | PyMuPDF drawing API 사용 |
| 표 구조 인식 | pdfplumber | 텍스트 bbox와 선 정보를 이용해 table cell, row, column 추정에 유리하다. | 별도 table 인식 없음 |
| 새 PDF 문서 생성 | ReportLab | page 생성, PDF 저장, 이미지/텍스트 배치가 안정적이다. | PyMuPDF `new_page()` 사용 |
| 번역문 shaping | HarfBuzz | glyph shaping, ligature, script 처리에 강하다. | 미연결 |
| 번역문 줄바꿈 / layout | Pango | CJK line breaking, fallback font, text layout에 강하다. | PyMuPDF `insert_textbox()` + custom wrapping |
| CJK 텍스트 drawing | Cairo | Pango layout 결과를 PDF surface에 그리기 좋다. | PyMuPDF embedded font 사용 |
| annotation 복사 | pikepdf | annotation object를 직접 읽고 새 PDF에 옮기기 좋다. | 미구현 |
| link 복사 | pikepdf | link annotation과 URI/action object 보존에 적합하다. | 미구현 |
| outline/bookmark 복사 | pikepdf | document outline tree 복사와 수정에 적합하다. | 미구현 |
| form / AcroForm 처리 | Apache PDFBox | form field, widget annotation, appearance stream 처리에 강하다. | 미구현 |
| 로컬 OCR | PaddleOCR | 로컬 실행 기준 이미지 안 텍스트 인식 품질이 좋다. | 미구현 |
| 클라우드 OCR | Azure AI Vision | 운영형 OCR과 문서 이미지 텍스트 인식 품질이 좋다. | 미구현 |
| PDF 구조 정리 / linearization | QPDF | object 정리, linearization, 구조 검증에 적합하다. | PyMuPDF clean 저장 사용 |
| PDF 강한 재압축 | Ghostscript | 파일 크기 감소에 강하지만 이미지 품질 손실 가능성이 있다. | 미연결 |
| render diff 품질 검증 | PDFium | 원본/결과 PDF를 같은 렌더러로 이미지화해 비교하기 좋다. | 작은 self-test 중심 |
| PDF/A 검증 | veraPDF | PDF/A 표준 검증에 특화되어 있다. | 미구현 |

품질 기준의 목표 연결은 다음처럼 기능별로 분리한다.

```text
QPDF        -> PDF 무결성 검사, 구조 정리, linearization
pikepdf     -> object/resource/image/annotation/link/bookmark 보존
PDFium      -> page 렌더링, text bbox 추출, render diff
Poppler     -> font/glyph 상태 분석
pdfplumber  -> table 구조 인식
HarfBuzz    -> glyph shaping
Pango       -> 줄바꿈, fallback font, CJK layout
Cairo       -> vector drawing 재생성, shaped text drawing
ReportLab   -> 새 PDF 문서 생성
PaddleOCR   -> 로컬 OCR
Azure Vision -> 클라우드 OCR
Ghostscript -> 선택적 강한 재압축
veraPDF     -> PDF/A 검증
```

따라서 v4의 PyMuPDF 단일 경로는 빠른 rebuild 구현을 위한 현재 구현이고, 최종 품질 기준으로는 위처럼 기능별 주 담당을 분리해 연결하는 구조가 더 적합하다.

## EXTRACT

`src/pdf/pymupdf_engine.py text <pdf> --json` 은 페이지별 텍스트 span을 추출한다.

응답은 기존 Node 파이프라인과 호환되도록 다음 형태를 유지한다.

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
        "y": 120.0,
        "left": 72.0,
        "right": 140.0,
        "top": 108.0,
        "bottom": 124.0,
        "font_size": 12.0,
        "font": "Arial-BoldMT",
        "color_rgb": [0, 0, 0],
        "bg_color": [1, 1, 1],
        "bold": true,
        "italic": false
      }
    ]
  }
]
```

추출 정보:

- bbox: `left/right/top/bottom/width/height`
- typography: `font_size`, `font`, `bold`, `italic`, `serif`, `monospace`, `flags`
- color: `color_rgb`
- sampled background: `bg_color`

## TRANSLATE

Node 파이프라인은 EXTRACT 결과를 line/visual segment 단위로 묶고, Translation Memory 와 glossary masking 을 적용한 뒤 LLM 번역을 수행한다.

v4는 원본 text object를 출력 PDF에 복사하지 않기 때문에, 표시해야 하는 텍스트는 모두 edit로 다시 써야 한다.

- `translated === original` 이어도 rebuild 모드에서는 edit를 생성한다.
- 실패한 번역은 `translated: null` 로 기록되며 현재 출력에 포함되지 않는다.
- 도형 안 글자가 실제 PDF text object이면 일반 span과 동일하게 추출된다.
- 도형 안 글자가 이미지 픽셀이나 vector outline이면 OCR/vision pass 없이는 추출되지 않는다.

## APPLY / REBUILD

`src/pdf/pymupdf_engine.py edit <input> <output> --edits <json>` 은 기본적으로 rebuild 모드로 동작한다.

처리 순서:

1. 원본 PDF를 읽어 page size를 가져온다.
2. 새 `fitz.open()` 문서를 만든다.
3. 각 페이지에 같은 크기의 blank page를 만든다.
4. 원본 page의 image block을 `insert_image()` 로 복사한다.
5. 원본 page의 vector drawing을 `page.get_drawings()` 기반으로 다시 그린다.
6. 원본 text object는 복사하지 않는다.
7. 번역 텍스트만 `AddTextBoxEmbedded` edit로 삽입한다.
8. 저장 전 `subset_fonts()` 를 호출해 CJK embedded font 크기를 줄인다.
9. `garbage=4`, `deflate=True`, `clean=True` 로 저장한다.

## Text Fitting

`insert_textbox()` 는 번역문이 원래 bbox보다 길어져 잘리는 문제를 줄이기 위해 다음 순서로 삽입을 시도한다.

1. 원래 bbox에 `page.insert_textbox()` 를 시도한다.
2. 실패하면 같은 page 안에서 width/height를 확장한다.
3. `wrap_text_to_width()` 로 긴 한글/긴 토큰을 줄바꿈한다.
4. font size를 0.5pt 단위로 줄이며 다시 시도한다.
5. 그래도 실패하면 page의 남은 영역에 4pt fallback 텍스트를 줄 단위로 삽입한다.

이 방식은 텍스트 누락보다 시각적 overflow를 더 허용하는 쪽으로 설계되어 있다. 즉 v4의 현재 우선순위는 “텍스트를 생략하지 않기”이다.

## 지원하는 EditOperation

v4 rebuild 모드에서 주로 사용하는 operation:

```json
{
  "type": "AddTextBoxEmbedded",
  "page": 1,
  "x": 72.0,
  "y": 108.0,
  "width": 120.0,
  "height": 18.0,
  "text": "번역 텍스트",
  "fontPath": "/mnt/c/Windows/Fonts/malgun.ttf",
  "fontName": "PDFTrRegular",
  "size": 10.5,
  "color": [0, 0, 0]
}
```

`FillRect` 는 overlay 모드에서 원문을 덮기 위한 operation 이다. rebuild 모드에서는 원문 text object가 애초에 복사되지 않으므로 Node 파이프라인이 `FillRect` 를 만들지 않는다.

## 한계

- 복잡한 shading, pattern, transparency, blend mode는 `page.get_drawings()` 로 완전히 복원되지 않을 수 있다.
- annotations, links, outlines/bookmarks는 아직 복사하지 않는다.
- 이미지에 박힌 텍스트는 OCR/vision pass 없이는 번역되지 않는다.
- 원본 PDF의 모든 내부 object 구조를 보존하는 것이 아니라 시각 구조를 재구성한다.

## fallback

Rust `pdftr` workspace 는 historical fallback 으로 남아 있다. v4 기본 경로는 PyMuPDF rebuild 이며, `PDF_ENGINE=pdftr` 는 디버그/비교용이다.
