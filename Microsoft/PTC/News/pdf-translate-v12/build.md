# build

## 문법 확인

WSL에서 v12 폴더 기준:

```bash
python3 -m compileall src
```

PowerShell에서 workspace root 기준:

```powershell
C:\Users\v-kimpy\test\.venv\Scripts\python.exe -m compileall profile\Microsoft\PTC\News\pdf-translate-v12\src
```

## 도구 점검

```bash
./run-v12.sh doctor
```

## 실행

```bash
./run-v12.sh input/sample.pdf
```

OpenAI 번역:

```bash
./run-v12.sh --translation-mode openai input/sample.pdf
```

OCR:

```bash
./run-v12.sh --ocr local input/sample.pdf
```

## 단계별 PDF 확인

실행 후 다음 경로를 확인한다.

```text
work/<job-id>/pdf/stages/
```

확인 순서는 `01-base.pdf`, `02-source-text-on-base.pdf`, `03-translated-text-on-base.pdf`다.
`02-source-text-on-base.pdf`는 베이스 위에 영문 원문 text layer를 그대로 입력한 파일이고, `03-translated-text-on-base.pdf`는 같은 베이스 위에 번역문 text layer를 입력한 최종 기준 파일이다.
