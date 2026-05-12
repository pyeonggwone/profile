# BUILD.md

## 1. 생성 파일

```text
pdf-vision-translate-v1/
├── package.json
├── package-lock.json
├── run-translate.sh
├── .env.example
├── .gitignore
├── glossary.csv
├── input/
│   └── done/
├── output/
├── work/
└── src/
    ├── index.mjs
    ├── pipeline.mjs
    ├── render/
    │   └── pdf-to-image.mjs
    ├── vision/
    │   ├── openai-layout.mjs
    │   └── schema.mjs
    ├── normalize/
    │   └── layout-normalizer.mjs
    ├── translate/
    │   └── llm.mjs
    ├── compose/
    │   └── pdf-writer.mjs
    ├── glossary/
    │   ├── loader.mjs
    │   └── masker.mjs
    ├── tm/
    │   └── store.mjs
    └── util/
        ├── env.mjs
        ├── fs.mjs
        ├── lang.mjs
        ├── log.mjs
        └── paths.mjs
```

## 2. package.json

```json
{
  "name": "pdf-vision-translate-v1",
  "version": "0.1.0",
  "type": "module",
  "private": true,
  "scripts": {
    "start": "node src/index.mjs",
    "translate": "node src/index.mjs",
    "render": "node src/index.mjs render",
    "analyze": "node src/index.mjs analyze",
    "compose": "node src/index.mjs compose"
  },
  "dependencies": {
    "commander": "latest",
    "dotenv": "latest",
    "openai": "latest",
    "pdf-lib": "latest",
    "sharp": "latest",
    "sqlite3": "latest"
  },
  "devDependencies": {}
}
```

## 3. .env.example

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_VISION_MODEL=gpt-4.1
OPENAI_TRANSLATE_MODEL=gpt-4.1-mini
OPENAI_IMAGE_DETAIL=high

AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=
AZURE_OPENAI_VISION_DEPLOYMENT=
AZURE_OPENAI_TRANSLATE_DEPLOYMENT=

SOURCE_LANG=en
TARGET_LANG=kr
PDF_OUTPUT_SUFFIX=KR

PDF_RENDER_DPI=300
PDF_RENDER_FORMAT=png
PDF_FONT_PATH=C:/Windows/Fonts/malgun.ttf

INPUT_DIR=input
OUTPUT_DIR=output
WORK_DIR=work
TM_DB_PATH=work/tm.sqlite
```

## 4. run-translate.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
fi

if [ ! -d node_modules ]; then
  npm install
fi

node src/index.mjs "$@"
```

## 5. CLI 구현

`src/index.mjs` 구현:

- `commander`를 사용한다.
- `.env`를 로드한다.
- 기본 실행은 `input/` 전체 처리로 연결한다.
- 명령을 추가한다.

```text
pdf-vision-translate-v1
pdf-vision-translate-v1 input/sample.pdf
pdf-vision-translate-v1 --in-lang en --out-lang kr
pdf-vision-translate-v1 render input/sample.pdf
pdf-vision-translate-v1 analyze work/sample/pages
pdf-vision-translate-v1 translate work/sample/segments.json
pdf-vision-translate-v1 compose input/sample.pdf work/sample/translated.json
```

CLI 옵션:

```text
--in-lang <lang>
--out-lang <lang>
--reset-work
--reset-tm
--detail <low|high|original|auto>
--dpi <number>
```

## 6. 환경 로더

`src/util/env.mjs` 구현:

- `.env`를 로드한다.
- 필수 값을 검증한다.
- 기본값을 지정한다.
- `LLM_PROVIDER=openai`이면 `OPENAI_API_KEY`를 필수로 둔다.
- `LLM_PROVIDER=azure`이면 Azure OpenAI 값을 필수로 둔다.
- `SOURCE_LANG`, `TARGET_LANG`를 소문자로 정규화한다.
- `OPENAI_IMAGE_DETAIL`은 `low`, `high`, `original`, `auto`만 허용한다.

