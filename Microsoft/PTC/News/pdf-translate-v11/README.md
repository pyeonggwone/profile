# pdf-translate-v11

`pdf-translate-v11` 은 독립 실행되는 품질 우선 PDF 번역 프로젝트다. 사용자가 보는 시각 결과를 기준으로 원본의 비텍스트 요소와 글자 색/style을 최대한 유지하면서 번역 텍스트를 새로 작성한다.

v11은 프로젝트 내부의 code, font, input, output, work 디렉터리만 사용한다. 흰색 박스로 원문 글자 영역을 덮지 않고, textless base를 배경으로 사용한 뒤 텍스트만 작성한다.

## 목표

```text
원본 PDF -> 구조 분석 -> 텍스트/이미지/도형/표/OCR 추출 -> 번역 -> 레이아웃 재구성 -> 새 번역 PDF 생성 -> 품질 검증
```

핵심 목표:

- 원본 PDF 위에 whiteout 방식으로 덮어쓰지 않는다.
- 원본 PDF에서 텍스트를 제거한 textless base를 만들고, 그 위에 텍스트만 작성한다.
- 글자 색, font size, bbox 기반 layout style은 기존 추출 결과를 최대한 유지한다.
- 번역은 chunk 단위 병렬 처리한다.
- 새 PDF를 생성한다.
- 원본의 구조, 이미지, 도형, 표, 주석, 링크, bookmark를 최대한 보존한다.
- 텍스트 누락을 막는다.
- 이미지 안 텍스트는 OCR로 보완한다.
- CJK 번역문은 shaping, fallback font, line breaking을 별도 처리한다.
- 최종 결과는 render diff로 검증한다.
- 실행 진입점은 `.sh` 하나로 통합한다.
- 내부 단계는 Python, Node, Java, CLI 등 필요한 언어와 도구를 사용한다.
- 단계 간 상태는 JSON, CSV, SQLite 등 공통 상태 파일로 공유한다.

## 원칙

| 원칙 | 설명 |
|---|---|
| 기능별 최적 도구 사용 | 한 엔진이 모든 PDF 기능을 최고 품질로 처리한다고 가정하지 않는다. |
| 단일 실행 진입점 | 사용자는 `run-v11.sh` 하나로 전체 파이프라인을 실행한다. |
| 공통 상태 파일 | 각 언어/도구는 같은 상태 파일을 읽고 쓴다. |
| 중간 산출물 명시 | 단계별 PDF, JSON, image, report를 명시적으로 남긴다. |
| 최종 PDF 조립 중심 | 여러 도구가 같은 PDF를 동시에 직접 수정하지 않는다. 상태와 중간 산출물을 기반으로 최종 PDF를 조립한다. |
| 품질 우선 | 구현 난이도, 도구 수, 프로젝트 복잡성보다 번역 PDF 품질을 우선한다. |

## 기능별 주 담당

| 기능 | 주 담당 |
|---|---|
| PDF 무결성 검사 | QPDF |
| PDF 구조 정리 / linearization | QPDF |
| PDF object/resource 보존 | pikepdf |
| image object 추출/보존 | pikepdf |
| annotation/link/bookmark 복사 | pikepdf |
| page 렌더링 | PDFium |
| text/glyph bbox 추출 | PDFium |
| render diff 검증 | PDFium |
| font/glyph 상태 분석 | Poppler |
| table 구조 인식 | pdfplumber |
| 새 PDF 문서 생성 | Cairo |
| glyph shaping | HarfBuzz |
| text layout / fallback font / line breaking | Pango |
| shaped text drawing / vector drawing | Cairo |
| fallback PDF 생성 | ReportLab |
| form / AcroForm 처리 | Apache PDFBox |
| 로컬 OCR | PaddleOCR |
| 클라우드 OCR | Azure AI Vision |
| 강한 재압축 | Ghostscript |
| PDF/A 검증 | veraPDF |

자세한 엔진 설계는 [PDF_ENGINE_ARCHITECTURE.md](PDF_ENGINE_ARCHITECTURE.md) 를 기준으로 한다.

## 실행 모델

사용자는 하나의 shell script만 실행한다.

```bash
./run-v11.sh input/sample.pdf
```

현재 구현된 명령:

```bash
./run-v11.sh doctor
./run-v11.sh bootstrap
./run-v11.sh input/sample.pdf
./run-v11.sh --strict input/sample.pdf
./run-v11.sh --translation-mode openai input/sample.pdf
./run-v11.sh --translation-mode azure-openai input/sample.pdf
./run-v11.sh --ocr local input/sample.pdf
./run-v11.sh --ocr azure input/sample.pdf
```

내부적으로는 단계별 도구가 순서대로 실행된다.

```text
QPDF -> pikepdf -> PDFium -> Poppler -> pdfplumber -> OCR -> LLM -> HarfBuzz -> Pango -> Cairo -> pikepdf -> QPDF -> PDFium diff
```

