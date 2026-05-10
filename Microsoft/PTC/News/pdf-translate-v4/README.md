# pdf-translate-v4

`pdf-translate-v3` 의 overlay 한계를 분리해, 원본 PDF 위에 덮어쓰지 않고 새 PDF를 재구성하는 PDF 번역 프로젝트.

## 기준

- **자립**: v1, v2, v3 디렉토리에 의존하지 않는다. v4 한 폴더만 있으면 실행 가능.
- 운영 패턴: input/output/work/done + glossary + .env (epub-translate-v5, ppt-translate-v4 와 동일).
- 실행 환경: Linux/bash + Node.js 20+ + Python 3.10+ + PyMuPDF.
- PDF 처리: 기본값은 PyMuPDF rebuild (`PDF_ENGINE=pymupdf`, `PDF_BUILD_MODE=rebuild`). 원본 텍스트를 복사하지 않고 새 PDF를 생성한다.
- LLM 호출: OpenAI / Azure OpenAI 분기.
- 동일 문장은 SQLite 기반 Translation Memory (`work/tm.sqlite`) 로 한 번만 호출.
- 용어집(`glossary.csv`) 의 protected 항목은 placeholder 로 보호.

## 실행

```bash
chmod +x run-translate.sh
cp .env.example .env
vi .env
./run-translate.sh
```

`run-translate.sh` 가 다음을 자동 수행한다:
1. `.env` 부재 시 `.env.example` 복사
2. `node_modules` 부재 시 `npm install`
3. `PyMuPDF` 부재 시 `pip install -r requirements.txt`
4. `PDF_ENGINE=pdftr` 인 경우에만 `cargo build --release -p pdftr_cli`
5. `node src/index.mjs "$@"` 실행

자세한 설치 단계는 [INSTALL.md](INSTALL.md) 참조.

## 입력과 출력

```text
input/sample.pdf  -> output/sample_KR.pdf
input/done/sample.pdf  (성공 시 원본 자동 이동)
work/sample/segments.json   (EXTRACT 산출)
work/sample/translated.json (TRANSLATE 산출)
work/sample/edits.json      (APPLY 입력 — EditOperation 배열)
work/tm.sqlite              (Translation Memory)
```

## 디렉토리

```text
pdf-translate-v4/
├── requirements.txt        # PyMuPDF 의존성
├── Cargo.toml              # Rust workspace (fallback pdftr 엔진)
├── crates/
│   ├── pdf_core/           # primitives, ObjectId, ByteRange, error
│   ├── pdf_filters/        # Flate/ASCIIHex/ASCII85/RLE/LZW + Predictor + Crypt
│   ├── pdf_reader/         # header/xref/object/stream/page-tree
│   ├── pdf_writer/         # primitive serializer + xref/trailer + content + font
│   ├── pdf_incremental/    # append-only EditOperation -> PDF bytes
│   ├── pdf_analysis/       # text extract + summary + ToUnicode CMap
│   ├── pdf_render_plan/    # JSON render plan
│   └── cli_tools/          # `pdftr` CLI binary
├── target/                 # Rust 빌드 산출물 (gitignore)
│
├── package.json            # Node 20+ 진입점
├── src/
│   ├── index.mjs           # commander CLI
│   ├── pipeline.mjs        # DETECT → EXTRACT → TRANSLATE → APPLY → DONE
│   ├── pdf/
│   │   ├── engine.mjs      # PyMuPDF/pdftr 호출 wrapper
│   │   ├── pymupdf_engine.py # MuPDF/PyMuPDF 기반 extract/rebuild CLI
│   │   └── edits.mjs       # EditOperation JSON 직렬화
│   ├── translate/
│   │   └── llm.mjs         # OpenAI / Azure OpenAI batch
│   ├── glossary/
│   │   ├── loader.mjs
│   │   └── masker.mjs
│   ├── tm/
│   │   └── store.mjs       # SQLite Translation Memory
│   └── util/
│       ├── env.mjs
│       ├── lang.mjs
│       ├── log.mjs
│       └── paths.mjs
├── node_modules/           # npm 산출물 (gitignore)
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PIPELINE.md
│   ├── FILE-runtime-dirs.md
│   ├── FILE-env.md
│   ├── FILE-glossary-csv.md
│   └── FILE-pdf-engine.md
│
├── run-translate.sh        # 진입 스크립트 (자동 빌드 포함)
├── README.md
├── INSTALL.md
├── TODO.md
├── .env.example
├── glossary.csv
├── .gitignore
│
├── input/                  # 사용자 PDF
│   └── done/               # 처리 완료된 원본 자동 이동
├── output/                 # 번역된 PDF (<stem>_KR.pdf)
└── work/                   # 중간 산출물 + TM
    └── tm.sqlite
```

