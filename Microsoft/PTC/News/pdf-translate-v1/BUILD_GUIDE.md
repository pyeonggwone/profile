# pdf-translate-v1 빌드 및 실행 가이드

이 문서는 `build/` 디렉토리의 설계를 따라 작성된 실제 코드 베이스를 빌드하고 실행하는 방법을 정리한다.

## 사전 요구

| 도구 | 기준 버전 | 설치 |
|---|---|---|
| Rust | `1.78+` | https://rustup.rs |
| Node.js | `20.10+` | https://nodejs.org |
| npm 또는 pnpm | 최신 stable | Node와 함께 설치됨 |

본 워크스페이스(`c:\Users\v-kimpy\test`)에는 위 두 도구가 설치되어 있지 않아 자동 빌드를 수행하지 않았다. 사용자가 두 도구를 설치한 뒤 아래 절차로 빌드한다.

## Rust 워크스페이스 빌드

```powershell
cd profile\Microsoft\PTC\News\pdf-translate-v1
cargo build
cargo test
```

처음 빌드 시 `flate2` (Pure-Rust `miniz_oxide` 백엔드), `axum`, `tokio` 등이 다운로드된다. C 컴파일러나 system zlib 의존이 없다.

설계 문서가 명시한 외부 라이브러리(`zlib 1.3.1`, `libjpeg-turbo`, `OpenJPEG`, `OpenSSL`)는 향후 단계에서 FFI로 연결할 수 있도록 `pdf_filters::flate` 모듈에 어댑터 경계가 분리돼 있다. Production 빌드 시 `flate2 = { features = ["zlib-ng"] }` 식으로 시스템 zlib에 연결할 수 있다.

## CLI

```powershell
cargo run -p pdftr_cli -- inspect path\to\sample.pdf
cargo run -p pdftr_cli -- text path\to\sample.pdf
cargo run -p pdftr_cli -- render-plan path\to\sample.pdf 1
cargo run -p pdftr_cli -- roundtrip path\to\sample.pdf
cargo run -p pdftr_cli -- edit input.pdf output.pdf --edits edits.json
```

`edits.json` 예시:

```json
[
  {
    "type": "AddText",
    "page": 1,
    "x": 72,
    "y": 72,
    "text": "Hello incremental!",
    "font": "Helvetica",
    "size": 14,
    "color": [0.1, 0.1, 0.1]
  },
  {
    "type": "AddTextAnnotation",
    "page": 1,
    "x": 320,
    "y": 96,
    "contents": "주석입니다."
  }
]
```

## 서버 실행

```powershell
cargo run -p pdftr_server
```

기본값:
- 주소: `127.0.0.1:7878`
- 작업 디렉토리: `./workdir`
- 업로드 한도: 100 MiB

환경 변수:
- `PDFTR_ADDR`: 바인딩 주소
- `PDFTR_WORKDIR`: 세션 데이터 경로

API 엔드포인트(설계 `02-web-boundary` 참조):

| Method | Path | 역할 |
|---|---|---|
| `GET` | `/api/health` | health check |
| `POST` | `/api/documents` | multipart 업로드 |
| `GET` | `/api/documents/:id` | 문서 metadata + summary |
| `DELETE` | `/api/documents/:id` | 세션 정리 |
| `GET` | `/api/documents/:id/pages/:page` | render plan |
| `POST` | `/api/documents/:id/edits` | edit operation 추가 |
| `GET` | `/api/documents/:id/download` | Incremental Update PDF 다운로드 |

## Frontend 실행

```powershell
cd frontend
npm install
npm run dev
```

기본 주소: http://localhost:5173 (vite dev server)
백엔드 API는 `/api` 경로로 프록시된다.

## 디렉토리 맵

