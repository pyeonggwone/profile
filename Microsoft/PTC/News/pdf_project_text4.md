# PDF 텍스트 기능별 대표 지원 제품

기준: 유료 상용 SDK 후보는 제외했다. 각 기능 행은 `pdf_project_text2.md`의 기능 이름을 그대로 사용했다. 각 행에서는 직접 `지원`하는 제품 중 지원 합계가 가장 높은 제품 하나만 적고, 나머지 제품은 `-`로 적었다. 직접 `지원` 제품이 없으면 `부분` 지원 제품 중 지원 합계가 가장 높은 제품을 적었다.

| 기능 | PyMuPDF | Apache PDFBox | PyMuPDF OCR/Tesseract |
|---|---|---|---|
| PDF object/page 접근 | 지원: `pymupdf.open()`, `Document`, `Page` | - | - |
| Page content stream 접근/해석 | - | 지원: `PDFStreamEngine.processPage(PDPage)` | - |
| Content stream decode/uncompress | - | 지원: `PDFStreamEngine.processPage()` | - |
| Content stream 재작성 | - | 지원: `PDPageContentStream` | - |
| Font resource/name/type | 지원: `Page.get_fonts()`, span `font` | - | - |
| Embedded font 여부 | 지원: `Page.get_fonts()` | - | - |
| Encoding/CMap/ToUnicode/Glyph code | 지원: `TextPage.extractRAWDICT()`, char `c` | - | - |
| Unicode text extraction | 지원: `Page.get_text("text")` | - | - |
| 글자/글리프 단위 위치 | 지원: `TextPage.extractRAWDICT()`, char `bbox`, `origin` | - | - |
| Glyph width/advance/font size | 지원: span `size`, char bbox | - | - |
| Text matrix/CTM/rotation/skew | 지원: line `dir`, `recover_quad()`, `recover_char_quad()` | - | - |
| Curved/rotated text 글자별 배치 | 지원: `recover_quad()`, `recover_line_quad()` | - | - |
| Text state: spacing/leading/rise/render mode | - | 지원: `PDFStreamEngine.getGraphicsState()`, `applyTextAdjustment()` | - |
| Fill/stroke color/color space | 지원: span `color`, `sRGB_to_rgb()` | - | - |
| Opacity/blend/layer/OCG | 지원: span `alpha`, `Page.get_drawings()` opacity/layer | - | - |
| Text bbox/baseline/position | 지원: span/char `bbox`, `origin` | - | - |
| Writing direction/vertical writing | 지원: line `wmode`, `dir` | - | - |
| Ligature/Unicode mapping 보존 | 부분: `TEXT_PRESERVE_LIGATURES` flags | - | - |
| Kerning/TJ adjustment | - | 지원: `showTextStrings(COSArray)`, `applyTextAdjustment()` | - |
| Draw order | - | 지원: `processOperator()`/`showGlyph()` 호출 순서 | - |
| Marked content/ActualText/Alt text | - | 지원: `PDFMarkedContentExtractor` | - |
| Plain text export | 지원: `Page.get_text()` | - | - |
| HTML/XML/JSON structured export | 지원: `Page.get_text("json")`, `rawjson`, `html`, `xml` | - | - |
| Bold/Italic 자동 판정 | 지원: span `flags`, `TEXT_FONT_BOLD`, `TEXT_FONT_ITALIC` | - | - |
| Fake bold 자동 판정 | 부분: `char_flags` filled/stroked 참고 | - | - |
| Underline/Strikethrough 자동 추출 | 지원: span `char_flags` bit 0 strikeout, bit 1 underline | - | - |
| Highlight/background 자동 추출 | 부분: `Page.get_drawings()`와 text bbox 매칭 | - | - |
| Word/HTML식 style model | 부분: span dict로 직접 변환 | - | - |
| Path/outline text 복원 | - | - | 부분: `Page.get_textpage_ocr()`로 시각 OCR만 가능 |
| Bidi/RTL/reading order | 부분: `sort=True`, direction info | - | - |
| 원본 text state JSON export/rewrite | 부분: raw JSON은 추출 결과 중심 | - | - |
| 원본 content stream 동일 재현 | - | - | - |
