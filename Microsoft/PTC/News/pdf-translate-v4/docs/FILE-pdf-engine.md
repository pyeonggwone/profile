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

`PDF_BUILD_MODE=overlay` 로 지정하면 v3 방식의 원본 수정 모드로 되돌릴 수 있지만, v4의 기본 목표는 rebuild 이다.

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

v4는 원본 text object를 출력 PDF에 복사하지 않기 때문에, 번역되지 않은 segment는 출력에서 빠질 수 있다. 실패한 번역은 `translated: null` 로 기록된다.

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
