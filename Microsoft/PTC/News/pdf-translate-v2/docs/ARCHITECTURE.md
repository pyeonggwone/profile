# Architecture — pdf-translate-v2

## 핵심 결정

| 항목 | 선택 | 이유 |
|---|---|---|
| PDF 처리 | **pdf-translate-v1 의 Rust workspace** (자식 프로세스) | 직접 구현 PDF 파서/Writer/Incremental Update. 외부 의존 0 (pure-Rust) |
| 운영 패턴 | input/output/work/done + glossary + .env | epub-translate-v5, ppt-translate-v4 와 동일 |
| 실행 환경 | **WSL/Linux + bash + Node.js 20+** | epub-translate-v5 와 동일하게 Linux first |
| LLM | OpenAI / Azure OpenAI (chat.completions) | epub-translate-v5 와 동일 분기 |
| TM | SQLite (`better-sqlite3`) | 동일 문장 재번역 방지, 전역 캐시 |
| 진입 | `./run-translate.sh` | epub-translate-v5 와 동일 패턴 |

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
pdf-translate-v2/
├── run-translate.sh
├── package.json
├── src/
│   ├── index.mjs               commander CLI 진입점
│   ├── pipeline.mjs            DETECT → EXTRACT → TRANSLATE → APPLY → DONE
│   ├── pdf/
│   │   ├── engine.mjs          v1 pdftr CLI 자식 프로세스 wrapper
│   │   └── edits.mjs           EditOperation JSON 직렬화 helper
│   ├── translate/
│   │   └── llm.mjs             OpenAI / Azure OpenAI batch
│   ├── glossary/
│   │   ├── loader.mjs          glossary.csv 파서
│   │   └── masker.mjs          placeholder 치환/복원
│   ├── tm/
│   │   └── store.mjs           SQLite TM (open/get/put/delete/reset/import)
│   └── util/
│       ├── env.mjs             .env 로드 + Config 빌드
│       ├── lang.mjs            언어 코드 정규화 (en/kr/ch/jp)
│       ├── log.mjs             타임스탬프 로거
│       └── paths.mjs           safeStem / outputPath / workSubdir
└── crates/                     (옵션 A 채택 시 v1 의 crate path 의존)
└── pdf-engine/                 (옵션 B 의 v1 pdftr CLI 로 가는 심볼릭 링크 권장)
```

## v1 엔진 사용 (옵션 B)

- v1 의 `cli_tools/src/main.rs` 가 노출하는 명령:
    - `pdftr inspect <pdf> --json`
    - `pdftr text <pdf> --json` → `Vec<PageText>` JSON
    - `pdftr edit <input> <output> --edits <edits.json>` → Incremental Update PDF
- `EditOperation` 의 serde 표현은 `{ "type": "AddText", "page", "x", "y", "text", "font", "size", "color" }`.
- v2 는 v1 디렉토리를 수정하지 않고, `target/release/pdftr` 바이너리만 자식 프로세스로 호출한다.

## 운영 모델 차이 흡수

| 영역 | v1 | v2 |
|---|---|---|
| 입력 | HTTP 업로드 | `input/` 디렉토리 + CLI |
| 출력 | HTTP 다운로드 | `output/<stem>_<TARGET>.pdf` |
| 처리 후 | 세션 디렉토리 | `input/done/` 자동 이동 |
| 언어 | 없음 | `--in-lang en --out-lang kr` |
| 용어집 | 없음 | `glossary.csv` |
| 캐시 | 세션 단위 격리 | 전역 `work/tm.sqlite` |
| LLM | 미연동 | OpenAI / Azure OpenAI |

## 폰트 처리 (제약)

- v1 의 `EditOperation::AddText` 는 Base14 폰트(`Helvetica/HelveticaBold/TimesRoman/Courier`)만 받는다.
- 한글 등 비-Latin 출력은 v1 의 `pdf_writer/font.rs` 의 TrueType subset 임베딩 API 가 CLI 표면에 노출되어야 가능하다.
- 현재 v2 는 `DEFAULT_FONT = Helvetica` 로 고정. 한글 PDF 는 깨질 수 있으며, 향후 v1 CLI 확장 또는 v2 에서 직접 incremental update 작성으로 해결 (TODO).
