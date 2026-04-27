# `glossary.csv` — 요구사항 명세

LLM 번역 시 참조하는 용어집. system prompt 에 그대로 삽입된다.

## 형식

UTF-8 (no BOM), 헤더 1행 필수.

```csv
term,translation,protected
```

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `term` | str | 영문 원문 (대소문자 구분 없음, LLM 이 매칭 판단) |
| `translation` | str | 한글 번역. `protected=true` 인 경우 원문 그대로 두고 싶으면 `term` 과 동일하게 |
| `protected` | bool | `true/1/yes` → 번역하지 않음, prompt 에 `(protected)` 표시. 그 외 → 권장 번역으로만 사용 |

## 파서 규칙 (ppt_translate.py / `load_glossary`)

- `csv.DictReader` 로 읽음.
- `term` 이 빈 행은 skip.
- `translation` 의 앞뒤 공백 strip.
- `protected` 의 truthy: `("1", "true", "yes")` (소문자 비교).
- 실패 무시 정책 없음 — 파일이 깨졌으면 명시적으로 실패시킬 것.

## prompt 삽입 형식

```
Glossary:
- Azure: Azure (protected)
- Database Administrator: DBA
- ...
```

## 운영 가이드

- **Microsoft 고유명사** (Azure, Microsoft, Copilot, Fabric 등) → `protected=true`.
- **자주 길어지는 용어** → 짧은 약어로 등록해 슬라이드 디자인 보존 (`Artificial Intelligence,AI,false`).
- **번역 일관성 강제** 필요한 용어 (예: `workload,워크로드`) → `protected=false` 로 등록.

## 비책임

- 정규식/와일드카드 미지원. LLM 의 자연어 매칭에 의존.
- 다국어 미지원 (현재 EN→KO 한 방향).

## 테스트 체크리스트

- [ ] 빈 파일 → 빈 dict 반환, 에러 없이 동작
- [ ] `protected=true` 인 단어가 출력에 그대로 보존
- [ ] 공백 trimming
