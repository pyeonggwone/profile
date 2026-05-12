# install.md — pdf-translate-v5 설치 설계

이 문서는 `pdf-translate-v5` 를 구현할 때 필요한 실행 환경과 도구 설치 기준을 정리한다.

v5는 구현 난이도를 고려하지 않고, 기능별 최고 품질 도구를 연결하는 구조다. 따라서 단일 언어 런타임만으로 구성하지 않는다.

## 전제

- 기본 실행 환경은 WSL/Linux 기준이다.
- 최종 실행 진입점은 `run-v5.sh` 하나다.
- 내부 단계는 Python, Node.js, Java, native CLI를 함께 사용한다.
- 설치는 도구별로 분리하되, 실행은 shell script에서 통합한다.
- Adobe / Apryse 계열은 제외한다.

## 필수 런타임

| 런타임 | 용도 |
|---|---|
| Bash | 전체 파이프라인 실행 진입점 |
| Python 3.10+ | pikepdf, pdfplumber, OCR wrapper, 상태 처리 |
| Node.js 20+ | LLM translation, glossary masking, orchestration 보조 |
| Java 17+ | Apache PDFBox, veraPDF 실행 |
| C/C++ native libraries | PDFium, HarfBuzz, Pango, Cairo, QPDF, Poppler, Ghostscript |
| SQLite | Translation Memory, segment queue |

## 시스템 패키지

Ubuntu/WSL 기준 설치 후보:

```bash
sudo apt-get update
sudo apt-get install -y \
  bash \
  curl \
  git \
  jq \
  sqlite3 \
  python3 \
  python3-venv \
  python3-pip \
  nodejs \
  npm \
  openjdk-17-jre \
  qpdf \
  poppler-utils \
  ghostscript \
  libcairo2 \
  libcairo2-dev \
  libpango-1.0-0 \
  libpango1.0-dev \
  libharfbuzz0b \
  libharfbuzz-dev
```

## Python 패키지

Python은 venv를 사용한다.

```bash
./run-v5.sh bootstrap
```

`run-v5.sh bootstrap` 은 WSL에서 Windows mount(`/mnt/c`) 위에 venv를 만들 때 `lib`/`lib64` 설치 경로가 갈라지는 문제를 피하도록 `venv --copies` 와 `pip --target` 방식을 사용한다.

설치 후보:

```bash
python -m pip install \
  pikepdf \
  pdfplumber \
  reportlab \
  pycairo \
  PyGObject \
  pillow \
  numpy \
  opencv-python \
  paddleocr \
  pydantic \
  uharfbuzz
```

역할:

| 패키지 | 용도 |
|---|---|
| `pikepdf` | PDF object/resource/image/annotation/link/bookmark 보존 |
| `pdfplumber` | table 구조 인식 |
| `reportlab` | 새 PDF 문서 생성 |
| `pycairo` | vector drawing / shaped text drawing |
| `PyGObject` | Pango binding |
| `pillow` | image 처리 |
| `numpy`, `opencv-python` | render diff / image comparison |
| `paddleocr` | 로컬 OCR |
| `pydantic` | 상태 JSON schema 검증 |
| `uharfbuzz` | HarfBuzz glyph shaping Python binding |

## Node.js 패키지

Node는 LLM translation, glossary masking, TM orchestration 보조에 사용한다.

설치 후보:

```bash
npm install \
  commander \
  dotenv \
  csv-parse \
  better-sqlite3 \
  openai \
  zod
```

역할:

| 패키지 | 용도 |
|---|---|
| `commander` | CLI option parsing |
| `dotenv` | `.env` 로드 |
| `csv-parse` | glossary CSV 읽기 |
| `better-sqlite3` | TM/segment queue SQLite 처리 |
| `openai` | OpenAI/Azure OpenAI translation 호출 |
| `zod` | 상태 JSON validation |

## Java 도구

Java 도구는 jar 또는 CLI로 연결한다.

| 도구 | 용도 |
|---|---|
| Apache PDFBox | form / AcroForm 처리 |
| veraPDF | PDF/A 검증 |

설치 방식은 구현 단계에서 `tools/java/` 아래에 jar를 두거나 system package로 연결한다.

```text
tools/java/pdfbox-app.jar
tools/java/verapdf/
```

## PDFium

PDFium은 v5의 렌더링 기준과 text bbox 기준이다.

용도:

- page render
- text/glyph bbox extraction
- vector path extraction
- render diff baseline 생성

설치 방식 후보:

| 방식 | 설명 |
|---|---|
| system binary | PDFium CLI wrapper를 별도 설치 |
| Python binding | `pypdfium2` 사용 |
| custom wrapper | C++/Rust/Node wrapper 작성 |

초기 구현 후보는 Python에서 접근 가능한 `pypdfium2` 이다.

```bash
python -m pip install pypdfium2
```

## OCR 선택

v5는 로컬 OCR과 클라우드 OCR을 모두 설계에 포함한다.

| 모드 | 도구 | 설정 |
|---|---|---|
| local | PaddleOCR | GPU/CPU 선택 가능 |
| azure | Azure AI Vision | endpoint/key 필요 |

`.env` 예시:

```env
OCR_MODE=local
AZURE_VISION_ENDPOINT=
AZURE_VISION_KEY=
```

## 폰트

CJK 번역 품질을 위해 명시적 font set을 사용한다.

Windows/WSL 후보:

```text
/mnt/c/Windows/Fonts/malgun.ttf
/mnt/c/Windows/Fonts/malgunbd.ttf
```

Linux 후보:

```text
/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc
/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc
```

`.env` 예시:

```env
FONT_REGULAR=/mnt/c/Windows/Fonts/malgun.ttf
FONT_BOLD=/mnt/c/Windows/Fonts/malgunbd.ttf
FONT_FALLBACK=/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc
```

## 환경 변수

```env
SOURCE_LANG=en
TARGET_LANG=kr
OCR_MODE=local
WORK_DIR=work
INPUT_DIR=input
OUTPUT_DIR=output
GLOSSARY_PATH=glossary.csv
TM_DB_PATH=work/tm.sqlite
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=
FONT_REGULAR=/mnt/c/Windows/Fonts/malgun.ttf
FONT_BOLD=/mnt/c/Windows/Fonts/malgunbd.ttf
```

## 설치 검증

각 도구는 개별 health check를 둔다.

```bash
qpdf --version
pdffonts -v
gs --version
java -version
python -c "import pikepdf, pdfplumber, reportlab"
python -c "import pypdfium2"
node --version
sqlite3 --version
```

프로젝트 통합 검증:

```bash
./run-v5.sh doctor
./run-v5.sh input/source.pdf
```

OCR local mode 검증:

```bash
python -c "from paddleocr import PaddleOCR; print('paddleocr-ok')"
```

## 설치 완료 기준

설치가 완료되었다고 판단하는 기준:

- `run-v5.sh doctor` 가 모든 필수 도구를 검사한다.
- QPDF validation 가능
- PDFium render 가능
- pikepdf object open 가능
- pdfplumber table scan 가능
- LLM translation 호출 가능
- HarfBuzz shaping 가능
- Pango text layout 가능
- Cairo drawing 가능
- ReportLab PDF 생성 가능
- PDFium render diff 가능

## 비고

현재 v5는 `requirements.txt`, `package.json`, `run-v5.sh doctor`, `run-v5.sh bootstrap` 까지 구현되어 있다. 현재 AlmaLinux WSL 환경에는 Poppler, Ghostscript, Java, sqlite3가 설치되어 있다. QPDF와 veraPDF는 환경에 별도로 설치해야 한다.
