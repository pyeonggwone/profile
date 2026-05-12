# pdf-translate-v8

v8은 v7 기반 프로젝트이며, PDF 재구성 방식은 유지하고 OpenAI 번역 단계를 chunk 기반으로 개선한 버전이다.

## 핵심 구조

`pdf-state.json`에는 원본 PDF bytes와 텍스트 상태를 저장한다. PDF 재구성은 원본 bytes를 기반으로 열고 기존 text block을 제거한 뒤 `textObjects`의 텍스트를 다시 쓰는 방식이다.

| 영역 | 용도 |
|---|---|
| `source.bytesBase64` | 원본 PDF 바이너리 보존 |
| `textObjects` | 번역/재작성용 텍스트 상태 |
| `state/text-state.json` | 추출 후 사람이 읽기 좋은 텍스트 상태 |
| `state/translated-text-state.json` | OpenAI 번역 병합 후 텍스트 상태 |
| `referenceObjects` | path/image/table 참고용 상태 |
| `reference/images/<pdf-name>/` | PDF별 참고용 image 추출 파일 |
| `reference/content-streams.json` | decoded page/Form XObject content stream 참고용 상태 |

`referenceObjects`는 PDF 재구성에 사용하지 않는다.

## v8 번역 개선

v7은 text object를 작은 batch로 나눠 번역했다. v8은 다음 방식으로 API 호출 수를 줄인다.

| 단계 | 설명 |
|---|---|
| cache 확인 | 이미 번역한 원문은 `work/translation-cache.json`에서 재사용 |
| skip 처리 | 숫자/기호/URL/email 등 번역이 필요 없는 텍스트는 OpenAI 호출 제외 |
| chunk 생성 | page 순서를 유지하면서 `MAX_CHUNK_CHARS`, `MAX_CHUNK_ITEMS` 기준으로 묶음 |
| chunk 번역 | chunk 단위로 OpenAI에 JSON payload 전송 |
| result merge | 응답의 `id` 기준으로 `textObjects`에 번역문 반영 |
| missing retry | 응답에서 누락된 text id는 작은 retry chunk로 한 번 더 요청 |

## 재작성 품질 보정

- PDF 내부 인코딩 문제로 `����`처럼 추출된 span은 번역/재작성 대상에서 제외한다.
- semantic rebuild는 page content stream뿐 아니라 Form XObject의 text stream도 제거한다.
- 번역문은 `translated-text-state.json`의 `textObjects`를 기준으로 원래 span의 bbox 안에 다시 쓴다.
- PDF 텍스트 입력은 `insert_textbox()` 단일 방식으로 처리하고, 필요하면 font size를 단계적으로 줄인다.
- 입력 결과는 `work/<job>/state/text-input-report.json`에 저장한다.

## Content Stream 참고 상태

추출 단계에서 page content stream과 Form XObject stream을 decode해 `work/<job>/reference/content-streams.json`에 저장한다. 이 파일은 `BT`, `ET`, `Tf`, `Tm`, `Tj`, `TJ` 같은 PDF text operator 확인용이며, PDF 재구성에는 사용하지 않는다.

## 번역 산출물

```text
work/<job>/state/progress.json
work/<job>/state/text-state.json
work/<job>/state/translation-input.json
work/<job>/state/translation-chunks.json
work/<job>/state/translation-results.json
work/<job>/state/translation-progress.json
work/<job>/state/translated-text-state.json
work/<job>/state/text-input-report.json
work/translation-cache.json
```

기본 설정에서는 용량 증가를 줄이기 위해 `translation-chunks.json`에는 원문 전체 대신 item id 목록과 통계만 저장하고, `translation-results.json`에는 번역문 전체 대신 chunk별 결과 요약만 저장한다. `translation-cache.json`은 job 간 재사용되는 전역 cache다.

## 진행률 표시

실행 중 콘솔에 단계별 진행률이 출력된다.

```text
PROGRESS 02_extract_pdf_state 3/20 (15.0%) - page 3: text=42, reference=8
PROGRESS 03_translate_text_state 2/12 (16.7%) - chunk chunk-00002: translated=420/2400
PROGRESS 04_build_pdf_from_state 10/20 (50.0%) - page 10: text=37
```

현재 진행 상태는 `work/<job>/state/progress.json`에도 기록된다.

## 용량 최적화

v8 기본값은 경량 저장이다.

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `KEEP_TEXT_RAW` | `false` | PyMuPDF raw text dict 저장 여부 |
| `KEEP_CHAR_STATE` | `false` | 글자 단위 `chars` 상태 저장 여부 |
| `KEEP_TRANSLATION_CHUNKS` | `false` | OpenAI 요청 chunk 원문 전체 저장 여부 |
| `KEEP_TRANSLATION_RESULTS` | `false` | 번역 결과 전문 저장 여부 |

디버깅을 위해 전체 정보를 남기고 싶을 때만 `.env`에서 `true`로 바꾼다.

## 실행

```bash
./run-v8.sh bootstrap
cp /path/to/source.pdf input/
./run-v8.sh input/sample.pdf
```

기본 입력은 `input/` 폴더의 첫 번째 PDF다.

```bash
./run-v8.sh
```

기존 `pdf-state.json`으로 다시 빌드할 수 있다.

```bash
./run-v8.sh --state work/<job>/state/pdf-state.json
```

OpenAI로 텍스트를 번역하려면 `.env`에 `OPENAI_API_KEY`를 넣고 실행한다.

```bash
SOURCE_LANG=en TARGET_LANG=ko ./run-v8.sh --build-mode semantic input/sample.pdf
```

chunk 크기는 환경 변수 또는 CLI 인자로 조정할 수 있다.

```text
MAX_CHUNK_CHARS=10000
MAX_CHUNK_ITEMS=250
KEEP_TEXT_RAW=false
KEEP_CHAR_STATE=false
KEEP_TRANSLATION_CHUNKS=false
KEEP_TRANSLATION_RESULTS=false
```

```bash
./run-v8.sh --max-chunk-chars 8000 --max-chunk-items 200 input/sample.pdf
```

## 출력

```text
work/<job>/state/pdf-state.json
work/<job>/reference/images/<pdf-name>/
work/<job>/pdf/draft.pdf
output/<name>_V8_exact.pdf
output/<name>_V8_semantic.pdf
```

번역 결과가 저장된 상태에서는 `exact` bytes 복원 대신 원본 바이너리 기반의 `semantic` 빌드로 PDF를 만든다.
