# pdf-translate-v1 Build 설계 구조

이 디렉토리는 `README.md`의 요구사항을 구현 전 설계 문서로 분해한 공간이다. 실제 소스 구현은 포함하지 않는다.

## 전체 원칙

- PDF 읽기와 PDF 쓰기를 모두 직접 제어한다.
- PDF 고유 로직은 직접 구현한다.
- 대체 가능한 부분은 표준이며 소스 공개된 구현체만 사용한다.
- 블랙박스 SaaS, 상용 PDF SDK, 외부 PDF API, `pdf.js`, `poppler`, `qpdf`, `iText`, `PDFBox` 같은 PDF 엔진 대체는 사용하지 않는다.
- 원본 PDF를 보존하고 변경분만 추가하는 `Incremental Update`를 기본 저장 방식으로 둔다.

## 설계 디렉토리

| 디렉토리 | 역할 |
|---|---|
| `00-requirements` | README 요구사항과 금지/허용 범위 정리 |
| `01-runtime-foundation` | 언어, 런타임, 표준 라이브러리, 대체 가능 OSS 버전 기준 |
| `02-web-boundary` | 업로드, 다운로드, API, 파일 처리 경계 설계 |
| `03-pdf-reader` | PDF 파서, xref, trailer, object, stream 읽기 설계 |
| `04-stream-filters` | Flate, JPEG, JPX, LZW, RLE, ASCII85, Hex, CCITT, JBIG2 처리 설계 |
| `05-document-model` | 원본 객체 보존, 내부 문서 모델, 변경 추적 설계 |
| `06-pdf-writer` | 객체 직렬화, stream 인코드, xref/trailer 생성 설계 |
| `07-incremental-update` | 원본 무손실 저장과 변경분 append 전략 |
| `08-analysis-extraction` | 텍스트, 이미지, 메타데이터, 폰트, 주석 분석 설계 |
| `09-web-viewer-editor` | Canvas 렌더링, 웹 편집 UI, 다운로드 연동 설계 |
| `10-compatibility-testing` | 라운드트립, 호환성, 회귀 테스트 설계 |
| `11-delivery-roadmap` | 단계별 구현 순서와 완료 기준 |

각 디렉토리의 `DESIGN.md`에 상세 구현 방식, 사용 기술, 기준 버전, 주요 로직을 작성한다.
