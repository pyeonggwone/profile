# Metadata and Usage 설계

## 목적

책별 메타데이터, 단어 수, token usage, 처리 상태를 `ebook-metadata/` JSON으로 저장한다.

## 저장 위치

```text
ebook-metadata/{stem}.json
```

동일 stem 충돌 시 구현 단계에서 timestamp 또는 hash suffix 정책을 정한다.

## JSON Schema 초안

```json
{
  "schemaVersion": "1.0",
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
  "tmHitCount": 0,
  "tmMissCount": 0,
  "inputTokenCount": 0,
  "outputTokenCount": 0,
  "totalTokenCount": 0,
  "model": "",
  "startedAt": "",
  "finishedAt": "",
  "durationMs": 0,
  "status": "success",
  "warnings": []
}
```

## 단어 수 정책

- 번역 대상 segment 기준으로 계산한다.
- 영어권 텍스트는 whitespace/token 기반 word count를 사용한다.
- 한국어, 일본어, 중국어 등은 향후 언어별 tokenizer 개선 대상으로 둔다.
- MVP에서는 단순 추정값임을 metadata warning에 남길 수 있다.

## Token Usage 정책

- LLM API 응답의 usage 값을 우선한다.
- usage가 없는 응답은 추정 token count로 기록한다.
- 입력, 출력, 총 token을 분리한다.
- 책 전체 합산값과 batch별 상세값을 선택적으로 저장할 수 있다.

## 완료 기준

- 성공, 실패, skip 모두 metadata JSON이 생성된다.
- token과 word count가 책 단위로 집계된다.
- format adapter의 warning이 metadata에 반영된다.