반환 객체:

```js
{
  provider,
  openaiApiKey,
  openaiVisionModel,
  openaiTranslateModel,
  imageDetail,
  sourceLang,
  targetLang,
  outputSuffix,
  renderDpi,
  renderFormat,
  fontPath,
  inputDir,
  outputDir,
  workDir,
  tmDbPath,
  azure
}
```

## 7. 경로 유틸

`src/util/paths.mjs` 구현:

- 입력 PDF stem을 계산한다.
- 파일별 작업 경로를 생성한다.
- 페이지 PNG 경로를 생성한다.
- 분석 JSON 경로를 생성한다.
- 정규화 JSON 경로를 생성한다.
- 번역 JSON 경로를 생성한다.
- composition JSON 경로를 생성한다.
- output PDF 경로를 생성한다.
- done 경로를 생성한다.

경로 규칙:

```text
input/sample.pdf
output/sample_KR.pdf
input/done/sample.pdf
work/sample/pages/page-001.png
work/sample/analysis/page-001.json
work/sample/normalized/page-001.json
work/sample/segments.json
work/sample/translated.json
work/sample/composition.json
work/sample/report.json
```

## 8. 파이프라인

`src/pipeline.mjs` 구현:

```text
DETECT
RENDER
VISION_ANALYZE
NORMALIZE
TRANSLATE
COMPOSE
DONE
```

처리 규칙:

- `input/`에서 `.pdf`만 처리한다.
- 단일 파일 인수가 있으면 해당 파일만 처리한다.
- 실패한 파일은 `input/`에 남긴다.
- 성공한 파일은 `input/done/`으로 이동한다.
- 각 단계 시작/완료를 로그로 남긴다.
- 각 파일별 `report.json`을 생성한다.
- 재실행 시 기존 산출물을 재사용한다.
- `--reset-work`가 있으면 해당 파일의 `work/{stem}/`을 삭제 후 재생성한다.

## 9. RENDER

`src/render/pdf-to-image.mjs` 구현:

- PDF를 페이지별 PNG로 변환한다.
- 기본 DPI는 `PDF_RENDER_DPI`를 사용한다.
- 출력 폴더는 `work/{stem}/pages/`를 사용한다.
- 파일명은 `page-001.png` 형식을 사용한다.
- 각 페이지 metadata를 `work/{stem}/pages.json`에 저장한다.

`pages.json` 형식:

```json
{
  "source": "input/sample.pdf",
  "dpi": 300,
  "format": "png",
  "pages": [
    {
      "page": 1,
      "image": "work/sample/pages/page-001.png",
      "widthPx": 2480,
      "heightPx": 3508,
      "widthPt": 595.28,
      "heightPt": 841.89,
      "rotation": 0
    }
  ]
}
```

구현 후보:

- `pdftoppm` CLI
- `mutool draw`
- PyMuPDF helper
- Node wrapper에서 외부 renderer 호출

MVP 우선순위:

1. 설치가 쉬운 renderer 선택
2. 페이지 크기 metadata 확보
3. PNG 품질 고정
4. Windows/WSL 경로 처리

## 10. Vision 분석

`src/vision/openai-layout.mjs` 구현:

- 페이지 PNG를 읽는다.
- Base64 data URL을 만든다.
- OpenAI Responses API를 호출한다.
- `input_image`에 `detail` 값을 지정한다.
- Structured Outputs schema를 적용한다.
- 페이지당 1 request로 처리한다.
- 실패 시 page 단위 retry를 수행한다.
- 응답을 `work/{stem}/analysis/page-001.json`에 저장한다.

요청 content 형식:

```json
[
  {
    "role": "user",
    "content": [
      {
        "type": "input_text",
        "text": "Extract all page layout objects for PDF reconstruction. Return JSON only."
      },
      {
        "type": "input_image",
        "image_url": "data:image/png;base64,...",
        "detail": "high"
      }
    ]
  }
]
```

분석 prompt 요구사항:

