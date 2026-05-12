# epub-translate-v4

네이티브 멀티 포맷 전자책 번역 플랫폼 설계 문서.

이 문서는 구현 기준 문서이며, `epup-translate-v3`를 참고해 `epub-translate-v4`를 새 프로젝트로 진행할 때의 요구사항을 고정한다.

## 1. 프로젝트 생성

- 기존 `epup-translate-v3`는 그대로 두고, 구현 참고 자료로만 사용한다.
- 신규 프로젝트 디렉터리 `epub-translate-v4`에 새 프로젝트로 구현한다.
- `epub-translate-v4`는 EPUB 전용 번역기가 아니라, 네이티브 멀티 포맷 전자책 번역 플랫폼으로 구성한다.

## 2. 핵심 목표

- 입력된 전자책 파일의 포맷을 자동 감지한다.
- 감지된 포맷별로 별도 처리 프로세스를 실행한다.
- 번역 후 원본과 같은 포맷으로 `output/`에 저장한다.
- 현재 단계의 1차 목표는 완벽한 품질이 아니라, 각 포맷별로 성공적으로 번역되고 저장되는 것을 확인하는 것이다.
- 향후 목표는 각 포맷의 구조, 메타데이터, 레이아웃, 리소스를 최대한 유지하는 것이다.

## 3. 지원 대상 포맷

초기 지원 대상은 다음과 같다.

- `epub`
- `azw3`
- `mobi`
- `kfx`

## 4. 입력/출력 규칙

- `input/` 디렉터리에 전자책 파일을 넣는다.
- 실행 시 `input/` 내부의 지원 포맷 파일을 스캔한다.
- 각 파일의 확장자와 실제 포맷 정보를 확인한다.
- 포맷에 따라 처리 프로세스를 분기한다.
- 출력 파일은 `output/` 디렉터리에 생성한다.
- 출력 파일은 원본과 같은 포맷을 유지한다.

예시:

```text
input/book.epub  -> output/book_KR.epub
input/book.azw3  -> output/book_KR.azw3
input/book.mobi  -> output/book_KR.mobi
input/book.kfx   -> output/book_KR.kfx
```

## 5. 처리 흐름

전체 파이프라인은 다음 순서로 구성한다.

```text
input scan
    -> format detection
    -> metadata extraction
    -> format-specific reader
    -> text segment extraction
    -> translation engine
    -> format-specific writer
    -> same-format output
    -> metadata JSON export
    -> move original file to input/done/
```

## 6. 포맷별 처리 구조

`epub-translate-v4`는 포맷별 native adapter 구조를 사용한다.

```text
src/
├── index.mjs
├── pipeline.mjs
├── formats/
│   ├── detect.mjs
│   ├── epub/
│   │   ├── reader.mjs
│   │   ├── writer.mjs
│   │   └── text.mjs
│   ├── azw3/
│   │   ├── reader.mjs
│   │   ├── writer.mjs
│   │   └── text.mjs
│   ├── mobi/
│   │   ├── reader.mjs
│   │   ├── writer.mjs
│   │   └── text.mjs
│   └── kfx/
│       ├── reader.mjs
│       ├── writer.mjs
│       └── text.mjs
├── translate/
│   ├── llm.mjs
│   ├── masker.mjs
│   ├── glossary.mjs
│   └── tm.mjs
├── metadata/
│   ├── extractor.mjs
│   ├── usage.mjs
│   └── writer.mjs
└── util/
        ├── env.mjs
        └── log.mjs
```

## 7. 공통 번역 엔진

- 번역 로직은 포맷과 분리한다.
- 모든 포맷 adapter는 공통 text segment 구조를 반환한다.
- 번역 엔진은 포맷을 알 필요 없이 segment만 처리한다.
- glossary, protected term masking, translation memory, LLM 호출 로직은 공통 모듈로 유지한다.

공통 segment 예시:

```json
{
    "id": "chapter-001-segment-0001",
    "text": "Original text",
    "location": {
        "format": "epub",
        "file": "chapter001.xhtml",
        "nodePath": "html/body/p[1]/text()[1]"
    }
}
```

## 8. EPUB 처리 요구사항

- 기존 `epup-translate-v3`의 EPUB 처리 로직을 기반으로 한다.
- ZIP 구조, `mimetype`, `META-INF/container.xml`, OPF, XHTML spine 구조를 유지한다.
- XHTML 텍스트 노드만 번역한다.
- 이미지, 폰트, CSS, `script`, `style`, `code`, `pre`, `svg`, `math` 등은 보존한다.
- 출력은 `.epub`으로 저장한다.

## 9. AZW3 처리 요구사항

- AZW3 파일을 native format adapter로 처리한다.
- 초기 단계에서는 성공적으로 텍스트를 추출, 번역, 저장하는 것을 우선한다.
- 출력은 `.azw3`로 저장한다.
- 향후에는 AZW3 내부 구조, Kindle 메타데이터, 리소스, 레이아웃 보존 품질을 개선한다.

## 10. MOBI 처리 요구사항