각 단계는 `work/<job-id>/state/` 아래의 공통 상태 파일을 읽고 쓴다.

## 상태 저장 원칙

| 데이터 | 저장 형식 |
|---|---|
| pipeline 전체 상태 | JSON |
| page/text/bbox/layout | JSON |
| object/resource/image manifest | JSON |
| glossary | CSV |
| Translation Memory | SQLite |
| segment queue / translation status | SQLite 또는 JSONL |
| OCR 결과 | JSON |
| render image | PNG |
| 품질 검증 결과 | JSON |
| 중간 PDF 경로 | JSON manifest |

## 디렉토리 개념

```text
pdf-translate-v11/
├── README.md
├── build.md
├── PDF_ENGINE_ARCHITECTURE.md
├── run-v11.sh                 # 단일 실행 진입점
├── input/                     # 원본 PDF
├── output/                    # 최종 번역 PDF
└── work/
    └── <job-id>/
        ├── state/             # 공통 상태 JSON/SQLite/CSV
        ├── pages/             # render image
        ├── objects/           # object/image/resource manifest
        ├── layout/            # text/table/OCR/layout JSON
        ├── pdf/               # intermediate PDF
        └── reports/           # validation / render diff / error report
```

## v4와의 차이

| 항목 | 이전 방식 | v11 목표 |
|---|---|---|
| PDF 처리 | PyMuPDF 단일 경로 중심 | 기능별 엔진 분리 |
| 실행 | Node + Python 중심 | `.sh` 단일 진입점 + 다중 언어/도구 |
| 상태 공유 | JSON 중심 + SQLite TM | JSON/CSV/SQLite/PNG/report manifest 명시 |
| PDF 생성 | PyMuPDF rebuild | Cairo PDF surface 생성, ReportLab fallback |
| bbox 기준 | PyMuPDF | PDFium |
| text layout | PyMuPDF `insert_textbox()` | HarfBuzz shaping, Pango layout, Cairo drawing을 단계별로 분리 |
| image text | 미구현 | OCR 단계 포함 |
| 품질 검증 | self-test 중심 | PDFium render diff |

## 현재 상태

이 디렉토리는 v11 connector 구현까지 진행된 상태다. 전체 품질 목표 엔진이 모두 연결된 완성본은 아니며, 설치되지 않은 고급 도구는 `degraded`, `skipped`, `missing-tools` 상태로 기록한다.

현재 작성된 문서:

- [PDF_ENGINE_ARCHITECTURE.md](PDF_ENGINE_ARCHITECTURE.md)
- [build.md](build.md)
- [install.md](install.md)
- [EXECUTION_PLAN.md](EXECUTION_PLAN.md)
- [DESIGN.md](DESIGN.md)

현재 구현된 파일:

- `run-v11.sh`
- `src/pdf_translate_v11/pipeline.py`
- `.env.example`
- `requirements.txt`
- `package.json`

현재 동작:

- job/state/artifact 디렉토리 생성
- doctor report 출력
- 원본 PDF validation. QPDF가 없으면 pikepdf degraded validation 사용
- pikepdf object manifest 생성
- PDFium source page render
- PDFium text bbox 추출, PyMuPDF style metadata 보강
- Poppler font report. Poppler가 없으면 degraded report 생성
- pdfplumber table report 생성
- OCR report 생성. `OCR_MODE=local`은 PaddleOCR, `OCR_MODE=azure`는 Azure AI Vision 호출
- segment/translation state 생성
- OpenAI 또는 Azure OpenAI translation mode
- HarfBuzz glyph shaping. Python binding은 `uharfbuzz` 사용
- Pango positioned layout 생성
- Cairo draft PDF 생성. Cairo 사용이 불가능하면 ReportLab fallback 사용
- pikepdf metadata/root entry/page annotation 복원
- enriched/optimized PDF 생성. QPDF가 없으면 Ghostscript degraded optimize 사용
- output validation
- PDFium render diff report 생성
- quality report 생성
- 최종 PDF publish

현재 제한:

- Cairo text drawing은 연결되었지만 vector drawing 재생성은 아직 미완성이다.
- pikepdf object restore는 metadata/root entry/page annotation 중심이며 bookmark, form, 구조 태그 전체 복원은 아직 미완성이다.
- PaddleOCR은 optional dependency라 별도 설치가 필요하다.
- 현재 AlmaLinux WSL에서는 Poppler, Ghostscript, Java, sqlite3, Pango/Cairo Python binding, Noto Sans CJK font는 설치 완료. QPDF와 veraPDF는 별도 설치가 필요하다.

## 제외

- Adobe PDF Services
- Apryse
- 상용 SDK 전제 구조
- 원본 PDF 위에 whiteout box를 그리고 번역문을 덧씌우는 overlay 기본 구조
