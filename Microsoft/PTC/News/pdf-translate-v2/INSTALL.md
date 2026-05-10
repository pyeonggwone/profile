# INSTALL — pdf-translate-v2

WSL2 (Ubuntu 22.04 LTS) 또는 Linux 기준 설치 가이드. Windows native 는 지원하지 않는다.

## 1. 시스템 패키지

```bash
sudo apt update
sudo apt install -y build-essential pkg-config curl ca-certificates fonts-nanum
```

선택 (v1 의 JPX/JBIG2 feature 활성화 시):

```bash
sudo apt install -y libopenjp2-7-dev libjbig2dec0-dev
```

## 2. Rust toolchain

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
. "$HOME/.cargo/env"
rustup default stable
rustc --version    # 1.78+ 확인
```

## 3. Node.js 20+

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node --version     # v20+ 확인
```

## 4. 저장소 진입

```bash
cd profile/Microsoft/PTC/News/pdf-translate-v2
```

## 5. PDF 엔진 빌드 (`pdf-translate-v1` 의 `pdftr` CLI)

`pdf-translate-v2` 는 v1 의 `pdftr` 바이너리를 자식 프로세스로 호출한다. v1 디렉토리에서 release 빌드를 한 번 수행한다.

```bash
cd ../pdf-translate-v1
cargo build --release -p pdftr_cli
ls target/release/pdftr   # 또는 target/release/pdftr.exe (Windows)
cd ../pdf-translate-v2
```

빌드 산출물은 v1 의 `target/release/pdftr` 에 생성된다. v2 는 다음 순서로 바이너리를 찾는다.

1. `.env` 의 `PDF_ENGINE_BIN` 값
2. `pdf-engine/target/release/pdftr` (`pdf-engine/` 심볼릭 링크 또는 카피본을 둔 경우)
3. `../pdf-translate-v1/target/release/pdftr`
4. `$PATH` 의 `pdftr`

심볼릭 링크 권장 (옵션):

```bash
ln -s ../pdf-translate-v1/target pdf-engine/target
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

## 7. npm 의존성

```bash
npm install --no-audit --no-fund
```

`run-translate.sh` 가 `node_modules/` 부재 시 자동으로 `npm install` 을 실행하므로 이 단계는 생략 가능.

## 8. 한글 폰트 (`PDF_FONT_PATH`)

PDF Base14 폰트는 한글을 표현할 수 없으므로, 한글 출력에는 TrueType 임베딩이 필요하다.

```
PDF_FONT_PATH=/usr/share/fonts/truetype/nanum/NanumGothic.ttf
```

설정하지 않으면 v1 엔진의 Base14 fallback 으로 출력되어 한글이 깨질 수 있다.

## 9. 실행

```bash
chmod +x run-translate.sh
mkdir -p input output work input/done
./run-translate.sh
```

## 10. 검증

```bash
xdg-open output/<stem>_KR.pdf     # Linux
evince output/<stem>_KR.pdf       # GNOME 환경
```

## 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `pdftr` 바이너리를 찾을 수 없습니다 | v1 디렉토리에서 `cargo build --release -p pdftr_cli` 실행, 또는 `PDF_ENGINE_BIN` 명시 |
| 한글이 깨져 출력됨 | `PDF_FONT_PATH` 에 TrueType 폰트 경로 지정 |
| `OPENAI_API_KEY 가 필요합니다` | `.env` 의 키가 비어있음. 입력 후 재실행 |
| LLM 응답 `=== N === 블록 파싱 실패` | 모델 응답이 형식을 어김. `BATCH_SIZE` 를 줄이거나 다른 모델 시도 |
| `input/done` 으로 이동되지 않음 | `PDF_KEEP_INPUT=true` 가 설정됐거나 처리 실패. `work/<stem>/error.json` 확인 |
