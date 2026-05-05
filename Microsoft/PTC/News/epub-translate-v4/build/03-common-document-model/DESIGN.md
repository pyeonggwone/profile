# Common Document Model 설계

## 목적

포맷별 reader가 서로 다른 내부 구조를 공통 번역 엔진으로 넘길 수 있도록 book, resource, segment 모델을 정의한다.

## 핵심 모델

```text
BookDocument
  metadata
  resources
  sections
  segments
  formatState
```

## BookDocument 예시

```json
{
  "format": "epub",
  "sourceFile": "book.epub",
  "title": "",
  "authors": [],
  "language": "en",
  "sections": [],
  "segments": []
}
```

## Segment 모델

모든 포맷 adapter는 번역 가능한 텍스트를 segment로 반환한다.

```json
{
  "id": "chapter-001-segment-0001",
  "text": "Original text",
  "kind": "body",
  "location": {
    "format": "epub",
    "path": "chapter001.xhtml",
    "selector": "html/body/p[1]/text()[1]"
  },
  "preserve": {
    "leadingWhitespace": "",
    "trailingWhitespace": ""
  }
}
```

## Format State

`formatState`는 writer가 원본 파일을 다시 저장하기 위해 필요한 포맷별 내부 상태다. 공통 번역 엔진은 이 값을 해석하지 않는다.

예시는 다음과 같다.

- EPUB: zip object, OPF path, XHTML path map
- AZW3: record map, text resource offsets, metadata records
- MOBI: PalmDB records, MOBI header, text compression info
- KFX: fragment map, container metadata, text fragment references

## 완료 기준

- 포맷별 reader는 동일한 segment schema를 반환한다.
- writer는 segment translation 결과를 원래 location에 적용할 수 있다.
- 공통 번역 엔진은 `formatState`에 의존하지 않는다.
