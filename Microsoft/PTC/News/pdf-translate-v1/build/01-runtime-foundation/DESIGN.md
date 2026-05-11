# Runtime Foundation 설계

## 목적

PDF 핵심 엔진, 서버, 웹 프론트엔드, 빌드 환경의 기준 기술과 버전을 정의한다. 이 문서는 실제 구현 시 사용할 기술 스택을 고정하는 역할을 한다.

## 기준 기술 스택

| 영역 | 기술 | 기준 버전 | 선택 이유 |
|---|---|---:|---|
| PDF core engine | Rust | `1.78+` | 메모리 안전성, byte-level 처리, FFI 연동 용이 |
| 서버 | Rust `axum` | `0.7.x` | HTTP routing만 담당, PDF 로직 대체 아님 |
| Async runtime | `tokio` | `1.37+` | 업로드/다운로드 I/O 처리 |
| JSON | `serde`, `serde_json` | `1.0.x` | 요청/응답 직렬화 |
| Web frontend | TypeScript | `5.4+` | Canvas viewer/editor 타입 안정성 |
| Frontend build | Vite | `5.2+` | 단순 개발 서버와 번들링 |
| UI layer | React | `18.3.x` | 상태 기반 편집 UI 구성 |
| Canvas | Browser Canvas 2D API | Chromium/Edge 최신 stable 기준 | PDF 표시를 직접 렌더링 |
| Local DB | SQLite | `3.45+` | 작업 metadata, cache, session index 저장 |
| Compression | zlib (`flate2 + miniz_oxide` 또는 `zlib-ng`) | `1.3.1` | FlateDecode/FlateEncode 표준 처리 |
| JPEG decode metadata | `jpeg-decoder` | `0.3.x` | JPEG header/preview parse (pure Rust) |
| JPEG encode | `mozjpeg-sys` 또는 `libjpeg-turbo` FFI | `3.0.x` | DCT encode |
| JPEG2000 (선택) | `openjpeg-sys` | `2.5.x` | JPXDecode |
| JBIG2 (선택) | `jbig2dec-sys` | `0.20+` | JBIG2Decode |
| Crypto | `aes`, `sha2`, `md-5`, `rc4`, `cbc` (RustCrypto) | latest stable | AES/RC4/SHA/MD5 primitives |
| TrueType parse | `ttf-parser` | `0.21+` | OpenType parse |
| TrueType subset | `subsetter` | `0.2+` | 임베딩 subset |
| Font shaping | `rustybuzz` | `0.18+` | HarfBuzz pure-Rust |
| ICC color | `qcms` | `0.3+` | ICC profile 변환 |

버전은 설계 기준선이다. 실제 구현 시 같은 major 또는 LTS 계열의 최신 patch를 사용하되, 문서에는 빌드 시점의 확정 버전을 기록한다.

## Rust를 PDF core로 두는 이유

PDF 처리는 byte offset, stream 길이, object reference, cross-reference 위치를 정확히 다뤄야 한다. Rust는 다음 영역에서 유리하다.

- borrow checker로 원본 byte slice 참조 범위를 안전하게 관리한다.
- `Vec<u8>`, `&[u8]`, `Cow<[u8]>`로 원본 보존과 수정본 생성을 구분하기 쉽다.
- FFI로 `zlib`, `libjpeg-turbo`, `OpenJPEG`, `OpenSSL`에 연결할 수 있다.
- CLI, server library, test harness를 같은 core crate에서 공유할 수 있다.

## crate 구성 설계

실제 구현 시 workspace는 다음 crate로 나눈다.

| crate | 역할 |
|---|---|
| `pdf_core` | PDF primitive, object model, byte reader/writer |
| `pdf_reader` | header, xref, trailer, object, stream parser |
| `pdf_filters` | stream filter decode/encode adapter |
| `pdf_writer` | object serialization, xref/trailer writer |
| `pdf_incremental` | incremental update builder |
| `pdf_analysis` | text/image/metadata extraction |
| `pdf_render_plan` | content stream을 웹 렌더링 명령으로 변환 |
| `server` | upload/download API, session orchestration |
| `cli_tools` | roundtrip, inspect, diff, fixture 검증 도구 |

## 대체 구현체 연결 방식

대체 가능한 OSS 라이브러리는 PDF engine 내부의 adapter boundary 뒤에 둔다.

```text
PDF stream dictionary
-> FilterChain
-> FilterAdapter trait
-> zlib/libjpeg/OpenJPEG/OpenSSL FFI or pure Rust direct implementation
-> decoded bytes or preserved raw bytes
```

중요한 점은 외부 라이브러리가 PDF object, xref, content stream 의미를 알지 못하게 하는 것이다. 외부 구현체는 압축, 이미지, 암호 primitive만 수행한다.

## 빌드 원칙

- Windows 개발 환경을 1차 대상으로 한다.
- C/C++ OSS 라이브러리는 vcpkg 또는 source build 둘 중 하나를 선택한다.
- Rust crate는 `Cargo.lock`을 고정한다.
- Frontend는 `package-lock.json` 또는 `pnpm-lock.yaml`을 고정한다.
- PDF 호환성 fixture는 source tree에 작은 공개 샘플만 둔다.
- 큰 PDF fixture는 별도 artifact storage에 두고 checksum만 문서화한다.

## 금지되는 의존성

다음 의존성은 PDF 고유 로직을 대체하므로 사용하지 않는다.

- `pdf.js`
- `poppler`
- `qpdf`
- `mupdf`
- `iText`
- `PDFBox`
- `pypdf`
- `PyMuPDF`
- 클라우드 기반 PDF 변환/분석 API

## 완료 기준

- core PDF 처리는 Rust crate 내부에 있다.
- 웹 UI는 PDF parsing을 직접 수행하지 않고 서버가 제공하는 render plan 또는 page model을 사용한다.
- 모든 외부 OSS는 표준 primitive 처리로 제한된다.
- 버전과 라이선스는 구현 시 별도 `THIRD_PARTY.md`에 고정한다.