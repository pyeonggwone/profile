# README

## 폴더 구조 및 파일 설명

PTC 케이스 단위로 생성되는 폴더이며, 각 케이스 작업에 필요한 입력 정보, 템플릿, 작성 결과, 참고 자료를 포함한다.

---

### `case_statement.md`

케이스의 기본 입력값을 정의하는 파일.  
`person_name`, `case_name`, `support_area_path`, `customer_statement` 등 템플릿 변수 소스로 사용된다.  
다른 파일에서 `[case_statement.md - ...]` 형식으로 참조한다.

---

### `note_templete.md`

케이스 노트 작성을 위한 마크다운 형식의 템플릿.  
섹션별 작성 지침과 예시 형식을 포함하며, 작성자가 참고하는 구조 가이드 역할을 한다.

---

### `note_templete.jsonl`

케이스 노트 각 섹션의 설정을 JSON Lines 형식으로 정의한 파일.  
AI 또는 자동화 도구가 참조하는 사전 설정값을 포함하며, 섹션별로 아래 필드를 제어한다.

| 필드 | 설명 |
|------|------|
| `section` | 섹션 식별자 |
| `language` | 최종 작성 언어 |
| `instruction` | 작성 지침 |
| `token_limit` | 섹션별 최대 토큰 수 |
| `format` | 출력 형식 (key-value / bullet-list / email 등) |
| `tone` | 문체 (factual / technical / professional-friendly 등) |
| `max_bullets` / `max_bullets_per_field` | 섹션별 최대 항목 수 |

섹션별 토큰 설정 근거:

| Section | Token Limit | 근거 |
|---------|-------------|------|
| Basic Information | 150 | 단순 필드값 기입, 자유 서술 없음 |
| Pre-scoping | 350 | 5개 필드 × 항목당 1~2줄, 간결성이 핵심 |
| Scoping | 500 | 5개 카테고리 × 2~3줄, 가장 상세한 기술 서술 |
| Requirement Evaluation | 150 | 답변 섹션 제목 형태, 짧은 구문 4개 |
| IR Message Draft | 400 | 고정 템플릿 골격 + 핵심 평가 항목만 채움 |
| Research Notes | 500 | 4개 서브섹션, 각 2~4줄 요약 |

---

### `note.md`

`note_templete.jsonl` 및 `note_templete.md` 를 참조하여 실제 작성된 케이스 노트.  
섹션별 언어 및 형식 규칙을 따르며, `case_statement.md` 의 값을 채워 완성한다.

---

### `reference_link.md`

조사 및 답변 작성에 사용된 공식 문서 URL을 raw 형태로 나열한 파일.  
가공 없이 URL만 기재하며, `note.md` 의 Research Notes 섹션에서 참조한다.

---

### `reference/`

케이스 관련 추가 참고 자료를 보관하는 디렉토리.
