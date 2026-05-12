# DESIGN.md — pdf-translate-v11 디자인

이 문서는 `pdf-translate-v11` 의 시스템 디자인을 정의한다.

v11은 원본 PDF를 번역 PDF로 재생성하는 품질 우선 파이프라인이다. 모든 기능을 하나의 PDF 엔진에 몰아넣지 않고, 기능별 최적 도구를 연결한다.

## 디자인 목표

- 원본 PDF는 읽기 전용으로 유지한다.
- 결과 PDF는 새로 생성한다.
- 원본의 시각 구조와 PDF object 정보를 최대한 보존한다.
- 텍스트, 이미지 텍스트, 표, 도형, 주석, 링크, bookmark를 별도 데이터로 추출한다.
- 모든 중간 상태는 명시적인 파일로 저장한다.
- 모든 도구는 같은 상태 파일 계약을 따른다.
- 최종 결과는 자동 검증한다.

## 시스템 구성

```text
                 ┌────────────────────┐
                 │     run-v11.sh      │
                 │  pipeline runner    │
                 └─────────┬──────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
  │ state store │   │ artifacts   │   │ tool steps  │
  │ JSON/SQLite │   │ pdf/png/etc │   │ CLI/scripts │
  └─────────────┘   └─────────────┘   └─────────────┘
```

`run-v11.sh` 는 orchestration만 담당한다. PDF 처리 로직은 각 단계 도구/script가 담당한다.

## 주요 컴포넌트

| 컴포넌트 | 책임 |
|---|---|
| `run-v11.sh` | 전체 단계 실행, 상태 갱신, 실패 처리 |
| state schema | 단계 간 데이터 계약 정의 |
| QPDF step | 원본/결과 PDF validation, 최종 구조 정리 |
| pikepdf step | object/resource/image/annotation/link/bookmark manifest 생성과 복원 |
| PDFium step | page render, text bbox, render diff |
| Poppler step | font/glyph 상태 분석 |
| pdfplumber step | table structure detection |
| OCR step | image text extraction |
| translation step | glossary, TM, LLM 번역 |
| HarfBuzz step | glyph shaping |
| Pango step | text layout, line breaking, fallback font |
| Cairo step | shaped text drawing, vector drawing 재생성 |
| ReportLab step | 새 PDF 문서 생성 |
| PDFBox step | form / AcroForm 처리 |
| Ghostscript step | 선택적 강한 압축 |
| veraPDF step | PDF/A validation |

## 상태 저장소 디자인

v11은 단일 DB에 모든 것을 넣지 않는다. 데이터 성격에 맞는 상태 파일을 사용한다.

| 상태 | 저장소 | 설명 |
|---|---|---|
| job 상태 | JSON | 현재 단계, 성공/실패, 산출물 경로 |
| artifact manifest | JSON | 각 단계 산출물 위치 |
| object manifest | JSON | PDF object/resource/image/annotation/link/bookmark 목록 |
| text bbox | JSON | page/line/span/glyph 좌표 |
| table layout | JSON | table/cell/row/column 구조 |
| OCR layout | JSON | OCR text, bbox, confidence |
| translation segments | JSON + SQLite | 사람이 읽는 JSON, 재시도/상태 관리는 SQLite |
| Translation Memory | SQLite | source/target/model/lang 기반 캐시 |
| render images | PNG | 원본/결과 렌더링 이미지 |
| quality report | JSON | render diff, text coverage, overflow |
| glossary | CSV | 사용자 편집 가능 용어집 |

## 상태 디렉토리

```text
work/<job-id>/
├── state/
│   ├── job.json
│   ├── artifacts.json
│   ├── validation.json
│   ├── object-manifest.json
│   ├── text-bbox.json
│   ├── font-report.json
│   ├── table-layout.json
│   ├── ocr-layout.json
│   ├── segments.json
│   ├── translated.json
│   ├── shaped-runs.json
│   ├── positioned-layout.json
│   ├── output-validation.json
│   ├── render-diff.json
│   └── error.json
├── pages/
│   ├── source/
│   └── output/
├── objects/
├── layout/
├── pdf/
│   ├── draft.pdf
│   ├── enriched.pdf
│   └── optimized.pdf
└── reports/
```

