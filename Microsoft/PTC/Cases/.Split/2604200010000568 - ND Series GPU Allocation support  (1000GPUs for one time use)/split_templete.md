---
description: reference 자료를 항목별로 분리하여 여러 개의 note.md를 생성한다.
---

# PTC Case Note Split Writer

현재 케이스 디렉토리의 `reference` 폴더를 읽고, 케이스 내 주요 검토 항목을 여러 개의 독립적인 `note.md`로 분리 작성하라.

## 목적

이 작업의 목적은 단일 `note.md`를 완성하기 전에, reference 자료에 포함된 여러 이슈, 질문, 검토 주제, 답변 후보를 항목별로 나누어 각각 별도의 `note.md`로 정리하는 것이다.

각 `note.md`는 최종 답변 작성 전 문제를 정의하고, 요구사항을 평가하며, 검토 범위를 명확히 하기 위한 작업 문서로 사용된다.

## 반드시 읽어야 할 기준 파일

다음 파일은 케이스의 가장 기초적이고 기본적인 정보이므로, 모든 항목 작성 시 검증 기준으로 사용한다.

- `profile/Microsoft/PTC/Cases/.Split/2604200010000568 - ND Series GPU Allocation support  (1000GPUs for one time use)/reference/case_statement.md`

다음 파일은 `note.md`의 섹션 구조와 작성 규칙의 기준으로 사용한다.

- `profile/Microsoft/PTC/Cases/.Split/2604200010000568 - ND Series GPU Allocation support  (1000GPUs for one time use)/reference/note_templete.jsonl`
- `profile/Microsoft/PTC/Cases/.Split/2604200010000568 - ND Series GPU Allocation support  (1000GPUs for one time use)/reference/note_templete.md`
- `profile/Microsoft/PTC/Cases/.Split/2604200010000568 - ND Series GPU Allocation support  (1000GPUs for one time use)/reference/reference_link.md`

## 입력 자료

`reference` 폴더 안의 모든 관련 자료를 검토한다.

단, 다음 파일은 구조와 기준으로만 사용하고, 별도 항목으로 분리하지 않는다.

- `case_statement.md`
- `note_templete.jsonl`
- `note_templete.md`
- `reference_link.md`
- `write-case-note.prompt.md`
- `README.md`

그 외의 Markdown, JSON, HTML, Excel 자료는 항목 분리 후보로 검토한다.

## 작업 방식

1. `case_statement.md`를 먼저 읽고 다음 기본 정보를 파악한다.
   - 담당자 이름
   - 케이스 이름
   - Support area path
   - Customer Statement
   - 고객의 핵심 요청
   - 고객이 실제로 확인하려는 질문

2. `reference` 폴더의 자료를 읽고, 자료를 다음 기준으로 항목화한다.
   - GPU quota / allocation
   - ND Series VM availability
   - region availability
   - VM SKU candidate
   - A100 / H100 조건
   - 1000 GPU 확보 가능성
   - UAT / action guide
   - customer email draft
   - additional information request
   - internal escalation or next action
   - 기타 독립적으로 검토해야 하는 주제

3. 각 항목이 독립적인 검토 주제로 충분하면 별도의 폴더를 만들고, 그 안에 `note.md`를 작성한다.

4. 각 `note.md`는 `note_templete.jsonl`의 섹션 구조를 따른다.
   - `basic_information`
   - `pre_scoping`
   - `scoping`
   - `requirement_evaluation`
   - `ir_message_draft`
   - `research_notes`

5. 각 섹션은 `note_templete.jsonl`에 정의된 규칙을 반드시 따른다.
   - `language`가 `ko`이면 한국어로 작성
   - `language`가 `en`이면 영어로 작성
   - `token_limit` 초과 금지
   - `max_bullets`가 있으면 해당 수 이하로 작성
   - `fields`에 명시된 항목만 작성
   - 임의 섹션 추가 금지

## 출력 구조

현재 케이스 디렉토리 아래에 항목별 폴더를 생성하고, 각 폴더에 `note.md`를 작성한다.

예시:

```text
01-gpu-allocation-overview/
  note.md

02-region-availability/
  note.md

03-vm-sku-candidates/
  note.md

04-a100-h100-feasibility/
  note.md

05-uat-action-guide/
  note.md

06-customer-email-draft/
  note.md