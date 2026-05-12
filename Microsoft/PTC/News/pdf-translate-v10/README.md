# pdf-translate-v10

## 목표

v10은 원본 PDF의 비텍스트 요소를 유지한 복제본 위에 텍스트를 새로 조판하는 PDF 번역 프로젝트다.

v10의 차이는 구현 언어와 PDF/text 처리 도구다.

```text
구현 언어는 Python이다.
PDF object/stream 접근, 비텍스트 요소 복사, 최종 저장은 pikepdf를 사용한다.
텍스트 추출과 layout 관찰은 pdfplumber와 pdfminer.six를 함께 사용한다.
텍스트 재조판 PDF layer 생성은 reportlab을 사용한다.
qpdf는 project-local reference/check 도구로 유지한다.
SQLite는 job 상태, step 상태, Translation Memory, term memory를 저장한다.
OpenAI 또는 Azure OpenAI는 사람이 읽기 좋은 JSON의 text만 번역한다.
최종 PDF는 텍스트가 제거된 PDF base 위에 번역 텍스트를 새로 작성한다.
```

## 핵심 원칙

```text
비텍스트 객체는 재구성하지 않는다.
이미지, 도형, 표, 배경, page resource, XObject는 원본 PDF object를 유지한다.

원본 텍스트는 바이너리 복사하지 않는다.
pikepdf로 source PDF의 content stream에서 text object block을 제거한 textless base를 만들고, 텍스트는 추출 결과를 기준으로 새로 작성한다.

원문 복제 검증용 PDF는 두 가지로 만든다.
pdfminer.six 추출 결과 기반 clone과 pdfplumber 추출 결과 기반 clone을 각각 생성한다.

번역은 decoded text만 대상으로 한다.
OpenAI는 PDF 구조나 operator를 알 필요가 없다.

번역 PDF는 원문 복제 PDF 위에 쓰지 않는다.
비텍스트 요소만 남긴 textless base 위에 번역된 한국어 텍스트를 새로 작성한다.
```

## 사용 도구

| 역할 | 도구 |
|---|---|
| PDF 구조 normalize/reference | qpdf |
| PDF object/stream 직접 처리 | pikepdf |
| text extraction/layout observation | pdfplumber |
| low-level text/page layout analysis | pdfminer.six |
| text layer PDF generation | reportlab |
| JSON 저장/변환 | Python dataclasses, json |
| 상태 DB/Translation Memory | SQLite |
| OpenAI 번역 | OpenAI API 또는 Azure OpenAI API |
| 최종 PDF 검증 | qpdf --check, pikepdf open/save smoke check |

v10에서는 PyMuPDF를 사용하지 않는다. 텍스트를 새로 쓰기 위한 PDF layer 생성에는 reportlab을 사용한다.

## 전체 구조

v10의 처리 구조는 다음 순서로 고정한다.

```text
input PDF
  -> qpdf가 PDF stream/object 구조를 풀어 reference 생성
  -> pikepdf가 원본 PDF object/resource/content stream을 읽고 textless base를 생성한다
  -> pdfplumber/pdfminer.six가 text run과 layout 후보를 추출한다
  -> Python parser가 가능한 범위의 text operator/state/font/CMap/range를 raw JSON에 결합한다
  -> raw JSON을 사람이 읽기 좋은 번역용 JSON으로 변환한다
  -> SQLite가 job 상태, step 상태, TM hit/miss를 기록한다
  -> job별 고유명사 후보와 용어집을 저장한다
  -> OpenAI가 번역용 JSON의 text만 번역한다
  -> pdfminer.six 기반 원문 복제 PDF와 pdfplumber 기반 원문 복제 PDF를 생성한다
  -> 번역 결과를 textless base 위에 새 텍스트로 조판한다
  -> qpdf가 최종 PDF를 검증한다
  -> output PDF
```

도구별 책임은 다음처럼 나눈다.

| 도구 | 책임 | 하지 않는 일 |
|---|---|---|
| qpdf | PDF 구조 풀기, QDF reference 생성, 원본/최종 PDF 검증 | 번역, text payload 교체 로직 |
| pikepdf | PDF object tree 읽기/쓰기, textless base 저장, layer 조합 | text layout 의미 추론, 번역 |
| pdfplumber | page text/char/bbox 추출, layout 관찰 | PDF object 저장, stream byte range 보장 |
| pdfminer.six | LTTextLine/LTChar 기반 보조 추출 | PDF object 저장, 번역 |
| reportlab | 원문/번역 텍스트 layer PDF 생성 | PDF object 복사, 번역 |
| Python parser | content stream text object 제거, text state 결합 | PDF 구조 검증 |
| OpenAI | decoded text 번역 | PDF 구조 해석 |

## 파이프라인 단계

```text
01_init_job
02_qpdf_reference
03_extract_raw_pdf_text_state
04_convert_raw_to_readable_text_state
05_extract_and_apply_job_terms
06_translate_readable_text_state
07_convert_translation_to_pdf_input_state
08_rebuild_pdf_with_extracted_options
09_qpdf_validate_output
10_publish_output
```

## 구현 프로젝트 구조