- MOBI 파일을 native format adapter로 처리한다.
- 초기 단계에서는 성공적으로 텍스트를 추출, 번역, 저장하는 것을 우선한다.
- 출력은 `.mobi`로 저장한다.
- 향후에는 MOBI 헤더, 목차, 이미지, 메타데이터, 본문 구조 보존 품질을 개선한다.

## 11. KFX 처리 요구사항

- KFX 파일을 native format adapter로 처리한다.
- 초기 단계에서는 성공적으로 텍스트를 추출, 번역, 저장하는 것을 우선한다.
- 출력은 `.kfx`로 저장한다.
- KFX는 난이도가 높으므로 초기 구현에서는 제한사항을 명확히 기록한다.
- 향후에는 Kindle enhanced typesetting, 위치 정보, 메타데이터, 리소스 보존 품질을 개선한다.

## 12. 메타데이터 JSON 생성 기능

- 번역 완료 후 책별 메타데이터 JSON 파일을 생성한다.
- 메타데이터 JSON은 `ebook-metadata/` 디렉터리에 저장한다.
- 파일명은 책 이름 또는 입력 파일 stem을 기준으로 한다.

예시:

```text
ebook-metadata/book.json
```

JSON에는 최소한 다음 정보를 포함한다.

```json
{
    "sourceFile": "book.azw3",
    "outputFile": "book_KR.azw3",
    "format": "azw3",
    "title": "",
    "authors": [],
    "publisher": "",
    "language": "",
    "targetLanguage": "ko",
    "totalWordCount": 0,
    "translatedSegmentCount": 0,
    "skippedSegmentCount": 0,
    "inputTokenCount": 0,
    "outputTokenCount": 0,
    "totalTokenCount": 0,
    "model": "",
    "startedAt": "",
    "finishedAt": "",
    "durationMs": 0,
    "status": "success"
}
```

## 13. 토큰 사용량 기록

- 책 1권 단위로 번역에 사용된 토큰 수를 기록한다.
- 가능하면 LLM API 응답의 usage 정보를 우선 사용한다.
- API usage 정보가 없을 경우 추정 토큰 수를 기록한다.
- 입력 토큰, 출력 토큰, 총 토큰을 분리해 기록한다.

## 14. 단어 수 기록

- 책 전체의 원문 단어 수를 계산한다.
- 가능하면 번역 대상 segment 기준으로 계산한다.
- 총 단어 수는 `totalWordCount`에 기록한다.
- 향후 언어별 단어 계산 방식을 개선할 수 있도록 별도 모듈로 분리한다.

## 15. DRM 처리

- DRM이 감지된 파일은 번역하지 않는다.
- DRM 파일은 실패로 기록하되 삭제하지 않는다.
- 메타데이터 JSON에는 실패 상태와 사유를 기록한다.

예시:

```json
{
    "sourceFile": "book.azw3",
    "format": "azw3",
    "status": "skipped",
    "reason": "DRM protected"
}
```

## 16. TODO.md 작성

- `TODO.md`를 생성한다.
- `TODO.md`에는 현재 MVP 이후 완성도를 높이기 위한 작업 목록을 작성한다.
- 특히 다음 항목을 포함한다.

```md
# TODO

## Format Preservation

- EPUB 구조 보존 품질 검증
- AZW3 native reader/writer 완성도 개선
- MOBI native reader/writer 완성도 개선
- KFX native reader/writer 완성도 개선
- 원본 메타데이터 보존 강화
- 목차/내비게이션 보존 강화
- 이미지/폰트/CSS 리소스 보존 강화
- Kindle 전용 메타데이터 보존 검토
- KFX enhanced typesetting 정보 보존 검토

## Translation Quality

- segment 분리 품질 개선
- 문단 단위/문장 단위 번역 옵션 추가
- placeholder 검증 강화
- glossary 적용 품질 개선
- translation memory hit rate 기록

## Metadata

- 책별 token usage 기록
- 책별 word count 기록
- 책별 번역 시간 기록
- 책별 실패/스킵 사유 기록
- metadata schema version 추가

## Validation

- 포맷별 output 파일 열림 검증
- EPUBCheck 연동
- Kindle Previewer 연동 검토
- Calibre ebook-viewer 검증
- 샘플 파일 기반 regression test 추가

## CLI

- input/output/work/metadata directory 옵션 추가
- 특정 포맷만 처리하는 옵션 추가
- dry-run 옵션 추가
- metadata-only 옵션 추가
- verbose/debug 로그 옵션 추가
```

## 17. 구현 원칙과 제외 범위

- `epup-translate-v3`는 수정하지 않고, 필요한 구조와 구현 방식을 참고만 한다.
- 포맷 변환 기반 구현으로 native adapter 요구사항을 대체하지 않는다.
- DRM 우회 또는 제거 기능은 구현하지 않는다.
- 초기 구현은 EPUB adapter와 공통 파이프라인을 우선하고, AZW3/MOBI/KFX는 native adapter 경계를 먼저 만든 뒤 단계적으로 완성한다.
