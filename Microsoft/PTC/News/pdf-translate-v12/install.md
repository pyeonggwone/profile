# install

## WSL 기준 설치

```bash
cd /mnt/c/Users/v-kimpy/test/profile/Microsoft/PTC/News/pdf-translate-v12
./run-v12.sh bootstrap
```

`bootstrap`은 Python 가상환경을 만들고 `requirements.txt`를 설치한다. Node/npm은 사용하지 않는다.

WSL에서 프로젝트가 `/mnt/c` 아래에 있으면 기본 venv 위치는 Linux 파일시스템의 `~/.cache/pdf-translate-v12/.venv`다. Windows 파일시스템 위 venv는 pip 설치 중 dist-info 파일 생성 오류가 날 수 있어서 기본으로 사용하지 않는다.

## 수동 설치

```bash
cd /mnt/c/Users/v-kimpy/test/profile/Microsoft/PTC/News/pdf-translate-v12
python3 -m venv --copies .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

WSL에서 수동 설치할 때는 아래처럼 Linux 홈 아래 venv를 권장한다.

```bash
cd /mnt/c/Users/v-kimpy/test/profile/Microsoft/PTC/News/pdf-translate-v12
python3 -m venv --copies ~/.cache/pdf-translate-v12/.venv
source ~/.cache/pdf-translate-v12/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 선택 도구

품질 검증과 최적화를 위해 있으면 좋은 외부 도구:

- `qpdf`
- `pdffonts` 또는 Poppler
- `gs` 또는 Ghostscript
- `sqlite3`

없어도 `ALLOW_DEGRADED=true`이면 가능한 단계는 degraded 상태로 진행한다.

## 설정

```bash
cp .env.example .env
```

OpenAI 번역을 사용할 때만 `.env`의 `TRANSLATION_MODE`, `OPENAI_API_KEY`를 설정한다. 기본값은 `TRANSLATION_MODE=copy`다.
