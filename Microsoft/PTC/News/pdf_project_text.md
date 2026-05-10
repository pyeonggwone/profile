# PDF 텍스트 기능 비교

기준: 공식 문서/API/CLI에서 확인되는 기능만 함수명, 클래스명, 명령어명으로 표기한다. `공식 고수준 API 없음`은 PDF 객체나 content stream에 저수준 접근은 가능하더라도 해당 텍스트 기능을 공식 기능으로 제공하지 않는다는 뜻이다.

## 공식 지원 범위

| 텍스트 기능 | QPDF | pikepdf | Apache PDFBox | MuPDF |
|---|---|---|---|---|
| PDF object 접근 | `qpdf --json`, `qpdf --show-object`, `QPDF::writeJSON()`, `QPDF::createFromJSON()`, `QPDF::updateFromJSON()` | `pikepdf.Pdf.open()`, `pdf.Root`, `pdf.pages`, `Page.obj` | `PDDocument`, `PDPage`, `COSDictionary`, `COSObjectable.getCOSObject()` | `mutool show` |
| Page 목록/페이지 객체 접근 | `qpdf --show-pages`, `QPDF::getAllPages()` | `pdf.pages`, `pikepdf.Page`, `Page.index()`, `Page.label()` | `PDDocument.getPages()`, `PDFStreamEngine.processPage(PDPage)` | `mutool draw`, `mutool convert`, `Page.prototype.toStructuredText()` |
| Page content stream 접근 | `qpdf --show-pages`, `qpdf --show-object`, `qpdf --raw-stream-data`, `qpdf --filtered-stream-data` | `page.Contents`, `Page.contents_coalesce()`, `Page.parse_contents()` | `PDFStreamEngine.processPage(PDPage)`, `PDFStreamEngine.processChildStream(...)` | `mutool show` |
| Content stream decode/uncompress | `qpdf --filtered-stream-data`, `qpdf --stream-data=uncompress`, `qpdf --decode-level=...` | `pikepdf.parse_content_stream()`, `Page.get_filtered_contents()` | `PDFStreamEngine.processPage(PDPage)` | `mutool draw -F text`, `mutool draw -F json`, `mutool draw -F xml` |
| Content stream operator 파싱 | 공식 text semantics API 없음. 구조 확인은 `qpdf --qdf`, `qpdf --normalize-content` | `pikepdf.parse_content_stream()`, `pikepdf.Operator`, `pikepdf.TokenFilter.handle_token()` | `PDFStreamEngine.processOperator(...)`, `PDFStreamEngine.addOperator(...)`, `PDFStreamEngine.beginText()`, `PDFStreamEngine.endText()` | 원본 PDF operator API는 공식 고수준 API 없음. 구조화 결과는 `StructuredText.prototype.walk()` |
| Content stream 재작성 | `qpdf --json-output`, `qpdf --json-input`, `qpdf --update-from-json`, `QPDF::updateFromJSON()` | `pikepdf.unparse_content_stream()`, `Pdf.make_stream()`, `Page.contents_add()`, `Page.add_content_token_filter()` | `PDPageContentStream` | PDF rewrite는 `mutool clean`; 텍스트 operator 단위 재작성 API는 공식 고수준 API 없음 |
| Page resources 접근 | JSON object의 `/Resources`, `qpdf --json` | `Page.resources`, `Page.add_resource()` | `PDFStreamEngine.getResources()`, `PDResources` | `mutool show` |
| Font resources 접근 | JSON object의 `/Resources` `/Font`, `qpdf --json` | `Page.resources`, `page.resources.Font` | `PDResources.getFont(...)`, `PDFStreamEngine.getResources()`, `PDFont` | `mutool extract`, `StructuredText.prototype.asJSON()`의 `font` 정보 |
| ExtGState/resources 접근 | JSON object의 `/ExtGState`, `qpdf --json` | `Page.resources`, `Page.add_resource(..., Name.ExtGState, ...)` | `PDResources`, `PDFStreamEngine.getGraphicsState()` | `mutool show`; structured text에는 style로 자동 병합되지 않음 |
| Text object `BT`/`ET` 감지 | 공식 text semantics API 없음 | `pikepdf.parse_content_stream(page, operators="BT ET")` | `PDFStreamEngine.beginText()`, `PDFStreamEngine.endText()` | 원본 operator 감지는 공식 고수준 API 없음 |
| Text show `Tj` | 공식 text extraction API 없음 | `pikepdf.parse_content_stream(page, operators="Tj")`; text extraction은 공식 미구현 | `PDFStreamEngine.showTextString(byte[])`, `PDFStreamEngine.showText(byte[])` | `StructuredText.prototype.walk()`, `onChar(...)`, `StructuredText.prototype.asText()` |
| Text show array `TJ` | 공식 text extraction API 없음 | `pikepdf.parse_content_stream(page, operators="TJ")`; text extraction은 공식 미구현 | `PDFStreamEngine.showTextStrings(COSArray)`, `PDFStreamEngine.applyTextAdjustment(float, float)` | `StructuredText.prototype.walk()`, `onChar(...)` |
| Quote text show `'`, `"` | 공식 text extraction API 없음 | `pikepdf.parse_content_stream()`로 operator 토큰 접근만 가능 | `PDFStreamEngine.processOperator(...)`, `PDFStreamEngine.showTextString(byte[])` | `StructuredText.prototype.walk()`, `onChar(...)` |
| Font select `Tf` | 공식 text state API 없음 | `pikepdf.parse_content_stream(page, operators="Tf")` | `PDFStreamEngine.getGraphicsState()`, `PDFStreamEngine.showGlyph(..., PDFont font, ...)` | `onChar(utf, origin, font, size, quad, argb, flags)`, `StructuredText.prototype.asJSON()` |
| Font name | JSON font dictionary `/BaseFont`, `qpdf --json` | `page.resources.Font`, raw font dictionary | `PDFont.getName()` | `StructuredText.prototype.asJSON()`의 `font.name`, `onChar(..., font, ...)` |
| Font subtype/type | JSON font dictionary `/Subtype`, `qpdf --json` | `page.resources.Font`, raw font dictionary | `PDFont.getSubType()`, `PDFont.getType()` | `StructuredText.prototype.asJSON()`의 `font.family`, `font.style`, `font.weight` |
| Embedded font 여부 | font stream dictionary 저수준 확인: `qpdf --json` | raw font dictionary/stream 접근 | `PDFont.isEmbedded()`, `PDFont.getFontDescriptor()` | `mutool extract` |
| Type0/Type1/TrueType/CID font 모델 | raw font dictionary 접근만: `qpdf --json` | raw font dictionary 접근만 | `PDType0Font`, `PDType1Font`, `PDTrueTypeFont`, `PDCIDFont`, `PDFont` | structured text의 font 정보 제공. PDF font class 모델은 공식 고수준 API로 표기하지 않음 |
| Encoding/CMap/ToUnicode | raw object 접근만: `qpdf --json`; text 변환 지원 아님 | raw object 접근만; text extraction 공식 미구현 | `PDFont.readCode(InputStream)`, `PDFont.toUnicode(int)`, `PDFont.toUnicode(int, GlyphList)` | `StructuredText.prototype.asText()`, `StructuredText.prototype.asJSON()` |
| Glyph code | 공식 text extraction API 없음 | 공식 text extraction API 없음 | `PDFont.readCode(InputStream)`, `PDFStreamEngine.showGlyph(..., int code, ...)` | `onChar(...)`는 Unicode char 중심. 원본 glyph code API는 공식 고수준 API 없음 |
| Unicode text 추출 | 공식 미지원. qpdf JSON도 text extraction 미지원 | 공식 미지원. pikepdf 문서상 text extraction 미구현 | `PDFTextStripper.getText(PDDocument)`, `PDFTextStripper.writeText(PDDocument, Writer)` | `mutool draw -F text`, `mutool convert -F text`, `StructuredText.prototype.asText()` |
| 글자 단위 callback | 공식 미지원 | 공식 미지원 | `PDFTextStripper.processTextPosition(TextPosition)`, `PDFStreamEngine.showGlyph(...)` | `StructuredText.prototype.walk()`, `onChar(utf, origin, font, size, quad, argb, flags)` |
| Glyph width/advance | 공식 text/glyph API 없음 | raw font dictionary 접근만 | `PDFont.getWidth(int)`, `PDFont.getWidthFromFont(int)`, `PDFont.getDisplacement(int)`, `PDFont.getStringWidth(String)` | `onChar(..., quad, ...)`로 위치 결과 제공. 원본 advance API는 공식 고수준 API 없음 |
| Font size | `Tf` operand 저수준 접근만 | `pikepdf.parse_content_stream(page, operators="Tf")`로 operand 접근만 | `TextPosition`, `PDFStreamEngine.getGraphicsState()`, `PDFStreamEngine.showGlyph(...)` | `onChar(..., size, ...)`, `StructuredText.prototype.asJSON()`의 `font.size` |
| Text matrix/line matrix | 공식 text matrix API 없음 | `pikepdf.models.ctm.MatrixStack`, `pikepdf.models.ctm.get_objects_with_ctm()`는 CTM 중심 | `PDFStreamEngine.getTextMatrix()`, `PDFStreamEngine.getTextLineMatrix()`, `PDFStreamEngine.setTextMatrix(...)` | `onChar(..., origin, quad, ...)` |
| CTM/좌표 변환 | 공식 content semantics API 없음 | `pikepdf.Matrix`, `pikepdf.models.ctm.MatrixStack`, `get_objects_with_ctm()` | `PDFStreamEngine.getGraphicsState()`, `PDFStreamEngine.transformedPoint(...)`, `PDFStreamEngine.transformWidth(...)` | `onChar(..., origin, quad, ...)`, `StructuredText.prototype.asJSON()`의 `bbox`, `x`, `y` |
| Rotation/scale/skew 결과 | 공식 text layout API 없음 | `pikepdf.Matrix`, `pikepdf.models.ctm.MatrixStack`로 직접 추적 | `TextPosition`, `Matrix`, `PDFStreamEngine.getTextMatrix()` | `onChar(..., quad, ...)`, `StructuredText.prototype.asJSON()` |
| Curved text/글자별 배치 | 공식 미지원 | 공식 미지원 | 글자별 접근은 `PDFStreamEngine.showGlyph(...)`, `PDFTextStripper.processTextPosition(TextPosition)` | 글자별 접근은 `onChar(..., origin, quad, ...)` |
| Character/word spacing, leading, rise 등 text state | 공식 text state API 없음 | operator operand 저수준 접근만: `pikepdf.parse_content_stream()` | `PDFStreamEngine.processOperator(...)`, `PDFStreamEngine.applyTextAdjustment(...)`, `PDFStreamEngine.getGraphicsState()` | structured text 결과 중심. 원본 text state API는 공식 고수준 API 없음 |
| Text rendering mode/fill/stroke/invisible/clipping | 공식 text rendering API 없음 | operator operand 저수준 접근만 | `PDFStreamEngine.getGraphicsState()`, `PDFStreamEngine.processOperator(...)` | render 결과/structured text 중심. 원본 rendering mode API는 공식 고수준 API 없음 |
| Fill/stroke color | 공식 text color API 없음 | color operator 저수준 접근만 | `PDFStreamEngine.getGraphicsState()`, `PDGraphicsState`, `PDColor`, `PDColorSpace` | `onChar(..., argb, ...)` |
| Color space | raw resource 접근: `qpdf --json` | `Page.resources`, raw `/ColorSpace` 접근 | `PDColorSpace`, `PDColor`, `PDFStreamEngine.getResources()` | `onChar(..., argb, ...)`; 원본 color space API는 공식 고수준 API 없음 |
| Opacity/blend/soft mask/overprint | raw `/ExtGState` 접근: `qpdf --json` | `Page.resources` raw `/ExtGState` 접근 | `PDFStreamEngine.getGraphicsState()`, `PDFStreamEngine.processSoftMask(...)`, `PDFStreamEngine.processTransparencyGroup(...)` | structured text style로 자동 병합되는 공식 API 없음 |
| Text bbox | 공식 미지원 | 공식 미지원 | `TextPosition`, `PDFTextStripper.processTextPosition(TextPosition)` | `StructuredText.prototype.asJSON()`의 `bbox`, `onChar(..., quad, ...)` |
| Baseline/position | 공식 미지원 | 공식 미지원 | `TextPosition`, `PDFStreamEngine.getTextMatrix()` | `onChar(..., origin, quad, ...)`, `StructuredText.prototype.asJSON()`의 `x`, `y` |
| Writing direction | 공식 미지원 | 공식 미지원 | `TextPosition`, `PDFont.isVertical()` | `StructuredText.prototype.walk()`의 `beginLine(bbox, wmode, direction)` |
| Vertical writing | 공식 미지원 | 공식 미지원 | `PDFont.isVertical()`, `PDFont.getPositionVector(int)`, `PDFont.getDisplacement(int)` | `beginLine(bbox, wmode, direction)`, `StructuredText.prototype.asJSON()`의 `wmode` |
| Ligature/Unicode mapping | 공식 미지원 | 공식 미지원 | `PDFont.toUnicode(int)`, `PDFTextStripper.getText(PDDocument)` | `StructuredText.prototype.asText()`, `onChar(utf, ...)` |
| Kerning-like `TJ` adjustment | 공식 text API 없음 | `pikepdf.parse_content_stream(page, operators="TJ")`로 숫자 operand 접근만 | `PDFStreamEngine.showTextStrings(COSArray)`, `PDFStreamEngine.applyTextAdjustment(float, float)` | 결과 위치는 `onChar(..., quad, ...)`; 원본 `TJ` 값 API는 공식 고수준 API 없음 |
| Draw order | raw content stream 순서 접근만 | `pikepdf.parse_content_stream()` 또는 `TokenFilter.handle_token()` 순서 | `PDFStreamEngine.processOperator(...)`, `PDFStreamEngine.showGlyph(...)` 호출 순서 | `StructuredText.prototype.walk()` 순서, `mutool draw -F json` |
| Marked content/ActualText/Alt text | raw object/operator 접근: `qpdf --json` | raw object/operator 접근: `pikepdf.parse_content_stream()` | `PDFMarkedContentExtractor`, `PDFStreamEngine.processOperator(...)` | `StructuredText.prototype.walk()`의 `beginStruct(...)`, `endStruct()` |
| Text as outline/path | raw path operator 접근만 | `pikepdf.parse_content_stream()`로 path operator 접근만 | path 처리 계열은 `PDFGraphicsStreamEngine`; 실제 text 복원은 공식 미지원 | `StructuredText.prototype.walk()`의 `onVector(...)`; 실제 text 복원은 공식 미지원 |
| Plain text export | 공식 미지원 | 공식 미지원 | `PDFTextStripper.getText(PDDocument)`, `PDFTextStripper.writeText(...)` | `mutool draw -F text`, `mutool convert -F text`, `StructuredText.prototype.asText()` |
| HTML export | 공식 미지원 | 공식 미지원 | `PDFText2HTML` | `mutool draw -F html`, `mutool convert -F html`, `StructuredText.prototype.asHTML(id)` |
| Structured text JSON/XML export | PDF 객체 JSON만: `qpdf --json`; text extraction JSON 아님 | 공식 text JSON export 없음 | 공식 기본 JSON export 없음. 직접 `TextPosition` 수집 필요 | `mutool draw -F json`, `mutool draw -F xml`, `StructuredText.prototype.asJSON(scale)` |