```text
pdf-translate-v10/
├── README.md
├── pyproject.toml
├── .env.example
├── glossary.csv
├── input/
│   ├── README.md
│   ├── ready/README.md
│   ├── done/README.md
│   └── failed/README.md
├── output/
│   ├── README.md
│   ├── validated/README.md
│   ├── rejected/README.md
│   └── reports/README.md
├── work/README.md
└── src/pdf_translate_v10/
    ├── cli.py
    ├── pipeline.py
    ├── config.py
    ├── paths.py
    ├── models.py
    ├── qpdf.py
    ├── extract.py
    ├── readable.py
    ├── terms.py
    ├── translate.py
    ├── encode.py
    ├── rebuild.py
    ├── validation.py
    └── state_db.py
```

## 실행 전제

```text
Python 3.11 이상 필요
pikepdf 필요
pdfplumber 필요
pdfminer.six 필요
reportlab 필요
qpdf 필요
OPENAI_API_KEY 또는 Azure OpenAI 설정 필요
```

설치 예시:

```powershell
cd profile\Microsoft\PTC\News\pdf-translate-v10
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

프로젝트 루트의 `.env`는 실행 시 자동으로 읽는다. 이미 OS 환경변수에 값이 있으면 OS 환경변수를 우선한다.

qpdf 실행 파일은 v10 프로젝트 내부 상대경로에서만 자동으로 탐색한다. 전역 package manager로 설치하지 않는다.

탐색 순서:

```text
QPDF_BIN                 상대경로면 v10 루트 기준
tools/qpdf/bin/qpdf
tools/qpdf/qpdf
tools/qpdf/bin/qpdf.exe
tools/qpdf/qpdf.exe
tools/bin/qpdf
tools/bin/qpdf.exe
```

## 실행 방식

기본 실행은 `input` 폴더 바로 아래의 모든 PDF를 파일명 순서대로 처리한다.

```powershell
python -m pdf_translate_v10
```

동일한 기본 batch 처리를 명시하려면 다음처럼 실행한다.

```powershell
python -m pdf_translate_v10 run
```

특정 파일이나 특정 디렉토리만 처리할 수도 있다.

```powershell
python -m pdf_translate_v10 run .\input\sample.pdf
python -m pdf_translate_v10 run .\input
```

이미 생성된 `pdf-input-text-state.json`을 기준으로 rebuild, validation, publish만 다시 수행하려면 `finalize`를 사용한다. 이 명령은 OpenAI 번역을 다시 호출하지 않는다.

```powershell
python -m pdf_translate_v10 finalize <job>
```

번역 언어와 모델은 `run` 명령에서 지정한다.

```powershell
python -m pdf_translate_v10 run --source-lang en --target-lang ko --model gpt-4o-mini
```

명령 옵션이 없으면 `.env`의 `SOURCE_LANG`, `TARGET_LANG`, `OPENAI_MODEL`을 사용한다.

OpenAI 요청은 전체 text run을 한 번에 보내지 않는다. PDF 자체는 분할하지 않고, 추출된 readable text item만 page range 기준 part로 나누어 병렬 번역한다. 각 part 안에서는 `.env`의 `OPENAI_CHUNK_SIZE` 단위로 요청한다. 기본값은 100이다.

번역 part 수는 `.env`의 `TRANSLATION_PARALLELISM`으로 지정할 수 있다. `0` 또는 미설정이면 page 수 기준으로 자동 결정한다. 20 page 미만은 3개, 50 page 미만은 5개, 그 외는 10개 part를 사용한다.

병렬 번역 산출물은 다음 위치에 저장된다.

```text
work/jobs/<job>/state/translation-input-part-0001.json
work/jobs/<job>/state/translation-input-part-0001-chunk-0001.json
work/jobs/<job>/state/translation-chunk-report-part-0001-0001.json
work/jobs/<job>/state/translation-results-part-0001.json
work/jobs/<job>/state/translation-report-part-0001.json
work/jobs/<job>/reports/translation-report.json
```

## 현재 구현 상태

v10은 overlay 방식이 아니라 textless base compose 방식으로 동작한다. 먼저 pikepdf가 원본 PDF에서 text object block을 제거해 `textless-base.pdf`를 만든다. 이 파일은 이미지, 도형, 표, 배경 같은 비텍스트 요소를 원본 PDF object 기반으로 유지한다.

원문 복제 검증용으로 두 파일을 만든다.

```text
work/jobs/<job>/pdf/clone-pdfminer.pdf
work/jobs/<job>/pdf/clone-pdfplumber.pdf
```

번역 PDF는 원문 복제 PDF가 아니라 같은 `textless-base.pdf` 위에 번역 결과를 새로 작성해 만든다.

```text
work/jobs/<job>/pdf/translated.pdf
work/jobs/<job>/pdf/rebuilt.pdf
```

`rebuilt.pdf`는 publish 단계에서 `translated.pdf`와 같은 내용으로 저장된다. `FONT_REGULAR`, `FONT_FALLBACK`, `FONT_BOLD` 중 존재하는 font를 사용하며, v10 `fonts` 폴더에 font가 없으면 같은 상위 폴더의 v9 `fonts` 폴더도 자동 탐색한다.