## PDF 생성 디자인

v11은 원본 PDF를 계속 직접 수정하지 않는다.

디자인:

1. 원본 PDF에서 보존 대상 object를 manifest로 추출한다.
2. 텍스트, 표, 도형, 이미지, OCR 결과를 layout data로 변환한다.
3. 번역문을 shaping/layout 처리한다.
4. ReportLab으로 새 PDF 초안을 만든다.
5. Cairo는 shaped text drawing과 vector drawing 단계에서 사용한다.
6. pikepdf로 annotation/link/bookmark/metadata를 복원한다.
7. QPDF로 구조 정리와 linearization을 수행한다.
8. PDFium으로 render diff를 수행한다.
9. 품질 기준을 통과하면 최종 PDF로 배치한다.

## 좌표계 디자인

모든 layout 상태는 공통 좌표계를 사용한다.

기준:

- page 좌상단 origin 기반 normalized layout 좌표
- PDF native 좌표가 필요한 단계에서는 변환 layer를 둔다.
- page width/height를 모든 layout object에 포함한다.
- bbox는 `x`, `y`, `width`, `height` 와 `left`, `top`, `right`, `bottom` 을 함께 저장한다.

예:

```json
{
  "page": 1,
  "pageWidth": 612,
  "pageHeight": 792,
  "bbox": {
    "x": 72,
    "y": 108,
    "width": 220,
    "height": 24,
    "left": 72,
    "top": 108,
    "right": 292,
    "bottom": 132
  }
}
```

## 번역 segment 디자인

segment는 원문, 위치, 스타일, 번역 상태를 모두 가진다.

```json
{
  "id": "p001-s0001",
  "source": "Original text",
  "translated": "번역 텍스트",
  "sourceLang": "en",
  "targetLang": "kr",
  "page": 1,
  "bbox": {
    "x": 72,
    "y": 108,
    "width": 220,
    "height": 24
  },
  "style": {
    "fontSize": 12,
    "fontWeight": 400,
    "color": [0, 0, 0]
  },
  "origin": "pdf-text",
  "status": "translated"
}
```

`origin` 값:

| 값 | 의미 |
|---|---|
| `pdf-text` | PDF text object에서 추출 |
| `ocr-image` | OCR에서 추출 |
| `table-cell` | table detection에서 생성 |
| `annotation` | annotation에서 추출 |
| `form-field` | form field에서 추출 |

## 품질 검증 디자인

품질 검증은 최종 단계가 아니라 release gate다.

| 검증 | 기준 |
|---|---|
| text coverage | 필수 segment가 출력 PDF에 포함되어야 함 |
| render diff | 원본과 결과의 비텍스트 구조가 허용 범위 안에 있어야 함 |
| layout overflow | 번역문이 page 밖으로 나가거나 심각하게 겹치면 실패 |
| PDF validation | QPDF validation 통과 |
| OCR coverage | OCR 대상 이미지 텍스트가 처리되었는지 확인 |
| object preservation | annotation/link/bookmark 복원 여부 확인 |

## 오류 처리 디자인

오류는 반드시 상태 파일로 남긴다.

```json
{
  "step": "12_build_draft_pdf",
  "tool": "ReportLab",
  "severity": "fatal",
  "message": "Failed to create page 12",
  "recoverable": false,
  "recordedAt": "2026-05-10T00:00:00.000Z"
}
```

오류 severity:

| 값 | 의미 |
|---|---|
| `info` | 참고 정보 |
| `warning` | 계속 가능하지만 품질 저하 가능 |
| `recoverable` | 재시도 또는 fallback 가능 |
| `fatal` | pipeline 중단 |

## 디자인 결론

v11 디자인의 핵심은 다음이다.

```text
단일 실행 진입점
다중 도구 단계
공통 상태 schema
원본 PDF 읽기 전용
새 PDF 조립
자동 품질 검증
기능별 최고 품질 도구 연결
```

이 구조는 복잡하지만, 원본 PDF를 최대한 보존하면서 번역 PDF를 새로 생성하기 위한 방향으로 가장 적합하다.
