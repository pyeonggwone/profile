# pdf-vision-translate-v1

PDF를 페이지 이미지로 렌더링한 뒤 OpenAI vision API로 페이지 구조를 분석하고, 분석 결과를 기반으로 번역 PDF를 재구성하는 비전 기반 PDF 번역 프로젝트.

이 프로젝트는 `pdf-translate-v3`의 PDF-native 방식과 다른 접근이다. 기존 프로젝트는 PDF 내부 text run, bbox, font size를 직접 추출해 원문 영역에 번역문을 삽입한다. `pdf-vision-translate-v1`은 PDF를 각 페이지별 PNG 이미지로 변환한 후, 이미지 분석 결과에서 텍스트, 이미지, 표, 레이아웃 정보를 재구성한다.

## 기준

- **새 프로젝트**: `pdf-translate-v3`를 수정하지 않고 독립 프로젝트로 진행한다.
- **운영 호환성**: 기존 번역 프로젝트와 동일하게 `input/`, `output/`, `work/`, `input/done/`, `.env`, `glossary.csv` 패턴을 사용한다.
- **메인 방식**: OpenAI image/vision API를 중심으로 페이지 단위 구조 분석을 수행한다.
- **대상 문서**: 스캔 PDF, 이미지 기반 PDF, PDF 내부 텍스트 추출이 불안정한 문서를 우선 대상으로 한다.
- **출력 목표**: 원본 페이지의 시각 구조를 최대한 유지한 reader-friendly 번역 PDF를 생성한다.
- **구현 범위**: 이 README는 프로젝트 설계 정리이며, 실제 구현은 별도 단계에서 진행한다.

## 핵심 아이디어

```text
input/sample.pdf
  -> PDF page render
  -> work/sample/pages/page-001.png
  -> OpenAI vision layout analysis
  -> work/sample/analysis/page-001.json
  -> translation
  -> work/sample/translated/page-001.json
  -> PDF composition
  -> output/sample_KR.pdf
  -> input/done/sample.pdf
```

기존 PDF-native 방식은 PDF 내부 객체를 직접 읽고 수정한다. 비전 방식은 PDF를 먼저 페이지 이미지로 고정한 뒤, 각 페이지 이미지를 문서 화면으로 보고 전체 레이아웃을 다시 해석한다.

## 입력과 출력

```text
input/sample.pdf
  -> output/sample_KR.pdf
  -> input/done/sample.pdf

work/sample/pages/page-001.png
work/sample/pages/page-002.png

work/sample/analysis/page-001.json
work/sample/analysis/page-002.json

work/sample/segments.json
work/sample/translated.json
work/sample/composition.json
work/sample/report.json
```

## 디렉터리 구조

```text
pdf-vision-translate-v1/
├── README.md
├── INSTALL.md
├── TODO.md
├── .env.example
├── glossary.csv
├── package.json
├── run-translate.sh
├── input/
│   └── done/
├── output/
├── work/
│   └── tm.sqlite
└── src/
    ├── index.mjs
    ├── pipeline.mjs
    ├── render/
    │   └── pdf-to-image.mjs
    ├── vision/
    │   └── openai-layout.mjs
    ├── translate/
    │   └── llm.mjs
    ├── compose/
    │   └── pdf-writer.mjs
    ├── glossary/
    ├── tm/
    └── util/
```

위 구조는 설계안이다. 실제 구현 시 기존 프로젝트들과 호환되는 실행 흐름을 우선한다.

## 파이프라인

### 1. DETECT

`input/` 폴더에서 PDF 파일을 탐색한다.

- `.pdf` 파일만 처리
- 암호화 또는 DRM PDF는 실패 처리
- 파일별 작업 폴더를 `work/{stem}/` 아래 생성
- 기존 산출물이 있으면 재실행 정책에 따라 reuse 또는 reset

### 2. RENDER

PDF를 각 페이지별 PNG 이미지로 렌더링한다.

```text
work/sample/pages/page-001.png
work/sample/pages/page-002.png
```

렌더링 기준:

