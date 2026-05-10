# PDF 텍스트 기능 지원 많은 순 정리

기준: `pdf_project_text2.md`의 `지원 합계`를 중심으로 정렬했다. 유료 상용 SDK 성격의 후보는 제외했다. `지원 합계`는 `지원 + 부분`이며, 공식 API로 직접 제공하는 기능과 직접 구현 여지가 있는 기능을 함께 본 값이다.

## 라이브러리별 지원 많은 순

| 순위 | 라이브러리 | 지원 합계 | 지원 | 부분 | 미지원 | 해석 |
|---:|---|---:|---:|---:|---:|---|
| 1 | PyMuPDF | 30 | 17 | 13 | 2 | Python에서 가장 넓게 쓰기 좋다. 텍스트, 좌표, span, JSON 추출 균형이 좋다. |
| 2 | Apache PDFBox | 29 | 20 | 9 | 3 | `지원` 항목 수가 가장 많다. Java 기반 저수준 분석과 text state 접근에 강하다. |
| 3 | MuPDF | 28 | 14 | 14 | 4 | CLI와 structured text 기반 추출이 강하다. 원본 text state 전체 재현보다는 추출 중심이다. |
| 3 | pdfplumber | 28 | 11 | 17 | 4 | Python에서 글자/표/좌표 분석에 실용적이다. 고급 PDF 내부 상태는 직접 구현이 필요하다. |
| 5 | pdfminer.six | 23 | 6 | 17 | 9 | Python 순수 텍스트/layout 분석 기반으로 쓸 수 있다. 스타일/렌더링 상태 지원은 제한적이다. |
| 6 | pikepdf | 15 | 4 | 11 | 17 | PDF object와 content stream 조작에 유리하다. 텍스트 의미 분석 기능은 직접 구현해야 한다. |
| 7 | QPDF | 13 | 3 | 10 | 19 | 구조 분석, stream decode, object 조작에 적합하다. 텍스트 추출 엔진으로 보기는 어렵다. |
| 8 | PDFium/Pdfium.Net | 11 | 7 | 4 | 21 | 렌더링/기본 텍스트 추출 계열에 가깝다. 고급 텍스트 상태 분석은 약하다. |
| 9 | PyMuPDF OCR/Tesseract | 9 | 3 | 6 | 23 | 원본 PDF 텍스트가 없는 경우의 OCR 보완 축이다. 원본 font/state 분석 용도는 아니다. |

## 지원 많은 그룹별 선택 축

| 그룹 | 대상 | 지원 합계 범위 | 우선 검토 상황 |
|---|---|---:|---|
| 최상위 | PyMuPDF | 30 | Python 기반에서 기능 누락을 최소화해야 하고, 텍스트/좌표/스타일/구조를 폭넓게 다뤄야 할 때 |
| 상위 | Apache PDFBox, MuPDF, pdfplumber | 28~29 | 특정 언어/운영 환경에 맞춰 강한 후보를 고를 때 |
| 중간 | pdfminer.six | 23 | Python 기반 텍스트 및 layout 분석이 주목적이고, 렌더링 상태까지 깊게 보지 않을 때 |
| 하위 | pikepdf, QPDF, PDFium/Pdfium.Net, PyMuPDF OCR/Tesseract | 9~15 | 텍스트 추출 주력보다는 PDF 구조 조작, 렌더링, OCR 보완처럼 역할이 분명할 때 |

## 목적별 우선 후보

| 목적 | 1차 후보 | 보조 후보 | 이유 |
|---|---|---|---|
| 가장 넓은 기능 커버리지 | PyMuPDF | Apache PDFBox, MuPDF, pdfplumber | 제외 대상 제거 후 `지원 합계`가 가장 높고 미지원 항목이 적다. |
| Python 기반 구현 | PyMuPDF | pdfplumber, pdfminer.six, pikepdf | PyMuPDF가 전체 지원이 가장 넓고, pdfplumber는 좌표/문자 분석 보조에 좋다. |
| Java 기반 저수준 분석 | Apache PDFBox | MuPDF | `지원` 항목 수가 가장 많고 text matrix, graphics state, font 처리에 강하다. |
| PDF object/content stream 조작 | pikepdf, QPDF | Apache PDFBox | 텍스트 의미 추출보다는 object, stream, resource 접근 축에서 유리하다. |
| 글자 위치/좌표 중심 추출 | PyMuPDF, pdfplumber | Apache PDFBox, MuPDF | char bbox, span, matrix, structured text 계열 결과를 얻기 쉽다. |
| OCR 보완 | PyMuPDF OCR/Tesseract | PyMuPDF | 원본 text layer가 없거나 스캔 PDF일 때 보완용으로 적합하다. |

## 요약 판단

| 결론 | 후보 |
|---|---|
| 전체적으로 가장 많은 기능을 지원하는 축 | PyMuPDF |
| 오픈소스 중심에서 가장 균형 좋은 축 | PyMuPDF, Apache PDFBox, MuPDF, pdfplumber |
| Python 프로젝트에서 현실적인 1순위 | PyMuPDF |
| PDF 내부 구조 조작 중심의 보조축 | pikepdf, QPDF |
| 스캔/OCR 보완축 | PyMuPDF OCR/Tesseract |