## 공식 미지원 또는 직접 구현 영역

| 텍스트 기능 | QPDF | pikepdf | Apache PDFBox | MuPDF |
|---|---|---|---|---|
| Text extraction | 공식 미지원. qpdf JSON 문서도 text extraction 미지원 명시 | 공식 미지원. pikepdf 문서상 `pikepdf does not currently implement text extraction` | 공식 지원: `PDFTextStripper.getText(PDDocument)` | 공식 지원: `mutool draw -F text`, `StructuredText.prototype.asText()` |
| PDF content stream semantics 해석 | 공식 미지원 | 부분 지원: `parse_content_stream()`는 parser/filter이며 text extraction 아님 | 공식 지원: `PDFStreamEngine` callback API | structured text 변환은 지원. 원본 operator semantics API는 공식 고수준 API 없음 |
| Bold 여부 자동 판정 | 공식 미지원 | 공식 미지원 | 완전 자동 API 없음. `PDFont.getName()`, `PDFont.getFontDescriptor()` 기반 직접 판정 | 완전 자동 API 없음. `font.weight`, `font.name` 기반 직접 판정 |
| Fake bold 자동 판정 | 공식 미지원 | 공식 미지원 | 완전 자동 API 없음. `getGraphicsState()`, rendering mode/stroke state 직접 판정 | 완전 자동 API 없음 |
| Italic 여부 자동 판정 | 공식 미지원 | 공식 미지원 | 완전 자동 API 없음. `PDFont.getName()`, `PDFont.getFontDescriptor()` 기반 직접 판정 | 완전 자동 API 없음. `font.style`, `font.name` 기반 직접 판정 |
| Underline 자동 추출 | 공식 미지원 | 공식 미지원 | 공식 미지원. path/line과 `TextPosition` 직접 매칭 필요 | 공식 미지원. `onVector(...)`와 `onChar(...)` 직접 매칭 필요 |
| Strikethrough 자동 추출 | 공식 미지원 | 공식 미지원 | 공식 미지원. path/line과 `TextPosition` 직접 매칭 필요 | 공식 미지원. `onVector(...)`와 `onChar(...)` 직접 매칭 필요 |
| Highlight/background 자동 추출 | 공식 미지원 | 공식 미지원 | 공식 미지원. filled rect와 `TextPosition` 직접 매칭 필요 | 공식 미지원. `onVector(...)`와 `onChar(...)` 직접 매칭 필요 |
| 텍스트 배경색을 텍스트 속성으로 추출 | 공식 미지원 | 공식 미지원 | 공식 미지원 | 공식 미지원 |
| Curved text를 하나의 스타일 객체로 인식 | 공식 미지원 | 공식 미지원 | 공식 미지원. 글자별 `TextPosition`/matrix 직접 그룹화 필요 | 공식 미지원. 글자별 `quad` 직접 그룹화 필요 |
| Path/outline으로 변환된 텍스트 복원 | 공식 미지원 | 공식 미지원 | 공식 미지원 | 공식 미지원 |
| Word/HTML식 `bold`, `underline`, `background` 속성 모델 | 공식 미지원 | 공식 미지원 | 공식 미지원 | 공식 미지원 |
| PDF 텍스트 상태 전체를 사람이 쓰기 좋은 JSON schema로 export | 공식 미지원. `qpdf --json`은 PDF object JSON | 공식 미지원 | 공식 미지원. `TextPosition`/`PDFStreamEngine`으로 직접 schema 구성 | 부분 지원: `StructuredText.prototype.asJSON(scale)`, 단 원본 text state 전체 아님 |
| JSON의 모든 텍스트 상태를 원본과 동일하게 자동 재작성 | 공식 미지원 | 공식 미지원 | 공식 미지원 | 공식 미지원 |
| Bidi/RTL 시각 순서와 논리 순서 완전 복원 | 공식 미지원 | 공식 미지원 | 완전 자동 API 없음 | 완전 자동 API 없음 |
| Ligature 원형/분해 상태 완전 보존 | 공식 미지원 | 공식 미지원 | 완전 자동 API 없음 | 완전 자동 API 없음 |
| Opacity/blend/layer를 텍스트 스타일로 자동 병합 | 공식 미지원 | 공식 미지원 | 공식 미지원 | 공식 미지원 |
| 원본 content stream 순서/리소스/텍스트 상태를 고수준 API만으로 동일 재현 | 공식 미지원 | 공식 미지원 | 공식 미지원 | 공식 미지원 |
