# Architecture — pdf-translate-v4

`pdf-translate-v4` 는 PDF 원문 위에 번역문을 덧씌우는 overlay 방식이 아니라, 새 PDF를 생성해 원본의 시각 구조와 번역 텍스트를 재구성하는 방식으로 구현되어 있다.

## 핵심 결정

| 항목 | 현재 선택 | 설명 |
|---|---|---|
| 기본 PDF 엔진 | PyMuPDF / MuPDF | `src/pdf/pymupdf_engine.py` 를 Node에서 subprocess로 호출한다. |
| 기본 출력 방식 | rebuild | `PDF_BUILD_MODE=rebuild`. 원본 PDF text object를 출력 PDF로 복사하지 않는다. |
| 비텍스트 요소 | 재구성 | 원본 image block과 vector drawing을 새 PDF page에 다시 삽입/그리기 한다. |
| 텍스트 출력 | embedded font text box | `AddTextBoxEmbedded` edit로 번역문을 삽입한다. CJK 출력은 `malgun.ttf` 등 TrueType font를 사용한다. |
| 텍스트 잘림 대응 | adaptive fitting | bbox에 먼저 넣고, 실패하면 같은 page 안에서 폭/높이 확장, 줄바꿈, font shrink를 순차 적용한다. |
| 동일 번역 처리 | rebuild에서는 출력 | 원문과 번역문이 같아도 rebuild에서는 text object가 없으므로 edit을 생성한다. |
| TM | SQLite | `work/tm.sqlite` 로 동일 문장 재번역을 줄인다. |
| LLM | OpenAI / Azure OpenAI | `.env` 설정에 따라 분기한다. |
| fallback | Rust `pdftr` | historical/debug fallback. v4 기본 경로는 PyMuPDF rebuild 이다. |

## 전체 구조

```text
pdf-translate-v4/
├── run-translate.sh
├── package.json
├── requirements.txt
├── .env / .env.example
├── glossary.csv
├── input/
├── output/
├── work/
├── src/
│   ├── index.mjs
│   ├── pipeline.mjs
│   ├── pdf/
│   │   ├── engine.mjs
│   │   ├── pymupdf_engine.py
│   │   └── edits.mjs
│   ├── translate/llm.mjs
│   ├── glossary/
│   ├── tm/store.mjs
│   └── util/
├── docs/
└── crates/                  # pdftr fallback
```

## 런타임 흐름

```text
./run-translate.sh
  │
  ├─ .env 없으면 .env.example 복사
  ├─ node_modules 없으면 npm install
  ├─ PyMuPDF 없으면 pip install -r requirements.txt
  ├─ PDF_ENGINE=pdftr 일 때만 cargo build
  │
  ▼
node src/index.mjs
  │
  ▼
src/pipeline.mjs
  │
  ├─ EXTRACT    PyMuPDF text extraction
  ├─ SEGMENT    visual line grouping
  ├─ TRANSLATE  TM + glossary + LLM
  ├─ BUILD      AddTextBoxEmbedded edit 생성
  ├─ APPLY      PyMuPDF rebuild output 생성
  └─ DONE       성공 시 input/done 이동
```

## EXTRACT 구현

`src/pdf/engine.mjs` 가 Python subprocess를 호출한다.

```text
python3 src/pdf/pymupdf_engine.py text <pdf> --json
```

`src/pdf/pymupdf_engine.py` 는 PyMuPDF의 `page.get_text("dict")` 를 사용해 text span을 추출한다.

추출되는 주요 값:

- page geometry: `page`, `width`, `height`
- text geometry: `x`, `y`, `left`, `right`, `top`, `bottom`, `width`, `height`
- style: `font_size`, `font`, `bold`, `italic`, `serif`, `monospace`, `flags`
- color: `color`, `color_rgb`
- background sample: `bg_color`
- grouping hints: `block`, `line`, `span`

도형 안 텍스트도 PDF 내부에서 실제 text object이면 같은 경로로 추출된다. 다만 도형 안 글자가 이미지 픽셀이나 vector outline이면 text extraction 대상이 아니므로 OCR/vision pass가 필요하다.