```text
Extract text blocks, tables, images, captions, headers, footers, page numbers, reading order, and approximate visual styles.
Use pixel coordinates from the top-left of the image.
Return every visible text block.
Return table cells with row, column, spans, bbox, text, alignment, background, and border.
Return images with bbox, description, and containsText.
Return confidence and warnings.
Do not translate.
Do not summarize.
Do not omit small text unless unreadable.
```

## 11. Vision schema

`src/vision/schema.mjs` 구현:

```js
export const pageLayoutSchema = {
  name: 'page_layout',
  strict: true,
  schema: {
    type: 'object',
    additionalProperties: false,
    required: ['page', 'width', 'height', 'dpi', 'rotation', 'languageHints', 'blocks', 'warnings'],
    properties: {
      page: { type: 'integer' },
      width: { type: 'integer' },
      height: { type: 'integer' },
      dpi: { type: 'integer' },
      rotation: { type: 'integer' },
      languageHints: { type: 'array', items: { type: 'string' } },
      blocks: {
        type: 'array',
        items: { '$ref': '#/$defs/block' }
      },
      warnings: { type: 'array', items: { type: 'string' } }
    },
    '$defs': {
      bbox: {
        type: 'object',
        additionalProperties: false,
        required: ['x', 'y', 'width', 'height'],
        properties: {
          x: { type: 'number' },
          y: { type: 'number' },
          width: { type: 'number' },
          height: { type: 'number' }
        }
      },
      block: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'type', 'role', 'bbox', 'text', 'description', 'readingOrder', 'style', 'table', 'confidence'],
        properties: {
          id: { type: 'string' },
          type: { type: 'string', enum: ['text', 'image', 'table', 'shape', 'line', 'unknown'] },
          role: { type: 'string' },
          bbox: { '$ref': '#/$defs/bbox' },
          text: { type: ['string', 'null'] },
          description: { type: ['string', 'null'] },
          readingOrder: { type: ['integer', 'null'] },
          style: { '$ref': '#/$defs/style' },
          table: { anyOf: [{ '$ref': '#/$defs/table' }, { type: 'null' }] },
          confidence: { type: 'number' }
        }
      },
      style: {
        type: 'object',
        additionalProperties: false,
        required: ['fontSizeApprox', 'bold', 'italic', 'color', 'align', 'backgroundColor'],
        properties: {
          fontSizeApprox: { type: ['number', 'null'] },
          bold: { type: ['boolean', 'null'] },
          italic: { type: ['boolean', 'null'] },
          color: { type: ['string', 'null'] },
          align: { type: ['string', 'null'] },
          backgroundColor: { type: ['string', 'null'] }
        }
      },
      table: {
        type: 'object',
        additionalProperties: false,
        required: ['rows', 'columns', 'border', 'cells'],
        properties: {
          rows: { type: 'integer' },
          columns: { type: 'integer' },
          border: { '$ref': '#/$defs/border' },
          cells: { type: 'array', items: { '$ref': '#/$defs/cell' } }
        }
      },
      border: {
        type: 'object',
        additionalProperties: false,
        required: ['style', 'thicknessApprox', 'color'],
        properties: {
          style: { type: ['string', 'null'] },
          thicknessApprox: { type: ['number', 'null'] },
          color: { type: ['string', 'null'] }
        }
      },
      cell: {
        type: 'object',
        additionalProperties: false,
        required: ['row', 'column', 'rowSpan', 'columnSpan', 'bbox', 'text', 'backgroundColor', 'align'],
        properties: {
          row: { type: 'integer' },
          column: { type: 'integer' },
          rowSpan: { type: 'integer' },
          columnSpan: { type: 'integer' },
          bbox: { '$ref': '#/$defs/bbox' },
          text: { type: ['string', 'null'] },
          backgroundColor: { type: ['string', 'null'] },
          align: { type: ['string', 'null'] }
        }
      }
    }
  }
};
```

## 12. NORMALIZE

