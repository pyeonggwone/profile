# INSTALL — pdf-translate-v4

WSL2 (Ubuntu 22.04 LTS) / Linux 기준 설치 가이드.

## 1. 시스템 패키지

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y build-essential pkg-config curl ca-certificates python3 python3-pip fonts-nanum
```

### RHEL / Rocky / Fedora

```bash
sudo dnf install -y gcc gcc-c++ make pkg-config curl ca-certificates python3 python3-pip google-noto-sans-cjk-fonts
```

선택 (v1 의 JPX/JBIG2 feature 활성화 시):

```bash
# Ubuntu / Debian
sudo apt install -y libopenjp2-7-dev libjbig2dec0-dev
# RHEL 계열
sudo dnf install -y openjpeg2-devel jbig2dec-devel
```

## 2. Python / PyMuPDF

```bash
python3 --version
python3 -m pip install -r requirements.txt
python3 -c 'import fitz; print(fitz.VersionBind)'
```

## 3. Rust toolchain (PDF_ENGINE=pdftr fallback 사용 시)

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
. "$HOME/.cargo/env"
rustup default stable
rustc --version    # 1.78+ 확인
cargo --version
```

## 4. Node.js 20+

### Ubuntu / Debian

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node --version     # v20+ 확인
```

### RHEL 계열

```bash
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo -E bash -
sudo dnf install -y nodejs
```

## 5. 저장소 진입

```bash
cd profile/Microsoft/PTC/News/pdf-translate-v4
```

## 6. .env 작성

```bash
cp .env.example .env
vi .env
```

최소 필수:

```
OPENAI_API_KEY=sk-...
SOURCE_LANG=en
TARGET_LANG=kr
```

또는 Azure OpenAI:

```
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

## 7. PDF 엔진 / 한글 폰트

기본 PDF 엔진은 PyMuPDF 이다.

```
PDF_ENGINE=pymupdf
PDF_BUILD_MODE=rebuild
PYTHON_BIN=python3
```

한글 출력에는 TrueType/OpenType 폰트가 필요하다.

```
PDF_FONT_PATH=/usr/share/fonts/truetype/nanum/NanumGothic.ttf
```

Windows venv에서 실행할 때는 다음처럼 지정할 수 있다.

```
PYTHON_BIN=c:/Users/v-kimpy/test/.venv/Scripts/python.exe
PDF_FONT_PATH=C:/Windows/Fonts/malgun.ttf
```

## 8. 첫 실행

```bash
chmod +x run-translate.sh
./run-translate.sh
```

`run-translate.sh` 가 자동으로:
1. `.env` 가 없으면 `.env.example` 복사
2. `node_modules/` 가 없으면 `npm install --no-audit --no-fund`
3. PyMuPDF 가 없으면 `pip install -r requirements.txt`
4. `PDF_ENGINE=pdftr` 일 때만 `cargo build --release -p pdftr_cli`
5. `node src/index.mjs` 실행

기본 PyMuPDF 엔진은 Rust 빌드 없이 실행된다.

## 9. 검증

```bash
xdg-open output/<stem>_KR.pdf     # Linux
evince output/<stem>_KR.pdf       # GNOME 환경
```

## 10. 수동 빌드 (필요 시)

```bash
# Rust 만 빌드
cargo build --release -p pdftr_cli

# Python 의존성만 재설치
python3 -m pip install -r requirements.txt

# Node 의존성만 재설치
rm -rf node_modules package-lock.json
npm install --no-audit --no-fund
```

## 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `No module named 'fitz'` | `python3 -m pip install -r requirements.txt` 실행 |
| `cargo: command not found` | `PDF_ENGINE=pdftr` 사용 시 rustup 설치 후 `. "$HOME/.cargo/env"` 로 PATH 적용 |
| `linker 'cc' not found` | `gcc` / `build-essential` 설치 |
| `pdftr 바이너리를 찾을 수 없습니다` | `PDF_ENGINE=pdftr` 사용 중이면 `cargo build --release -p pdftr_cli` 수동 실행, 또는 `PDF_ENGINE_BIN` 명시 |
| 한글이 깨져 출력됨 | `PDF_FONT_PATH` 에 CJK 지원 TTF/OTF 지정 |
| `OPENAI_API_KEY 가 필요합니다` | `.env` 의 키가 비어있음 |
| LLM 응답 `=== N === 블록 파싱 실패` | `BATCH_SIZE` 를 줄이거나 다른 모델 시도 |
| `input/done` 으로 이동되지 않음 | `PDF_KEEP_INPUT=true` 또는 처리 실패. `work/<stem>/error.json` 확인 |
| WSL `/mnt/c` 실행 느림 | v4 디렉토리를 WSL 홈(`~/`) 으로 이동 후 실행 |
