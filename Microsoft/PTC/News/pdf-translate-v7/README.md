# pdf-translate-v7

PDF 원본 바이너리와 텍스트 상태를 JSON으로 저장하고, 그 JSON을 기준으로 새 PDF를 만드는 프로젝트다.

v7의 기본 목표는 번역이 아니라 round-trip이다. `pdf-state.json` 안에 원본 PDF bytes를 저장하고, 별도로 텍스트만 재구성용 상태로 추출한다. 이미지/path/기타 PDF object는 JSON으로 다시 그리지 않고 원본 바이너리 상태를 사용한다. 다만 분석 참고용으로 table/path/image 상태는 `referenceObjects`에 저장하고, image 파일은 PDF별 폴더에 별도 추출한다. 기본 빌드 모드인 `exact`는 JSON 안의 원본 bytes를 복원하므로 결과 PDF는 원본과 동일한 bytes hash를 목표로 한다. `semantic` 모드는 원본 bytes를 기반으로 PDF를 열고 page content stream의 기존 text block을 제거한 뒤 저장된 text state만 다시 쓰는 경로다.

## 실행

```bash
./run-v7.sh bootstrap
cp /path/to/source.pdf input/
./run-v7.sh input/sample.pdf
```

기본 입력은 `input/` 폴더의 첫 번째 PDF다.

```bash
./run-v7.sh
```

기존 `pdf-state.json`으로 다시 빌드할 수 있다.

```bash
./run-v7.sh --state work/<job>/state/pdf-state.json
```

의미적 재작성 경로를 확인할 때는 다음처럼 실행한다.

```bash
./run-v7.sh --build-mode semantic input/sample.pdf
```

OpenAI로 텍스트를 번역하려면 `.env`에 `OPENAI_API_KEY`를 넣고 실행한다.

```bash
SOURCE_LANG=en TARGET_LANG=ko ./run-v7.sh --build-mode semantic input/sample.pdf
```

또는 `.env`에 다음 값을 둔다.

```text
SOURCE_LANG=en
TARGET_LANG=ko
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
```

번역 결과가 저장된 상태에서는 `exact` bytes 복원 대신 원본 바이너리 기반의 `semantic` 빌드로 PDF를 만든다.

## 출력

```text
work/<job>/state/pdf-state.json
work/<job>/reference/images/<pdf-name>/
work/<job>/pdf/draft.pdf
output/<name>_V7_exact.pdf
output/<name>_V7_semantic.pdf
```

## JSON 저장 범위

| 영역 | 저장 내용 |
|---|---|
| 원본 PDF | file name, path, size, sha256, bytesBase64 |
| 문서 | metadata, page count |
| 페이지 | size, rotation, page/media/crop rectangles |
| 리소스 | page font list, image count |
| text | source text, raw text dict, plain text, textObjects, text state, char state, style model |
| reference | referenceObjects(path/image/table), image file path, image hash |

`referenceObjects`는 참고용이다. PDF 재구성은 이 값을 사용하지 않는다. 이미지, path, 기타 PDF object의 실제 보존은 `source.bytesBase64`에 들어 있는 원본 PDF 바이너리를 기준으로 한다.

## 텍스트 구현 기준

[../pdf_project_text4.md](../pdf_project_text4.md)의 기능 목록을 기준으로 텍스트 상태를 저장한다.

| 기능 축 | v7 구현 |
|---|---|
| PDF object/page 접근 | PyMuPDF document/page 순회 |
| Unicode text extraction | `Page.get_text("text")`, `Page.get_text("rawdict")` |
| 글자/글리프 단위 위치 | rawdict의 char 단위 origin/rectangle 저장 |
| font name/type/size | span font, size, page font list 저장 |
| color/opacity | span color, alpha 저장 |
| direction/rotation | line direction, writing mode, derived rotation 저장 |
| style model | flags와 char flags로 bold/italic/underline/strikeout 후보 저장 |
| JSON export/rewrite | `pdf-state.json` 저장 후 exact/semantic build |

## 모드 차이

| 모드 | 목적 | 결과 |
|---|---|---|
| exact | PDF 전체 상태를 JSON에서 그대로 복원 | 원본 bytes 복원 |
| semantic | 원본 bytes 기반 PDF에 text state 반영 | 텍스트 번역/재작성용 |

`semantic` 모드는 이미지/path를 JSON에서 다시 그리는 경로가 아니다. 원본 content stream에서 `BT ... ET` text block을 제거하고 `textObjects`를 다시 쓴다. 완전 동일 PDF가 목적이면 `exact` 모드를 사용한다.

## 참고용 추출

페이지별 `referenceObjects`에는 다음 정보를 저장한다.

| 유형 | 저장 내용 | 재구성 사용 여부 |
|---|---|---|
| path | drawing items, stroke/fill, opacity, line style, rect | 사용 안 함 |
| image | xref, rect, transform, size, colorspace, hash, imagePath | 사용 안 함 |
| table | table bbox, row/column count, cell rectangles | 사용 안 함 |

이미지 파일은 `work/<job>/reference/images/<pdf-name>/` 아래에 저장한다.

## 번역 단계

번역 단계에서는 `pdf-state.json`의 각 text object를 OpenAI로 번역한다. 원문은 `source`에 보존하고, 번역문은 `text`와 `translated`에 저장한다. 이후 `semantic` 빌드가 원본 바이너리 PDF를 열고 기존 text block을 제거한 다음 이 `text` 값을 text state 위치에 쓴다.
