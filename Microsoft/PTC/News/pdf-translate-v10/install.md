# install

이 문서는 `pdf-translate-v10` 실행 환경을 준비하는 절차다.

## 전제 조건

```text
Python 3.11 이상
PowerShell
project-local qpdf
OpenAI API key 또는 Azure OpenAI 설정
```

v10은 PDF 처리를 Python package로 수행한다.

```text
pikepdf       PDF object/stream 접근과 저장
pdfplumber    page text/char/layout 추출
pdfminer.six  low-level layout 보조 추출
requests      OpenAI/Azure OpenAI 호출
```

## 1. 프로젝트 위치로 이동

workspace root 기준으로 이동한다.

```powershell
cd profile\Microsoft\PTC\News\pdf-translate-v10
```

## 2. Python 가상 환경 준비

프로젝트 안에 독립 `.venv`를 만들 수 있다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

이미 workspace 공용 `.venv`를 사용 중이면 해당 환경을 활성화한 뒤 다음 단계부터 진행한다.

## 3. package 설치

개발 모드로 설치한다.

```powershell
python -m pip install -e .
```

설치 후 CLI entry point가 등록된다.

```powershell
pdf-translate-v10 doctor
```

editable install 없이 실행하려면 `PYTHONPATH`를 지정한다.

```powershell
$env:PYTHONPATH = "src"
python -m pdf_translate_v10 doctor
```

## 4. 환경 변수 파일 준비

`.env.example`을 기준으로 `.env`를 만든다.

```powershell
Copy-Item .env.example .env
```

필수 또는 주요 값은 다음과 같다.

```dotenv
SOURCE_LANG=en
TARGET_LANG=ko
OPENAI_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
OPENAI_CHUNK_SIZE=100
TRANSLATION_PARALLELISM=0
OPENAI_API_KEY=
PDF_TRANSLATION_RENDER_MODE=text-compose
FONT_REGULAR=fonts/malgun.ttf
FONT_FALLBACK=fonts/NotoSansCJK-Regular.ttc
```

text-compose 모드에서 한국어가 보이려면 `FONT_REGULAR`, `FONT_FALLBACK`, `FONT_BOLD` 중 하나가 실제 font 파일을 가리켜야 한다. v10 `fonts` 폴더에 없으면 같은 상위 폴더의 v9 `fonts` 폴더도 자동으로 탐색한다.

Azure OpenAI를 사용할 경우 다음 값을 설정한다.

```dotenv
OPENAI_PROVIDER=azure
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=
```

OS 환경변수에 같은 값이 있으면 OS 환경변수가 `.env`보다 우선한다.

## 5. qpdf 배치

v10은 qpdf를 project-local tool로만 탐색한다. 전역 `PATH`의 qpdf는 사용하지 않는다.

Windows 실행 파일은 다음 위치에 둔다.

```text
tools/qpdf/bin/qpdf.exe
```

Linux 또는 WSL 실행 파일은 다음 위치에 둔다.

```text
tools/qpdf/bin/qpdf
```

탐색 순서는 다음과 같다.

```text
QPDF_BIN
tools/qpdf/bin/qpdf
tools/qpdf/qpdf
tools/qpdf/bin/qpdf.exe
tools/qpdf/qpdf.exe
tools/bin/qpdf
tools/bin/qpdf.exe
```

`QPDF_BIN`이 상대 경로이면 v10 root 기준으로 해석한다.

## 6. 설치 확인

다음 명령으로 설정 상태를 확인한다.

```powershell
python -m pdf_translate_v10 doctor
```

정상 상태에서는 `qpdfOk`, `glossaryOk`, directory path를 확인할 수 있다.

qpdf를 아직 배치하지 않았다면 다음 issue가 출력되는 것이 정상이다.

```text
project-local qpdf not found
```

## 7. 입력 PDF 배치

기본 batch는 `input` 바로 아래 PDF를 처리한다.

```text
input/sample.pdf
```

ready queue를 사용하려면 `input/ready` 아래에 둔다.

```text
input/ready/sample.pdf
```

## 8. 기본 실행

```powershell
python -m pdf_translate_v10 run
```

특정 파일만 실행하려면 다음처럼 지정한다.

```powershell
python -m pdf_translate_v10 run .\input\sample.pdf
```

## 설치 후 산출물 위치

```text
work/jobs/<job>/state/*.json
work/jobs/<job>/reports/*.json
work/jobs/<job>/pdf/rebuilt.pdf
output/validated/*.pdf
output/rejected/*.pdf
output/reports/<job>/*.json
```

검증 통과 PDF만 `output/validated`에 publish된다. degraded, fallback, failed 결과는 `output/rejected`에 publish된다.