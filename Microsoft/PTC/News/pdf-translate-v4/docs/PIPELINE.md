# PIPELINE — pdf-translate-v4

`pdf-translate-v4` 의 현재 파이프라인은 `DETECT -> EXTRACT -> SEGMENT -> TRANSLATE -> BUILD EDITS -> APPLY/REBUILD -> DONE` 순서로 동작한다.

## 1. DETECT

`src/pipeline.mjs` 의 `listInputPdfs()` 가 입력 PDF를 수집한다.

동작:

- `INPUT_DIR` 기본값은 `input` 이다.
- 확장자가 `.pdf` 인 파일만 처리한다.
- `~$` 로 시작하는 임시 파일은 제외한다.
- 디렉토리는 처리하지 않는다.
- CLI 인자로 PDF 경로를 직접 넘기면 해당 파일만 처리한다.

예:

```bash
./run-translate.sh
./run-translate.sh --keep-input input/done/sample.pdf
```

## 2. EXTRACT

Node wrapper:

```text
src/pdf/engine.mjs::extractPages()
```

Python engine:

```bash
python3 src/pdf/pymupdf_engine.py text <pdf> --json
```

PyMuPDF 구현:

- `fitz.open(pdf_path)` 로 원본 PDF를 연다.
- 각 page에서 `page.get_text("dict", flags=...)` 를 호출한다.
- `block.type === 0` 인 text block만 span 단위로 추출한다.
- 각 span의 bbox/style/color/background 정보를 run으로 저장한다.

산출:

```text
work/<stem>/segments.json
```

주의:

- 도형 안 글자가 실제 PDF text object이면 추출된다.
- 도형 안 글자가 이미지 픽셀이거나 vector outline이면 추출되지 않는다.
- 스캔 PDF나 이미지형 다이어그램 텍스트는 OCR/vision pass가 필요하다.

## 3. SEGMENT

`src/pipeline.mjs::flattenSegments()` 가 run을 번역 단위 segment로 묶는다.

주요 로직:

- y 좌표와 font size 기준으로 같은 visual line을 찾는다.
- 같은 visual line 안에서 x 좌표 순서로 정렬한다.
- horizontal gap이 크면 서로 다른 segment로 분리한다.
- 여러 run을 `joinRuns()` 로 합쳐 하나의 문장/라벨로 만든다.
- bbox, page size, style, color를 segment에 보존한다.

segment 주요 필드:

```json
{
  "id": 0,
  "page": 1,
  "pageWidth": 612,
  "pageHeight": 792,
  "x": 72,
  "y": 120,
  "left": 72,
  "right": 180,
  "top": 108,
  "bottom": 124,
  "height": 16,
  "fontSize": 12,
  "bold": false,
  "color": [0, 0, 0],
  "bgColor": [1, 1, 1],
  "maxWidth": 108,
  "text": "Original text"
}
```

## 4. TRANSLATE

`src/pipeline.mjs::translateSegments()` 가 번역을 수행한다.

처리 순서:

1. glossary protected term을 placeholder로 치환한다.
2. URL, email, 변수 표현도 보호한다.
3. Translation Memory에서 기존 번역을 조회한다.
4. miss만 LLM batch로 보낸다.
5. batch 실패 시 segment 단위로 재시도한다.
6. placeholder가 깨지면 원문 fallback한다.
7. 성공 결과는 SQLite TM에 저장한다.
8. `translated.json` 을 작성한다.

산출:

```text
work/<stem>/translated.json
```

번역 실패 segment는 다음처럼 남는다.

```json
{
  "id": 10,
  "text": "Original text",
  "translated": null
}
```

현재 `translated: null` 은 출력에 포함되지 않는다.

## 5. BUILD EDITS

`src/pipeline.mjs::buildEdits()` 가 translated segment를 PDF edit operation으로 바꾼다.

rebuild 모드의 핵심 규칙:

- 원본 text object를 복사하지 않으므로 모든 표시할 텍스트는 edit으로 다시 써야 한다.
- `translated === text` 여도 edit을 만든다.
- `translated === null` 은 edit을 만들지 않는다.
- `FillRect` 는 만들지 않는다.
- 주 operation은 `AddTextBoxEmbedded` 이다.