- 기본 해상도: 200-300 DPI 검토
- 페이지 크기, 회전, crop box 정보 보존
- 페이지별 width, height, dpi, scale metadata 기록
- 원본 시각 품질과 API 비용의 균형 고려

### 3. VISION_ANALYZE

각 PNG 페이지를 OpenAI image/vision API에 전달해 페이지 구조를 분석한다.

분석 대상:

- 텍스트 위치
- 텍스트 내용
- 텍스트 블록 종류
- 제목, 본문, 캡션, 각주, 머리글, 바닥글 구분
- 이미지 위치
- 이미지 내용 설명
- 이미지 좌표
- 표 위치
- 표 내용
- 표 행/열 구조
- 표 선 두께
- 표 border 스타일
- 표 배경색, 셀 병합, 정렬 등 시각 속성
- 페이지 여백, 단 구성, 읽기 순서

산출물 예시:

```text
work/sample/analysis/page-001.json
```

## OpenAI Vision 처리 방식

OpenAI에서 이미지와 관련된 처리는 크게 다음 방식으로 나눠서 검토한다.

| 방식 | 용도 | 이 프로젝트에서의 역할 |
|---|---|---|
| Responses API + image input | 이미지를 입력으로 받아 분석 결과를 text/JSON으로 반환 | 기본 후보. 페이지 PNG를 넣고 layout JSON을 받는 메인 경로 |
| Chat Completions API + image input | 대화형 요청 안에서 이미지를 분석 | 호환 또는 fallback 후보. 기존 chat 기반 구현과 맞출 때 검토 |
| Images API | 이미지 생성 또는 편집 | PDF 번역의 메인 경로는 아님. 이미지 재생성/편집 실험 시에만 검토 |
| Responses API + image_generation tool | text/image 입력을 바탕으로 새 이미지 생성 | 번역 PDF 재조립보다는 이미지 보정/재생성 실험용 |
| Structured Outputs | 모델 응답을 JSON Schema에 맞춰 반환 | vision 분석 결과를 `page`, `blocks`, `tables`, `bbox` schema로 고정하는 핵심 기능 |
| JSON mode | 유효한 JSON 출력을 유도 | Structured Outputs를 쓸 수 없을 때 fallback |

이 프로젝트의 기본 선택은 다음 조합으로 둔다.

```text
Responses API
  + input_image
  + detail: high 또는 original
  + Structured Outputs JSON Schema
  -> work/{stem}/analysis/page-001.json
```

### 이미지 입력 방식

OpenAI vision 요청에 이미지를 넣는 방식은 세 가지다.

1. 이미지 URL 전달
2. Base64 data URL 전달
3. Files API에 업로드한 file ID 전달

로컬 PDF 변환 도구에서는 기본적으로 페이지 PNG가 `work/` 아래 생성되므로, MVP에서는 **Base64 data URL** 방식이 가장 단순하다. 대량 처리나 재시도 비용 최적화가 필요해지면 file ID 방식도 검토한다.

```json
{
  "type": "input_image",
  "image_url": "data:image/png;base64,...",
  "detail": "high"
}
```

### detail 옵션

`detail`은 모델이 이미지를 어느 수준으로 처리할지 정하는 옵션이다.

| detail | 특징 | 사용 후보 |
|---|---|---|
| `low` | 빠르고 저렴하지만 512px 수준의 저해상도 이해에 가깝다 | 문서 전체 분류, 페이지 타입 판단 |
| `high` | 일반적인 고품질 이미지 이해 | MVP 기본값 후보 |
| `original` | 큰 이미지, 조밀한 문서, 좌표 민감 작업에 유리한 고정밀 처리 | 지원 모델 사용 시 표/좌표 추출 후보 |
| `auto` | 모델이 자동 선택 | 기본 동작 검증 또는 비용 비교용 |

PDF 페이지 분석은 작은 글자, 표, 좌표, 줄 단위 구분이 중요하다. 따라서 `low`는 메인 분석에는 부적합하고, 기본은 `high`, 가능하면 `original`을 실험한다.

### 단일 페이지 요청과 다중 페이지 요청

