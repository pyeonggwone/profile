# Translation Engine 설계

## 목적

포맷과 무관한 번역 엔진을 설계한다. 이 영역은 segment를 입력받아 번역 결과, token usage, translation memory 정보를 반환한다.

## 처리 흐름

```text
segments
  -> protected term masking
  -> TM lookup
  -> LLM batch translation
  -> placeholder validation
  -> token usage aggregation
  -> TM write
  -> translated segments
```

## 재사용 대상

`epup-translate-v3`에서 다음 개념을 이어받는다.

- glossary CSV
- protected term masking
- placeholder 복원 및 검증
- SQLite translation memory
- OpenAI/Azure OpenAI 호출
- batch 단위 처리

## Translation Result 모델

```json
{
  "segmentId": "chapter-001-segment-0001",
  "sourceText": "Original text",
  "translatedText": "번역문",
  "status": "translated",
  "tmHit": false,
  "usage": {
    "inputTokens": 0,
    "outputTokens": 0,
    "totalTokens": 0
  }
}
```

## 실패 정책

- LLM 오류 시 해당 batch는 원문 fallback한다.
- placeholder 검증 실패 시 해당 segment는 원문 유지한다.
- TM hit는 token usage에 포함하지 않는다.
- 실패 segment 수는 metadata JSON에 기록한다.

## 완료 기준

- 포맷별 adapter 없이도 segment 배열만으로 번역을 실행할 수 있다.
- 책 단위 token usage 합산이 가능하다.
- TM hit/miss 수를 metadata에 전달할 수 있다.
