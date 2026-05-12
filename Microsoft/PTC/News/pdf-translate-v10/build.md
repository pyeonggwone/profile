# build

이 문서는 `pdf-translate-v10`의 빌드, 검증, 실행 확인 절차다.

v10은 Python package 프로젝트다. Rust나 Cargo build 단계는 없다.

## 1. 환경 활성화

프로젝트 로컬 `.venv`를 사용하는 경우:

```powershell
cd profile\Microsoft\PTC\News\pdf-translate-v10
.\.venv\Scripts\Activate.ps1
```

workspace 공용 `.venv`를 사용하는 경우 workspace root에서 활성화한 뒤 v10 root로 이동한다.

```powershell
cd profile\Microsoft\PTC\News\pdf-translate-v10
```

## 2. 의존성 설치 확인

editable install 기준:

```powershell
python -m pip install -e .
```

설치된 package metadata를 확인한다.

```powershell
python -m pip show pdf-translate-v10
python -m pip show pikepdf pdfplumber pdfminer.six requests
```

## 3. 문법 검증

Python source 전체를 compile한다.

```powershell
python -m compileall src
```

workspace root에서 실행할 경우:

```powershell
python -m compileall profile\Microsoft\PTC\News\pdf-translate-v10\src
```

## 4. import smoke test

editable install 후에는 다음 명령이 동작해야 한다.

```powershell
python -c "import pdf_translate_v10; print(pdf_translate_v10.__version__)"
```

editable install 없이 확인하려면 `PYTHONPATH`를 지정한다.

```powershell
$env:PYTHONPATH = "src"
python -c "import pdf_translate_v10; print(pdf_translate_v10.__version__)"
```

## 5. CLI smoke test

```powershell
python -m pdf_translate_v10 doctor
```

또는 console script로 확인한다.

```powershell
pdf-translate-v10 doctor
```

qpdf가 아직 없으면 `qpdfOk=false`와 `project-local qpdf not found`가 출력된다. 이는 CLI 자체 실패가 아니라 tool 배치 상태 report다.

## 6. build artifact 생성

wheel/sdist가 필요하면 `build` package를 설치한 뒤 실행한다.

```powershell
python -m pip install build
python -m build
```

생성 위치:

```text
dist/*.whl
dist/*.tar.gz
```

`dist`는 배포 산출물이다. 일반 실행에는 필요하지 않다.

## 7. package 설치 검증

생성한 wheel을 별도 환경에 설치해 확인할 수 있다.

```powershell
python -m pip install .\dist\pdf_translate_v10-0.1.0-py3-none-any.whl
python -m pdf_translate_v10 doctor
```

## 8. pipeline smoke test

실제 PDF와 API 호출 없이 가능한 최소 확인은 `doctor`다.

PDF 추출까지 확인하려면 sample PDF를 `input`에 둔 뒤 실행한다.

```powershell
python -m pdf_translate_v10 run .\input\sample.pdf
```

API key가 없으면 translation 단계는 원문 fallback 결과를 만들고 report에 `TRANSLATION_API_KEY_MISSING`을 기록한다.

현재 v10 초기 구현은 `pdfplumber`/`pdfminer.six` 추출 결과가 원본 content stream byte range와 안전하게 매핑되지 않으면 PDF를 조용히 수정하지 않는다. 이 경우 `rebuild-report.json`에 `REBUILD_BYTE_RANGE_UNAVAILABLE` warning이 남고 결과는 `output/rejected`로 publish된다.

## 9. 성공 기준

기본 build 검증 기준은 다음과 같다.

```text
python -m compileall src                 성공
python -m pdf_translate_v10 doctor       JSON 출력
VS Code Problems                         v10 source 오류 없음
```

qpdf와 API 설정까지 완료된 실행 검증 기준은 다음과 같다.

```text
work/jobs/<job>/state/raw-pdf-text-state.json 생성
work/jobs/<job>/state/readable-text-state.json 생성
work/jobs/<job>/state/translation-results.json 생성
work/jobs/<job>/state/translation-input-part-0001.json 생성
work/jobs/<job>/state/translation-chunk-report-part-0001-0001.json 생성
work/jobs/<job>/reports/rebuild-report.json 생성
work/jobs/<job>/reports/validation-report.json 생성
output/reports/<job>/run-summary.json 생성
```

textless base rebuild가 성공하면 `rebuild-report.json`의 `ok`가 `true`이고 `replaced`가 1 이상이어야 한다. 이 경우 output PDF의 SHA는 source PDF와 달라야 한다.

검증 통과 PDF만 `output/validated`에 위치해야 한다. degraded 또는 fallback 결과는 `output/rejected`에 위치해야 한다.

## 10. 정리

임시 build artifact를 삭제하려면 다음 항목을 제거한다.

```text
build/
dist/
*.egg-info/
```

작업 중간 산출물은 다음 위치에 있다.

```text
work/jobs/
work/db/
```

중간 산출물 삭제 전에는 필요한 report가 `output/reports/<job>`에 publish되어 있는지 확인한다.