OpenAI vision은 한 요청에 여러 이미지를 넣을 수 있다. 다만 PDF 번역에서는 다음 이유로 **페이지당 1 요청**을 기본으로 둔다.

- 페이지별 실패 재시도가 쉽다.
- `work/sample/analysis/page-001.json`처럼 산출물 관리가 단순하다.
- 긴 PDF에서 토큰/TPM 제한을 제어하기 쉽다.
- 페이지별 prompt를 다르게 줄 수 있다.
- 특정 페이지만 재분석하기 쉽다.

다중 페이지 요청은 다음 경우에만 검토한다.

- 2페이지 spread 문서
- 앞뒤 페이지 맥락이 강한 표/그림 설명
- header/footer, footnote 연결 판단
- 비용보다 문맥 정확도가 중요한 소량 문서

### Structured Outputs 사용

이 프로젝트는 단순 설명문이 아니라 PDF 재조립용 좌표와 블록 구조가 필요하다. 따라서 일반 자연어 응답보다 Structured Outputs를 우선한다.

요구사항:

- root schema는 object로 둔다.
- 모든 필드는 required로 정의한다.
- object에는 `additionalProperties: false`를 둔다.
- optional 값은 `null` union으로 표현한다.
- schema가 복잡해지면 page, block, table, cell subschema로 분리한다.

Structured Outputs를 사용할 수 없는 모델이나 환경에서는 JSON mode를 fallback으로 쓰되, validator와 retry를 반드시 둔다.

### Vision 처리 한계

OpenAI vision은 OCR 전용 엔진이나 문서 분석 전용 엔진과 다르다. 다음 항목은 confidence와 검증 로직이 필요하다.

- 아주 작은 글자
- 회전되거나 기울어진 텍스트
- 한국어/일본어/중국어 등 non-Latin 텍스트
- 표의 정확한 선 두께와 셀 병합
- 그래프의 색상/선 스타일/범례 해석
- 정밀 좌표 추정
- 긴 문서의 페이지 간 일관성

따라서 MVP에서는 OpenAI vision을 “페이지 구조를 추정하는 주 엔진”으로 쓰되, 좌표와 표 구조는 후처리 검증을 전제로 한다.

### 4. NORMALIZE

OpenAI vision 응답을 프로젝트 내부 공통 schema로 정규화한다.

목표:

- 페이지 좌표계를 일관되게 정리
- reading order 부여
- 번역 대상 텍스트와 비번역 요소 분리
- 표를 cell 단위 구조로 변환
- 이미지와 장식 요소를 구분
- confidence, warnings, unresolved 항목 기록

### 5. TRANSLATE

정규화된 텍스트 블록을 OpenAI 또는 Azure OpenAI로 번역한다.

기존 프로젝트와 호환되는 정책:

- `glossary.csv` 사용
- protected term placeholder 처리
- SQLite Translation Memory 사용
- 동일 문장 재호출 방지
- `en`, `kr`, `jp`, `ch` 등 기존 언어 코드 체계 유지

번역 대상:

- 일반 텍스트 블록
- 표 셀 텍스트
- 캡션
- 도형 내부 텍스트
- 필요한 경우 이미지 속 텍스트

번역 제외 후보:

- 로고
- 제품명
- URL
- 코드
- 고유 식별자
- 페이지 번호
- glossary protected term

### 6. COMPOSE

분석/번역 결과를 기반으로 새 PDF를 생성한다.

구성 방식 후보:

1. 원본 페이지 PNG를 배경 이미지로 깔고 번역 텍스트를 overlay
2. 원본 페이지 이미지를 사용하지 않고 layout object를 다시 그려 vector/text PDF 생성
3. 페이지별로 원본 이미지 + 선택 가능한 invisible text layer를 함께 생성
4. 표와 텍스트만 재구성하고 복잡한 이미지는 원본 crop을 유지

초기 MVP는 다음 방식을 우선 검토한다.

```text
원본 페이지 PNG 배경 + 번역 텍스트 overlay + 필요 시 whiteout rectangle
```