`src/normalize/layout-normalizer.mjs` 구현:

- analysis JSON을 읽는다.
- page metadata와 image metadata를 병합한다.
- bbox를 page pixel 좌표로 정규화한다.
- bbox가 페이지 밖이면 clamp한다.
- block id를 안정적으로 재부여한다.
- readingOrder가 없으면 y, x 기준으로 계산한다.
- type별 필수 값을 보정한다.
- confidence가 낮은 block을 warnings에 추가한다.
- 번역 대상 segment를 만든다.

segment 생성 규칙:

- `type=text`이고 `text`가 있으면 segment 생성
- `type=table`이면 cell별 segment 생성
- `image.containsText=true`이면 옵션에 따라 segment 생성
- URL, code, page number, protected term only text는 제외

`segments.json` 형식:

```json
{
  "source": "input/sample.pdf",
  "sourceLang": "en",
  "targetLang": "kr",
  "segments": [
    {
      "id": "p1-b001",
      "page": 1,
      "kind": "text",
      "text": "Original heading text",
      "bbox": { "x": 120, "y": 180, "width": 1800, "height": 96 },
      "role": "heading"
    }
  ]
}
```

## 13. Glossary

`src/glossary/loader.mjs` 구현:

- `glossary.csv`를 읽는다.
- 빈 줄을 무시한다.
- header를 지원한다.
- `source,target,protected` 컬럼을 지원한다.

`src/glossary/masker.mjs` 구현:

- protected term을 placeholder로 치환한다.
- 번역 후 placeholder를 원문으로 복원한다.
- placeholder 형식은 `__PT_{index}__`를 사용한다.

## 14. Translation Memory

`src/tm/store.mjs` 구현:

- SQLite DB를 생성한다.
- `translations` 테이블을 생성한다.
- key는 `sourceLang`, `targetLang`, `sourceText`, `glossaryHash`로 만든다.
- hit이면 LLM 호출을 생략한다.
- miss이면 번역 후 저장한다.

테이블:

```sql
CREATE TABLE IF NOT EXISTS translations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_lang TEXT NOT NULL,
  target_lang TEXT NOT NULL,
  source_text TEXT NOT NULL,
  translated_text TEXT NOT NULL,
  glossary_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(source_lang, target_lang, source_text, glossary_hash)
);
```

## 15. TRANSLATE

`src/translate/llm.mjs` 구현:

- `segments.json`을 입력으로 받는다.
- glossary protected term을 mask한다.
- TM hit을 먼저 조회한다.
- miss segment만 batch로 번역한다.
- 번역 결과에서 placeholder를 복원한다.
- `translated.json`을 저장한다.

번역 prompt:

```text
Translate the text from {sourceLang} to {targetLang}.
Preserve placeholders exactly.
Preserve product names, URLs, IDs, code, and glossary protected terms.
Return JSON array with id and translatedText.
Do not add explanations.
```

`translated.json` 형식:

```json
{
  "source": "input/sample.pdf",
  "sourceLang": "en",
  "targetLang": "kr",
  "segments": [
    {
      "id": "p1-b001",
      "page": 1,
      "sourceText": "Original heading text",
      "translatedText": "번역된 제목"
    }
  ],
  "usage": {
    "tmHit": 0,
    "tmMiss": 1,
    "inputTokens": 0,
    "outputTokens": 0,
    "totalTokens": 0
  }
}
```

## 16. COMPOSE

`src/compose/pdf-writer.mjs` 구현:

- `pages.json`, normalized layout, `translated.json`을 읽는다.
- `composition.json`을 생성한다.
- `pdf-lib`로 새 PDF를 생성한다.
- 원본 page PNG를 각 PDF page 배경으로 삽입한다.
- 번역 대상 bbox에 whiteout rectangle을 그린다.
- 같은 bbox에 번역문을 삽입한다.
- 텍스트가 bbox를 넘치면 font size를 줄인다.
- 최저 font size 아래로 내려가면 warning을 기록한다.
- 표 cell 텍스트는 cell bbox 기준으로 삽입한다.
- output PDF를 `output/{stem}_{suffix}.pdf`에 저장한다.

