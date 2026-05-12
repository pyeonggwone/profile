# pdf-translate-v12

`pdf-translate-v12`는 v11에서 검증된 PDF 번역 파이프라인을 정리한 독립 프로젝트다. 실행 잔재, 가상환경, Node 관련 파일, 이전 작업 산출물을 포함하지 않는다.

## 목표

- 원본 PDF의 비텍스트 요소는 `textless-base` 배경으로 보존한다.
- 단계별 PDF는 `base`, `base + source text`, `base + translated text`로 분리한다.
- 번역문은 새 PDF text layer로 작성한다.
- whiteout box overlay 방식은 사용하지 않는다.
- 원본 텍스트의 위치, 색상, 굵기, 크기, 표/문단 context를 최대한 반영한다.
- 단계별 PDF를 `work/<job-id>/pdf/stages/`에 보존한다.
- 복원/최적화/게시용 PDF는 별도 stage로 만들지 않고 `base + translated text` 산출물을 검증 후 최종 출력으로 복사한다.
- 특수문자는 원문에 있는 경우만 유지하고, 원문에 없는 장식 문자는 제거한다.

## 구조

```text
pdf-translate-v12/
├── .env.example
├── README.md
├── build.md
├── install.md
├── requirements.txt
├── run-v12.sh
├── glossary.csv
├── fonts/
├── input/
├── output/
├── work/
└── src/
    └── pdf_translate_v12/
        ├── __init__.py
        └── pipeline.py
```

## 제외된 잔재

v12에는 다음 항목을 포함하지 않는다.

- `.env` secret 파일
- `.venv`, `.venv-wsl`
- `node_modules`
- `package.json`, `package-lock.json`
- 기존 `work` job 산출물
- 기존 `output` PDF
- 기존 `input` PDF
- v11 실험 문서와 TODO/계획 문서

## 빠른 실행

```bash
cd /mnt/c/Users/v-kimpy/test/profile/Microsoft/PTC/News/pdf-translate-v12
./run-v12.sh bootstrap
./run-v12.sh doctor
./run-v12.sh input/sample.pdf
```

처음 실행 시 `.env`가 없으면 `.env.example`에서 자동 생성한다.

## 주요 산출물

```text
work/<job-id>/pdf/stages/
├── 01-base.pdf
├── 02-source-text-on-base.pdf
└── 03-translated-text-on-base.pdf
```

최종 PDF는 `output/`에 생성된다.

## Base text layer 작성 규칙

`base` PDF에 영문 원문이나 번역문을 입력할 때는 PDF를 직접 문자열 치환하지 않는다. 각 단계의 JSON을 기준으로 새 text layer를 작성한다.

```text
segments.json
→ source-positioned-layout.json
→ 02-source-text-on-base.pdf

translated.json
→ shaped-runs.json
→ positioned-layout.json
→ 03-translated-text-on-base.pdf
```

### 원문 입력

- 입력 JSON: `work/<job-id>/state/segments.json`
- 기준 필드: `segments[].source`
- 레이아웃 JSON: `work/<job-id>/state/source-positioned-layout.json`
- 작성 함수: `step_10_build_source_pdf()`
- 레이아웃 함수: `_layout_text_items(source_items, "source", "source-text")`
- PDF 작성 함수: `_build_text_layer_pdf()`
- 산출물: `work/<job-id>/pdf/stages/02-source-text-on-base.pdf`

영문 원문은 `segments[].source` 값을 그대로 사용한다. 다만 PDF에 쓰기 전에는 레이아웃 엔진이 줄바꿈과 영역 맞춤을 적용한다. Pango가 가능하면 `_layout_with_pango()`가 `WORD_CHAR` wrapping과 폰트 크기 축소를 수행하고, 불가능하면 `_layout_with_custom_wrapper()`가 `wrap_text_by_width()`로 줄바꿈한다.

### 번역문 입력

- 입력 JSON: `work/<job-id>/state/translated.json`
- 기준 필드: `segments[].translated`
- shaping JSON: `work/<job-id>/state/shaped-runs.json`
- 레이아웃 JSON: `work/<job-id>/state/positioned-layout.json`
- 작성 함수: `step_14_build_translated_pdf()`
- 레이아웃 함수: `step_13_layout_text()`
- PDF 작성 함수: `_build_text_layer_pdf()`
- 산출물: `work/<job-id>/pdf/stages/03-translated-text-on-base.pdf`

번역문은 `translated.json`의 `segments[].translated` 값을 기준으로 한다. 번역 결과가 없거나 실패한 경우에는 `source`를 fallback으로 사용한다. 번역 후 `align_translation_decoration()`으로 원문에 있던 bullet, 번호, 기호만 보존하고, `collapse_repeated_translation()`으로 반복 번역을 줄인다.

### PDF 작성 엔진

`_build_text_layer_pdf()`는 같은 레이아웃 JSON을 받아 다음 순서로 PDF text layer를 작성한다.

1. `ReportLab`: 기본 작성 엔진. `_build_pdf_with_reportlab()`이 배경 이미지를 깔고 `drawString()`으로 텍스트를 쓴다.
2. `Cairo + Pango`: ReportLab을 사용할 수 없을 때 `_build_pdf_with_cairo()`가 Pango layout으로 텍스트를 쓴다.
3. `PyMuPDF`: 위 엔진이 실패하고 degraded mode가 허용될 때 `_build_pdf_with_pymupdf()`가 `insert_textbox()`로 작성한다.

문자 단위 변환은 `_sanitize_draw_character()`에서 수행한다. zero-width 문자와 BOM은 제거하고, non-breaking space는 일반 공백으로 바꾸며, `ff`, `fi`, `fl` 같은 ligature 문자는 일반 문자열로 풀어서 쓴다. PDF에 없는 장식 문자는 새로 추가하지 않는다.