이 방식은 원본 시각 구조를 가장 빨리 보존할 수 있다. 다만 파일 크기, 검색 가능성, 텍스트 선택 품질은 별도 개선 대상이다.

### 7. DONE

성공한 원본 PDF는 `input/done/`으로 이동한다.

실패한 파일은 원본을 유지하고 `work/{stem}/report.json`에 실패 원인을 기록한다.

## OpenAI Vision 분석 Schema 초안

페이지 단위 분석 결과는 다음 형태를 목표로 한다.

```json
{
  "page": 1,
  "width": 2480,
  "height": 3508,
  "dpi": 300,
  "rotation": 0,
  "languageHints": ["en"],
  "blocks": [
    {
      "id": "p1-b001",
      "type": "text",
      "role": "heading",
      "bbox": { "x": 120, "y": 180, "width": 1800, "height": 96 },
      "text": "Original heading text",
      "readingOrder": 1,
      "style": {
        "fontSizeApprox": 28,
        "bold": true,
        "italic": false,
        "color": "#111111",
        "align": "left"
      },
      "confidence": 0.92
    },
    {
      "id": "p1-b002",
      "type": "image",
      "bbox": { "x": 120, "y": 340, "width": 900, "height": 520 },
      "description": "Product architecture diagram",
      "containsText": true,
      "confidence": 0.88
    },
    {
      "id": "p1-b003",
      "type": "table",
      "bbox": { "x": 120, "y": 920, "width": 2100, "height": 760 },
      "rows": 5,
      "columns": 4,
      "border": {
        "style": "solid",
        "thicknessApprox": 1,
        "color": "#444444"
      },
      "cells": [
        {
          "row": 0,
          "column": 0,
          "rowSpan": 1,
          "columnSpan": 1,
          "bbox": { "x": 120, "y": 920, "width": 525, "height": 120 },
          "text": "Header",
          "backgroundColor": "#f2f2f2",
          "align": "center"
        }
      ],
      "confidence": 0.84
    }
  ],
  "warnings": []
}
```

## PDF Composition Schema 초안

PDF 재조립 단계는 vision 분석 결과와 번역 결과를 합쳐 composition plan을 만든다.

```json
{
  "source": "input/sample.pdf",
  "target": "output/sample_KR.pdf",
  "pages": [
    {
      "page": 1,
      "widthPt": 595.28,
      "heightPt": 841.89,
      "backgroundImage": "work/sample/pages/page-001.png",
      "operations": [
        {
          "type": "whiteout",
          "bboxPt": { "x": 28, "y": 42, "width": 430, "height": 32 },
          "color": "#ffffff"
        },
        {
          "type": "text",
          "bboxPt": { "x": 28, "y": 42, "width": 430, "height": 32 },
          "text": "번역된 제목",
          "font": "Malgun Gothic",
          "fontSize": 14,
          "color": "#111111",
          "align": "left"
        }
      ]
    }
  ]
}
```

## CLI 목표

기존 프로젝트와 비슷한 사용성을 목표로 한다.

```bash
chmod +x run-translate.sh
cp .env.example .env
vi .env
./run-translate.sh
```

예상 명령:

```bash
./run-translate.sh
./run-translate.sh --in-lang en --out-lang kr
./run-translate.sh input/sample.pdf

./run-translate.sh render input/sample.pdf
./run-translate.sh analyze work/sample/pages
./run-translate.sh translate work/sample/segments.json --in-lang en --out-lang kr
./run-translate.sh compose input/sample.pdf work/sample/translated.json --out-lang kr
```

## 환경 변수 초안

```env
OPENAI_API_KEY=
OPENAI_VISION_MODEL=gpt-4.1
OPENAI_TRANSLATE_MODEL=gpt-4.1-mini

PDF_RENDER_DPI=300
PDF_RENDER_FORMAT=png
PDF_OUTPUT_SUFFIX=KR

SOURCE_LANG=en
TARGET_LANG=kr

PDF_FONT_PATH=C:/Windows/Fonts/malgun.ttf
WORK_DIR=work
INPUT_DIR=input
OUTPUT_DIR=output
```