## SEGMENT 구현

`src/pipeline.mjs` 의 `flattenSegments()` 가 page별 run을 visual line으로 묶는다.

처리 방식:

1. y 좌표와 font size tolerance로 같은 시각 줄을 찾는다.
2. 같은 줄 안에서 x 좌표 순서로 정렬한다.
3. 큰 horizontal gap이 있으면 다른 그룹으로 분리한다.
4. run들을 join해 번역 단위 segment를 만든다.
5. bbox, page size, style, color를 segment에 유지한다.

segment에는 `pageWidth`, `pageHeight` 도 포함된다. APPLY 단계에서 text box 확장 한계를 계산하기 위해 사용한다.

## TRANSLATE 구현

`translateSegments()` 는 다음 순서로 동작한다.

1. glossary protected term과 URL/email/변수를 placeholder로 masking한다.
2. `tmGet()` 으로 Translation Memory를 조회한다.
3. miss만 `BATCH_SIZE` 단위로 LLM에 보낸다.
4. batch 실패 시 segment 단위로 재시도한다.
5. placeholder가 깨지면 원문 fallback한다.
6. 성공 결과는 `tmPut()` 으로 SQLite에 저장한다.
7. 최종 결과를 `work/<stem>/translated.json` 에 쓴다.

번역 실패 segment는 `translated: null` 로 남는다. 이 경우 현재 출력에 포함되지 않는다.

## BUILD 구현

`buildEdits()` 는 translated segment를 `AddTextBoxEmbedded` 배열로 변환한다.

현재 rebuild 기준 동작:

- `translated === original` 이어도 edit을 생성한다.
- 이유: rebuild 출력에는 원본 text object가 없기 때문에 동일 문장도 다시 써야 한다.
- 원본 bbox를 우선 사용한다.
- 번역문 예상 폭이 원본 bbox보다 길면 page 범위 안에서 text box 폭을 확장한다.
- 예상 line count를 계산해 text box 높이도 늘린다.
- CJK 대상 언어는 `PDF_CJK_SIZE_RATIO` 로 글자 크기를 보정한다.
- bold segment는 `PDF_FONT_BOLD_PATH` 가 있으면 bold font를 사용한다.

생성 예:

```json
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
```

`FillRect` 는 overlay 모드 전용이다. rebuild 모드에서는 생성하지 않는다.

## APPLY / REBUILD 구현

`src/pdf/pymupdf_engine.py edit <input> <output> --edits <json>` 이 기본 rebuild를 수행한다.

처리 순서:

1. 원본 PDF를 연다.
2. 새 `fitz.open()` 문서를 만든다.
3. 원본과 같은 크기의 blank page를 만든다.
4. `page.get_text("dict")` 의 image block을 `insert_image()` 로 복사한다.
5. `page.get_drawings()` 의 vector drawing을 새 page에 다시 그린다.
6. 원본 text object는 복사하지 않는다.
7. `AddTextBoxEmbedded` edit만 삽입한다.
8. `insert_textbox()` 는 원본 bbox에 먼저 넣고, 실패하면 확장/줄바꿈/font shrink를 재시도한다.
9. 저장 전 `doc.subset_fonts()` 를 호출해 embedded CJK font 크기를 줄인다.
10. `garbage=4`, `deflate=True`, `clean=True` 로 저장한다.

## overlay fallback

`PDF_BUILD_MODE=overlay` 로 바꾸면 원본 PDF를 열고 그 위에 edit을 적용하는 방식으로 동작한다. 이 모드는 v3와 유사하며 원본 text object가 남을 수 있다.

## 현재 한계

- 이미지 안 글자는 OCR/vision pass 없이는 추출되지 않는다.
- vector outline으로 변환된 글자는 일반 text object가 아니므로 추출되지 않는다.
- 복잡한 shading, pattern, transparency, blend mode는 `page.get_drawings()` 로 완전 복원되지 않을 수 있다.
- annotations, links, bookmarks/outlines는 아직 복사하지 않는다.
- 새 PDF 재구성 방식이므로 원본 PDF 내부 object 구조를 보존하는 것이 아니라 시각 결과를 재생성한다.