좌표 변환:

```text
xPt = xPx / widthPx * widthPt
yPt = heightPt - ((yPx + heightPx) / heightPxPage * heightPt)
wPt = widthPxBox / widthPxPage * widthPt
hPt = heightPxBox / heightPxPage * heightPt
```

composition operation:

```json
{
  "type": "text",
  "page": 1,
  "sourceId": "p1-b001",
  "bboxPt": { "x": 28, "y": 42, "width": 430, "height": 32 },
  "text": "번역된 제목",
  "font": "Malgun Gothic",
  "fontSize": 14,
  "color": "#111111",
  "align": "left"
}
```

## 17. DONE

성공 처리:

- output PDF 존재 확인
- `report.json` 저장
- 원본 PDF를 `input/done/`으로 이동
- 동일 파일명이 있으면 timestamp suffix 추가

실패 처리:

- 원본 PDF 유지
- 실패 단계 기록
- error message 기록
- stack trace는 debug 옵션에서만 기록

## 18. report.json

```json
{
  "source": "input/sample.pdf",
  "target": "output/sample_KR.pdf",
  "status": "success",
  "startedAt": "2026-05-10T00:00:00.000Z",
  "finishedAt": "2026-05-10T00:01:00.000Z",
  "pages": 1,
  "segments": 10,
  "warnings": [],
  "usage": {
    "visionInputTokens": 0,
    "visionOutputTokens": 0,
    "translateInputTokens": 0,
    "translateOutputTokens": 0,
    "totalTokens": 0
  }
}
```

## 19. 단계별 구현 순서

1. `package.json`, `.env.example`, `.gitignore`, `run-translate.sh` 생성
2. `src/util/env.mjs` 구현
3. `src/util/paths.mjs` 구현
4. `src/index.mjs` CLI 구현
5. `src/pipeline.mjs` skeleton 구현
6. `src/render/pdf-to-image.mjs` 구현
7. `pages.json` 생성 확인
8. `src/vision/schema.mjs` 구현
9. `src/vision/openai-layout.mjs` 구현
10. page 단위 `analysis/page-001.json` 저장 확인
11. `src/normalize/layout-normalizer.mjs` 구현
12. `segments.json` 생성 확인
13. glossary loader/masker 구현
14. TM store 구현
15. `src/translate/llm.mjs` 구현
16. `translated.json` 생성 확인
17. `src/compose/pdf-writer.mjs` 구현
18. `composition.json` 생성 확인
19. `output/{stem}_KR.pdf` 생성 확인
20. 성공 시 `input/done/` 이동 구현
21. 실패 시 `report.json` 기록 구현

## 20. 검증 명령

```bash
npm install
cp .env.example .env
./run-translate.sh render input/sample.pdf
./run-translate.sh analyze work/sample/pages
./run-translate.sh translate work/sample/segments.json --in-lang en --out-lang kr
./run-translate.sh compose input/sample.pdf work/sample/translated.json --out-lang kr
./run-translate.sh input/sample.pdf
```

## 21. 완료 조건

- `input/sample.pdf`가 `output/sample_KR.pdf`로 생성된다.
- 성공한 원본이 `input/done/sample.pdf`로 이동된다.
- `work/sample/pages/page-001.png`가 생성된다.
- `work/sample/pages.json`가 생성된다.
- `work/sample/analysis/page-001.json`가 생성된다.
- `work/sample/segments.json`가 생성된다.
- `work/sample/translated.json`가 생성된다.
- `work/sample/composition.json`가 생성된다.
- `work/sample/report.json`가 생성된다.
- OpenAI vision 호출 실패 시 해당 page만 재시도된다.
- 번역 TM hit 시 LLM 번역 호출이 생략된다.
- 실패한 원본 PDF는 `input/`에 남는다.