```
pdf-translate-v1/
├── Cargo.toml                       # workspace
├── BUILD_GUIDE.md                   # this file
├── README.md                        # 개념 설명 (입력 문서)
├── build/                           # 설계 문서 (DESIGN.md per area)
├── crates/
│   ├── pdf_core/                    # primitives, ObjectId, ByteRange, error
│   ├── pdf_filters/                 # FlateDecode/ASCIIHex/ASCII85/RLE/LZW + Predictor
│   ├── pdf_reader/                  # header/startxref/xref/object/stream/page-tree
│   ├── pdf_writer/                  # primitive serializer + xref/trailer + content builder
│   ├── pdf_incremental/             # append-only EditOperation -> PDF bytes
│   ├── pdf_analysis/                # text extract + summary
│   ├── pdf_render_plan/             # JSON render plan for Canvas viewer
│   ├── server/                      # axum API (PDFTR_SERVER)
│   └── cli_tools/                   # `pdftr` CLI binary
├── frontend/                        # React + TS + Vite
└── fixtures/                        # 호환성 테스트 fixture (커밋 가능한 작은 샘플만)
```

## Phase 매핑

설계의 `11-delivery-roadmap`에 정의된 phase가 어느 crate에서 다뤄지는지:

| Phase | 위치 |
|---|---|
| 1. 양방향 뼈대 | `crates/server` |
| 2. PDF Reader MVP | `crates/pdf_reader` |
| 3. Stream Filter MVP | `crates/pdf_filters` |
| 4. Text Analysis MVP | `crates/pdf_analysis`, `crates/pdf_render_plan` |
| 5. PDF Writer MVP | `crates/pdf_writer` |
| 6. Incremental Update MVP | `crates/pdf_incremental` |
| 7. Web Editor MVP | `frontend/` |
| 8a. Crypt (RC4 + AES-128) | `crates/pdf_filters/src/crypt.rs` + `pdf_reader::ParsedPdf::from_bytes_with_password` |
| 8b. DCT JPEG + Image XObject + AddImage | `crates/pdf_filters/src/dct.rs`, `crates/pdf_writer/src/image.rs`, `EditOperation::AddImageJpeg` |
| 8c. TrueType subset embedding | `crates/pdf_writer/src/font.rs` (`ttf-parser` + `subsetter`) |
| 9a. ToUnicode CMap | `crates/pdf_analysis/src/cmap.rs` |
| 9b. JPXDecode (feature) | `crates/pdf_filters/src/jpx.rs` (`jpx-openjpeg` feature) |
| 9c. CCITTFaxDecode | `crates/pdf_filters/src/ccitt.rs` (`fax` crate) |
| 9d. JBIG2Decode (feature) | `crates/pdf_filters/src/jbig2.rs` (`jbig2-jbig2dec` feature) |
| 9e. Font shaping | `crates/pdf_analysis/src/shaping.rs` (`rustybuzz`) |
| 9f. ICC color management | `crates/pdf_analysis/src/color.rs` (`qcms`) |
| 10. 안정화 | `crates/cli_tools::roundtrip` 명령 |

## 미구현 / 향후

- `JPXDecode`, `JBIG2Decode` 어댑터는 feature flag (`jpx-openjpeg`, `jbig2-jbig2dec`) 뒤에 stub 으로 분리되어 있다. 실제 디코드를 활성화하려면 시스템에 OpenJPEG / jbig2dec 를 설치하고 `openjpeg-sys` / `jbig2dec-sys` 와이어링을 추가한다.
- `mozjpeg-encode` feature 로 새 JPEG 인코딩 어댑터를 활성화할 수 있다 (현재는 stub).
- 암호화 PDF **저장**은 명시 오류 (`PDF_ENCRYPTED_WRITE`). 읽기/복호화 + incremental update 는 R≤4 (RC4 + AES-128) 까지 지원한다. R=6 (AES-256) 는 미구현.
- 단순 폰트 메트릭 ("Adobe Standard Encoding" 등) 은 일부만 폴백.

이 영역들은 모두 `build/` 설계 문서에 명시된 단계별 도입 대상이며 각 crate의 어댑터 경계가 마련되어 있다.
