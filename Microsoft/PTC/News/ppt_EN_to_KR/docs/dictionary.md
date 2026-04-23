# 번역 사전 (translation_dict.json)

## 구조

```json
{
  "version": 1,
  "entries": {
    "database modernization": "데이터베이스 현대화",
    "workload": "워크로드"
  },
  "protected_terms": [
    "Azure", "Microsoft", "SQL", "Copilot", "Fabric", "OpenAI"
  ]
}
```

## 운영 규칙

- `entries`: 슬라이드 번역마다 LLM이 신규 용어 추출하여 자동 추가 (STEP 3의 `dict_manager.py`)
- `protected_terms`: 번역하지 않는 고유명사 목록
- 충돌 시 기존 값 유지 (덮어쓰기 금지)
- 전체 프로젝트 공통 누적 관리 (여러 PPT 파일에 걸쳐 재사용)
