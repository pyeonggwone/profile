# progress.json

`work/progress/{파일명}.json` — 모니터링 전용 기록. 재개 목적 아님.

```json
{
  "filename": "Microsoft Databases narrative L100.PPTX",
  "started_at": "2026-04-22T10:00:00",
  "completed_at": null,
  "total_slides": 44,
  "steps": {
    "extract": "done",
    "font_analysis": "done",
    "translation": "in_progress",
    "dict_update": "pending"
  },
  "slides_translated": [1, 2, 3],
  "slides_total": 44
}
```

## steps 키

| 키 | 의미 |
|----|------|
| `extract` | STEP 2 extractor.py 완료 여부 |
| `font_analysis` | STEP 2 font_analyzer.py 완료 여부 |
| `translation` | STEP 3 translator.py 진행 상태 |
| `dict_update` | STEP 3 dict_manager.py 진행 상태 |

## 상태 값

- `pending` / `in_progress` / `done` / `failed`
