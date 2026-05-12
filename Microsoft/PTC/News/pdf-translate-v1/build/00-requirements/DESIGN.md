# 요구사항 정리

## 목적

`README.md`의 핵심 요구사항을 구현 가능한 설계 조건으로 정리한다. 이 문서는 이후 모든 디렉토리 설계의 기준 문서다.

## 핵심 요구사항

### 1. 대체 가능하지만 수정 가능해야 함

외부 구현체를 사용할 수 있는 범위는 제한한다. 사용할 수 있는 것은 다음 조건을 모두 만족해야 한다.

- 표준 기반 구현체다.
- 소스가 공개되어 있다.
- 필요하면 직접 빌드하거나 수정할 수 있다.
- PDF 고유 로직을 대신 수행하지 않는다.

허용 예시는 다음과 같다. (PDF 엔진이 아닌 "PDF가 참조하는 기반 표준 라이브러리".)

| 영역 | 기준 구현체 | 기준 버전 | 사용 이유 |
|---|---:|---:|---|
| Flate 압축 | `zlib` 또는 `miniz_oxide`(pure Rust) | `1.3.1` / `0.7.x` | RFC 1950/1951 기반 표준 구현체 |
| JPEG DCT (decode metadata) | `jpeg-decoder`(pure Rust) | `0.3.x` | JPEG metadata/preview |
| JPEG DCT (encode) | `mozjpeg-sys` 또는 `libjpeg-turbo` FFI | `3.0.x` | 새 이미지 인코딩 |
| JPEG2000 JPX | `openjpeg-sys` (선택 feature) | `2.5.x` | ISO/IEC 15444 |
| JBIG2 | `jbig2dec-sys` (선택 feature) | `0.20+` | ISO/IEC 14492 |
| AES/SHA/MD5/RC4 | `aes`, `sha2`, `md-5`, `rc4` (pure Rust crypto crates) | RustCrypto 최신 stable | NIST primitives, FIPS 호환 알고리즘 |
| TrueType parse | `ttf-parser` (pure Rust) | `0.21+` | OpenType cmap/glyph metrics |
| TrueType subset | `subsetter` (pure Rust, by Typst) | `0.2+` | 폰트 임베딩 크기 최소화 |
| 폰트 shaping | `rustybuzz` (HarfBuzz pure-Rust port) | `0.18+` | 복잡 스크립트 shaping |
| ICC color | `qcms` (pure Rust, Servo) | `0.3+` | ICC profile 색역 변환 |
| 로컬 색인/작업 DB | `SQLite` | `3.45+` | 소스 공개 임베디드 DB |
| HTTP 서버 | Rust 표준 네트워크 + `axum` | `Rust 1.78+`, `axum 0.7` | 네트워크/HTTP 처리만 담당 |

위 라이브러리는 모두 다음 기준을 만족한다.

- 소스가 공개되어 있다.
- PDF 고유 로직(객체, xref, trailer, content stream, incremental update)을 대신하지 않는다.
- PDF가 참조하는 비-PDF 표준(JPEG, JPEG2000, JBIG2, AES, OpenType, ICC)의 정의에 따라 데이터만 다룬다.

금지 예시는 다음과 같다.

- Adobe PDF Library
- 클라우드 PDF 변환 API
- `pdf.js` 렌더링 엔진 대체 사용
- `poppler`, `qpdf`, `iText`, `PDFBox` 등 PDF 파서/생성기 대체 사용
- 소스 수정이 불가능한 상용 SDK

### 2. 업로드와 다운로드 양방향 지원

방향 A는 업로드 흐름이다.

```text
사용자 PDF 업로드 -> 서버 PDF 분석 -> 웹 표시
```

방향 B는 다운로드 흐름이다.

```text
웹 편집/생성 -> 서버 PDF 생성 -> 사용자 다운로드
```

따라서 서버에는 반드시 PDF 읽기 엔진과 PDF 쓰기 엔진이 모두 필요하다.

## 직접 구현해야 하는 영역

PDF 고유 문법과 호환성에 영향을 주는 영역은 직접 구현한다.

| 영역 | 직접 구현 이유 |
|---|---|
| PDF header/version 파싱 | PDF 파일 구조의 시작점 |
| `startxref`, `xref`, `trailer` 파싱 | 객체 주소와 문서 루트 해석의 핵심 |
| indirect object 파싱 | 모든 PDF 구성 요소의 기본 단위 |
| stream dictionary 처리 | filter, length, decode params 제어 필요 |
| content stream operator 해석 | 렌더링과 텍스트 추출의 핵심 |
| ToUnicode CMap 해석 | 텍스트 추출 품질의 핵심 |
| 객체 직렬화 | 쓰기 엔진의 핵심 |
| xref/trailer 작성 | PDF 저장 호환성의 핵심 |
| Incremental Update | 원본 무손실 보존의 핵심 |
| Canvas 렌더링 adapter | 웹 표시를 직접 제어하기 위해 필요 |

## 호환성 원칙

PDF는 모르는 구조가 나와도 전체 파일을 망가뜨리면 안 된다. 기본 원칙은 다음과 같다.

- 모르는 객체 타입은 파싱 가능한 최소 metadata만 기록하고 원본 byte range를 보존한다.
- 모르는 filter는 디코딩하지 않고 stream 원본을 보존한다.
- 편집하지 않은 객체는 재직렬화하지 않는다.
- 저장은 기본적으로 Incremental Update를 사용한다.
- 암호화, linearized PDF, object stream, xref stream은 별도 기능으로 인식하되 초기 구현에서 실패 방식을 명확히 둔다.

## 범위 밖

초기 설계에서 다음은 구현 대상이지만, 첫 단계의 필수 완료 조건은 아니다.

- 모든 폰트 shaping 완전 지원
- JBIG2 전체 디코더 완성
- PDF 2.0 전체 feature coverage
- 복잡한 투명도 그룹과 blend mode의 픽셀 완전 일치
- XFA form 완전 처리

## 완료 기준

- 구현 전 모든 핵심 영역이 독립 디렉토리 설계 문서로 나뉘어 있어야 한다.
- 각 문서는 사용 기술, 기준 버전, 직접 구현/대체 구현 구분, 주요 로직을 포함해야 한다.
- 전체 구조는 `build/BUILD.md`만 보고도 파악 가능해야 한다.