text box 계산:

- 원본 bbox를 1차 기준으로 사용한다.
- 번역문 예상 폭이 더 길면 page 안에서 폭을 확장한다.
- 예상 줄 수에 따라 height를 늘린다.
- target language가 `kr/ch/jp` 이면 `PDF_CJK_SIZE_RATIO` 를 적용한다.
- 최소 font size는 `PDF_MIN_FONT_SIZE` 를 따른다.

산출:

```text
work/<stem>/edits.json
```

예:

```json
[
  {
    "type": "AddTextBoxEmbedded",
    "page": 1,
    "x": 72,
    "y": 108,
    "width": 180,
    "height": 34,
    "text": "번역 텍스트",
    "fontPath": "/mnt/c/Windows/Fonts/malgun.ttf",
    "fontName": "PDFTrRegular",
    "size": 9.8,
    "color": [0, 0, 0]
  }
]
```

## 6. APPLY / REBUILD

Node wrapper:

```text
src/pdf/engine.mjs::applyEdits()
```

Python engine:

```bash
python3 src/pdf/pymupdf_engine.py edit <input> <output> --edits <edits.json>
```

`PDF_BUILD_MODE=rebuild` 기준 처리:

1. 원본 PDF를 연다.
2. 새 PDF 문서를 만든다.
3. 각 원본 page와 같은 크기의 blank page를 만든다.
4. 원본 image block을 `insert_image()` 로 복사한다.
5. 원본 vector drawing을 `page.get_drawings()` 기반으로 다시 그린다.
6. 원본 text object는 복사하지 않는다.
7. edit에 있는 번역 텍스트만 삽입한다.
8. 저장 전 embedded font를 subset한다.
9. clean/deflate 옵션으로 저장한다.

출력:

```text
output/<stem>_KR.pdf
```

## 7. 텍스트 삽입 방식

`src/pdf/pymupdf_engine.py::insert_textbox()` 가 최종 text drawing을 담당한다.

현재 동작:

1. 원래 bbox에 `page.insert_textbox()` 를 시도한다.
2. 실패하면 text box width/height를 page 안에서 확장한다.
3. 긴 텍스트를 `wrap_text_to_width()` 로 줄바꿈한다.
4. font size를 0.5pt 단위로 줄이며 다시 시도한다.
5. 끝까지 실패하면 page의 남은 영역에 4pt fallback으로 줄 단위 삽입한다.

이 로직은 번역문이 원문보다 길어져서 잘리는 문제를 줄이기 위한 것이다.

## 8. DONE

APPLY 성공 후:

- `PDF_KEEP_INPUT=true` 또는 `--keep-input` 이면 원본을 이동하지 않는다.
- 그렇지 않으면 원본을 `input/done` 으로 이동한다.
- 같은 이름이 있으면 timestamp를 붙인다.

## 9. 실패 처리

각 PDF 처리 중 실패하면 다음 파일에 기록한다.

```text
work/<stem>/error.json
```

형태:

```json
{
  "source": "input/sample.pdf",
  "reason": "TRANSLATE 실패: ...",
  "recordedAt": "2026-05-10T00:00:00.000Z"
}
```

파일 하나가 실패해도 전체 batch는 다음 PDF로 계속 진행한다.

## 10. 단계별 실행

```bash
./run-translate.sh extract input/sample.pdf
./run-translate.sh translate work/sample/segments.json
./run-translate.sh apply input/sample.pdf work/sample/translated.json
```

중간 산출물인 `segments.json`, `translated.json`, `edits.json` 을 확인하거나 수정한 뒤 다음 단계만 재실행할 수 있다.

## 현재 한계

- 이미지 안 텍스트는 아직 번역하지 않는다.
- vector outline으로 변환된 텍스트는 text extraction에 잡히지 않는다.
- 복잡한 PDF graphic effect는 완전 재현되지 않을 수 있다.
- annotation/link/bookmark 복사는 아직 구현하지 않았다.
