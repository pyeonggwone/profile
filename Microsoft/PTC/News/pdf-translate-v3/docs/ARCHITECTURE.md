# Architecture — pdf-translate-v3

## 핵심 결정

| 항목 | 선택 | 이유 |
|---|---|---|
| PDF 처리 | **자체 빌드한 Rust workspace** (`cargo build` → `target/release/pdftr` → 자식 프로세스 호출) | v1, v2 디렉토리에 의존하지 않는 자립형 구조 |
| 운영 패턴 | input/output/work/done + glossary + .env | epub-translate-v5, ppt-translate-v4 와 동일 |
| 실행 환경 | **WSL/Linux + bash + Node.js 20+ + Rust 1.78+** | epub-translate-v5 와 동일하게 Linux first |
| LLM | OpenAI / Azure OpenAI (chat.completions) | epub-translate-v5 와 동일 분기 |
| TM | SQLite (`better-sqlite3`) | 동일 문장 재번역 방지, 전역 캐시 |
| 진입 | `./run-translate.sh` | 자동 빌드 + 자동 npm install + node 실행 |

## 파이프라인

```
input/foo.pdf
  │
  ▼  EXTRACT  (pdftr text foo.pdf --json)
work/foo/segments.json      [{ id, page, runIndex, x, y, fontSize, text }]
  │
  ▼  TRANSLATE  (TM 조회 → 미스만 LLM 배치 → SQLite 저장 → glossary placeholder)
work/foo/translated.json    ←→  work/tm.sqlite
  │
  ▼  APPLY  (translated.segments → EditOperation::AddText[] → pdftr edit foo.pdf out.pdf --edits edits.json)
output/foo_KR.pdf           (incremental update; 원본 byte prefix 무손실 보존)
  │
  ▼  DONE
input/done/foo.pdf
```

## 컴포넌트

```
pdf-translate-v3/
│
├── Cargo.toml                workspace (8 members)
├── crates/
│   ├── pdf_core/             primitives, ObjectId, ByteRange, error
│   ├── pdf_filters/          Flate/ASCIIHex/ASCII85/RLE/LZW + Predictor + Crypt
│   ├── pdf_reader/           header/xref/object/stream/page-tree
│   ├── pdf_writer/           primitive serializer + xref/trailer + content + font
│   ├── pdf_incremental/      append-only EditOperation -> PDF bytes
│   ├── pdf_analysis/         text extract + summary + ToUnicode CMap
│   ├── pdf_render_plan/      JSON render plan
│   └── cli_tools/            pdftr CLI binary
│
├── package.json              Node 진입점
├── src/
│   ├── index.mjs             commander CLI
│   ├── pipeline.mjs          DETECT → EXTRACT → TRANSLATE → APPLY → DONE
│   ├── pdf/
│   │   ├── engine.mjs        target/release/pdftr 자식 프로세스 wrapper
│   │   └── edits.mjs         EditOperation JSON 직렬화
│   ├── translate/
│   │   └── llm.mjs           OpenAI / Azure OpenAI batch
│   ├── glossary/
│   │   ├── loader.mjs
│   │   └── masker.mjs
│   ├── tm/
│   │   └── store.mjs         SQLite TM
│   └── util/
│       ├── env.mjs
│       ├── lang.mjs
│       ├── log.mjs
│       └── paths.mjs
│
└── run-translate.sh          자동 빌드 + 자동 install + node 실행
```

## v1, v2 와의 분리

- `pdf-translate-v1` : 원본 Rust 엔진 + HTTP server + frontend. v3 는 8 crate (server 제외) 만 자체 복사.
- `pdf-translate-v2` : 옵션 B (v1 자식 프로세스 호출) 의 Node 오케스트레이션. v3 가 src/ 와 docs/ 를 자체 복사하면서 v2 자체 의존도 제거.
- v3 는 v1, v2 디렉토리 부재 시에도 단독으로 동작한다.

## v3 의 빌드 흐름

```
./run-translate.sh
  │
  ▼ .env 없음? → cp .env.example .env
  ▼ node_modules 없음? → npm install
  ▼ target/release/pdftr 없음? → cargo build --release -p pdftr_cli
  ▼ exec node src/index.mjs "$@"
        │
        ▼ src/pdf/engine.mjs::resolvePdfEngineBin()
              → target/release/pdftr (또는 .env 의 PDF_ENGINE_BIN)
        │
        ▼ pipeline.processFile()
              → pdftr text → segments.json
              → LLM batch → translated.json
              → pdftr edit → output/*_KR.pdf
              → input/done/*.pdf
```

## 폰트 처리 (제약)

- v1 의 `EditOperation::AddText` 는 Base14 폰트(`Helvetica/HelveticaBold/TimesRoman/Courier`)만 받는다.
- 한글 등 비-Latin 출력은 깨진다.
- v1 의 `pdf_writer/font.rs` 에 TrueType subset 임베딩이 구현되어 있으나 CLI 표면(`pdftr edit`) 에는 미노출.
- 해결은 v3 의 `crates/cli_tools` + `crates/pdf_incremental` 에 옵션 추가로 가능 (TODO).