## CLI

```bash
./run-translate.sh                                # input/ 일괄 처리
./run-translate.sh --in-lang en --out-lang kr
./run-translate.sh --in-lang en --out-lang jp input/sample.pdf

./run-translate.sh extract input/sample.pdf
./run-translate.sh translate work/sample/segments.json --in-lang en --out-lang kr
./run-translate.sh apply input/sample.pdf work/sample/translated.json --out-lang kr

./run-translate.sh tm import legacy.csv
./run-translate.sh --reset-tm
```

언어 코드 표기는 `ppt-translate-v4` 와 동일: `en`, `kr`, `ch`, `jp` (대소문자 구분 없음).

## PDF 엔진 (PyMuPDF rebuild 기본)

v4 의 기본 엔진은 MuPDF/PyMuPDF rebuild 이다. 텍스트 bbox, font size, page geometry 를 PyMuPDF로 추출하고, 출력 단계에서는 원본 PDF를 수정하지 않는다. 새 PDF를 만든 뒤 원본의 이미지/벡터 도형을 다시 그리고 번역 텍스트만 `insert_textbox` 방식으로 삽입한다.

추출/적용 단계에서 다음 정보를 보존한다.

- 원본 bbox (`left/right/top/bottom`) 기반 텍스트 박스 배치
- 원본 텍스트 미복사: 출력 PDF에 원문 text object를 남기지 않음
- 원본 이미지와 vector drawing 재구성
- 원본 글자색과 배경색 샘플링
- bold/italic/serif/monospace font flags
- CJK 폰트 크기 보정 (`PDF_CJK_SIZE_RATIO`)
- 저장 전 font subsetting 으로 CJK 폰트 크기 폭증 완화

```env
PDF_ENGINE=pymupdf
PDF_BUILD_MODE=rebuild
PYTHON_BIN=python3
PDF_FONT_PATH=/usr/share/fonts/truetype/nanum/NanumGothic.ttf
PDF_FONT_BOLD_PATH=/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf
PDF_CJK_SIZE_RATIO=0.92
```

Windows venv에서 직접 실행할 때는 예를 들어:

```env
PYTHON_BIN=c:/Users/v-kimpy/test/.venv/Scripts/python.exe
PDF_FONT_PATH=C:/Windows/Fonts/malgun.ttf
```

Rust `pdftr` 엔진은 fallback 으로 유지한다. 사용할 경우:

```env
PDF_ENGINE=pdftr
```

첫 실행 시 `cargo build --release -p pdftr_cli` 가 자동으로 수행된다.

수동 빌드:

```bash
cargo build --release -p pdftr_cli
ls target/release/pdftr
```

`pdftr` fallback 이 노출하는 명령:

- `pdftr inspect <pdf> --json` : metadata + warnings
- `pdftr text <pdf> --json` : 페이지/런 단위 텍스트 추출
- `pdftr edit <input> <output> --edits <json>` : `EditOperation` 적용 → Incremental Update PDF
- `pdftr roundtrip <pdf>` : 무변경 검증

PyMuPDF rebuild 엔진은 결과 PDF를 clean/deflate 저장하고, 가능하면 embedded font 를 subset 한다. 포맷 유지 품질을 위해 bbox 기반 text box 삽입을 우선한다. (자세한 내용: [docs/FILE-pdf-engine.md](docs/FILE-pdf-engine.md))

## v1 / v2 와의 관계

| 프로젝트 | 역할 | 관계 |
|---|---|---|
| `pdf-translate-v1` | Rust PDF 엔진 (HTTP 서버 + frontend 포함) | v3 의 모태. v3 는 v1 의 8개 crate (server 제외) 를 자체 복사 보유 |
| `pdf-translate-v2` | Node 오케스트레이션 (v1 을 자식 프로세스 호출) | v3 의 모태. v3 는 v2 의 `src/`, `docs/`, 진입 스크립트를 자체 복사 보유 |
| `pdf-translate-v3` | overlay 방식 통합 | 원본 PDF 위에 whiteout + 번역 텍스트 덧그림 |
| `pdf-translate-v4` | **rebuild 방식 통합** | 새 PDF에 원본 비텍스트 요소와 번역 텍스트를 재구성 |

향후 rebuild 방식 변경은 v4 안에서만 한다. v1/v2/v3 는 historical 참조용.

## 제외 범위

- DRM / 암호 PDF 의 자동 우회 (지원 안 함)
- 웹 viewer (v1 의 server crate / frontend 는 v3 에서 제외; 필요 시 별도 프로젝트로 분리)
- AZW3/MOBI/KFX 등 비-PDF 포맷 (epub-translate-v5 영역)
- PowerPoint / 스프레드시트 (각각 ppt-translate-v* / docs-translate-v* 영역)