Azure OpenAI를 병행 지원할 경우 기존 프로젝트와 동일한 분기 구조를 둔다.

```env
LLM_PROVIDER=openai
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=
AZURE_OPENAI_VISION_DEPLOYMENT=
AZURE_OPENAI_TRANSLATE_DEPLOYMENT=
```

## 기존 프로젝트와의 호환 포인트

- `input/`, `output/`, `work/`, `input/done/` 운영 방식 유지
- `run-translate.sh` 진입 방식 유지
- `.env.example` 기반 설정 유지
- `glossary.csv` 형식 유지
- SQLite Translation Memory 재사용 가능성 검토
- `segments.json`, `translated.json` 이름 유지
- 언어 코드 `en`, `kr`, `jp`, `ch` 유지
- 성공 시 원본 이동, 실패 시 원본 보존 정책 유지
- LLM provider 분기 구조는 기존 `OpenAI / Azure OpenAI` 방식과 맞춤

## 장점

- 스캔 PDF와 이미지 기반 PDF 처리 가능
- PDF 내부 텍스트 인코딩 문제의 영향을 적게 받음
- 사람이 보는 페이지 기준으로 레이아웃 분석 가능
- 표, 이미지, 캡션, 다단 문서 등 시각 구조 중심 분석 가능
- 원본 PDF 구조가 복잡하거나 깨져 있어도 접근 가능

## 한계와 주의점

- 페이지 이미지를 API에 보내므로 비용이 높을 수 있음
- 고해상도 PNG 생성으로 `work/` 용량이 커질 수 있음
- OpenAI vision 응답만으로 정확한 좌표 재현이 어려울 수 있음
- 표의 선 두께, 셀 병합, 배경색 등 시각 속성은 confidence 기반으로 다뤄야 함
- 원본 PDF의 vector/text 품질을 그대로 보존하기 어렵다
- 출력 PDF가 이미지 기반이 되면 파일 크기가 커지고 텍스트 선택성이 떨어질 수 있다
- 민감 문서 처리 시 외부 API 전송 정책을 반드시 확인해야 한다

## MVP 제안

### MVP 1: 페이지 이미지 기반 번역 PDF

- PDF를 페이지별 PNG로 렌더링
- OpenAI vision으로 텍스트 블록과 읽기 순서 추출
- 텍스트 블록 번역
- 원본 페이지 PNG 배경 위에 whiteout + 번역 텍스트 overlay
- `output/{stem}_KR.pdf` 생성

### MVP 2: 표 구조 지원

- table block schema 안정화
- cell 단위 번역
- 표 영역 whiteout 후 간단한 table redraw
- border thickness, alignment, background color 일부 반영

### MVP 3: 이미지/도형 설명 metadata

- 이미지 좌표와 설명 추출
- 이미지 내부 텍스트 번역 옵션 추가
- figure caption 연결
- `report.json`에 이미지 설명 저장

### MVP 4: 검색 가능한 PDF 개선

- visible translated text layer 품질 개선
- invisible OCR text layer 옵션 검토
- 원본 이미지 crop 재사용
- 파일 크기 최적화

## 제외 범위

- DRM 또는 암호 PDF 우회
- 원본 PDF 객체를 완전 보존하는 PDF-native 편집
- OpenAI vision 응답을 무조건 신뢰하는 자동 보정 없는 처리
- 복잡한 CAD 도면, 매우 큰 지도, 수식 중심 논문에 대한 완전 재현
- Word/PPT/EPUB 번역 기능

## 프로젝트 판단

`pdf-vision-translate-v1`은 `pdf-translate-v3`의 대체가 아니라 보완 프로젝트다.

- 일반 텍스트 PDF: `pdf-translate-v3` 우선
- 스캔 PDF: `pdf-vision-translate-v1` 우선
- PDF 내부 텍스트 추출 실패 문서: `pdf-vision-translate-v1` fallback 후보
- 원본 품질 보존이 중요한 문서: PDF-native 방식 우선
- 읽기용 번역본 생성이 중요한 문서: vision 방식 검토
