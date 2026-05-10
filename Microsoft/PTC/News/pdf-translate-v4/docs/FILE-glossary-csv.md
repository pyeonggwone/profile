# `glossary.csv` — pdf-translate-v4

LLM 번역 시 참조하는 용어집. system prompt 에 그대로 삽입되며, `protected=true` 인 용어는 placeholder 로 보호되어 LLM 응답에서도 원문 그대로 유지된다.

## 형식

UTF-8 (BOM 허용), 헤더 1행 필수.

```csv
term,translation,protected
Azure,Azure,true
Microsoft,Microsoft,true
Copilot,Copilot,true
Database Administrator,DBA,false
workload,워크로드,false
```

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `term` | str | 원문 (대소문자/구두점 매칭은 placeholder 단계에서 정확 일치) |
| `translation` | str | 권장 번역. `protected=true` 인 경우 보통 `term` 과 동일하게 둠 |
| `protected` | bool | `true/1/yes` → placeholder 치환으로 강제 유지. 그 외 → 권장 번역으로만 prompt 에 삽입 |

## 파서 규칙 (`src/glossary/loader.mjs`)

- `csv-parse` 의 `columns: true` + `skip_empty_lines: true` + `trim: true`.
- `term` 이 빈 행은 skip.
- `translation` 의 앞뒤 공백 strip.
- `protected` 의 truthy: `("1", "true", "yes")` (소문자 비교).
- 깨진 CSV 는 명시적으로 throw.

## prompt 삽입 형식 (`src/translate/llm.mjs`)

```
Glossary:
- Azure => Azure (protected, keep exactly)
- Microsoft => Microsoft (protected, keep exactly)
- workload => 워크로드
- ...
```

비어 있으면 `(none)`.

## placeholder 보호 (`src/glossary/masker.mjs`)

- `protected=true` 인 term 은 글자 길이 내림차순으로 정렬된 후 단어 경계 기반 정규식으로 매칭되어 `__PDFSTR_TERM_NNNN__` 로 치환된다.
- LLM 응답에서 placeholder 가 누락되거나 순서가 바뀌면 원문 fallback (TM 에 저장하지 않음).
- 응답이 정상이면 placeholder 를 원래 term 으로 복원한 뒤 PDF 에 적용된다.

## 운영 가이드

- **Microsoft 고유명사** (Azure, Microsoft, Copilot, Fabric 등) → `protected=true`.
- **자주 길어지는 용어** → 짧은 약어로 등록해 PDF layout 변형 최소화.
- **번역 일관성 강제** 필요한 용어 (예: `workload,워크로드`) → `protected=false` 로 등록.

## 비책임

- 정규식/와일드카드 미지원. 단어 경계 기반 정확 일치만.
- 다국어 동시 매칭 미지원 (현재 단방향 source → target).
- LLM 의 자연어 매칭 품질에 의존하는 부분 (`protected=false` 항목) 은 보장하지 않는다.
