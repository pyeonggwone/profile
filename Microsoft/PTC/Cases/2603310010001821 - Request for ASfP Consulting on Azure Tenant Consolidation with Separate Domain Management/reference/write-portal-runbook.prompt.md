---
description: Portal URL, Docs URL, numbered steps만 사용해 Azure 또는 Microsoft Entra 설정 가이드를 작성한다.
---

# Portal Step Guide Writer

사용자의 요구사항, 현재 케이스 문서, 참고 문서를 읽고 Azure Portal 또는 Microsoft Entra admin center에서 그대로 따라 할 수 있는 단계형 문서를 작성하라.

반드시 포털 실행 runbook 스타일로 작성한다. 각 작업은 `## 번호. 작업명` 제목, `Portal URL`, `Docs URL`, numbered steps만 사용한다. 설명 문단, 표, 완료 확인 블록, 주의 사항 블록, 목적 블록은 작성하지 않는다.

## 출력 스타일

출력은 반드시 아래 구조만 사용한다.

```markdown
# <문서 제목>

## 1. <서비스 또는 작업명>

Portal URL: <Portal URL>
Docs URL: <Microsoft Learn URL>

1. <Portal 메뉴 경로 또는 작업>
2. <입력 필드>: `<값>`
3. <같은 화면에서 확인할 항목>:
   - `<확인 항목>` > `<대상 값 이름>`
   - `<확인 항목>` > `<대상 값 이름>`
4. <Portal 메뉴 경로 또는 작업>

## 2. <서비스 또는 작업명>

Portal URL: <Portal URL>
Docs URL: <Microsoft Learn URL>

1. <Portal 메뉴 경로 또는 작업>
2. <입력 필드>: `<값>`
3. <같은 화면에서 확인할 항목>:
	- `<확인 항목>` > `<대상 값 이름>`
	- `<확인 항목>` > `<대상 값 이름>`
```

## 금지 형식

아래 형식은 절대 작성하지 마라.

- 표
- `완료 확인:` 블록
- `주의 사항:` 블록
- `수행 조건:` 블록
- `수행 절차:` 블록
- `결과 정리:` 블록
- `목적:` 블록
- `사전 조건:` 블록
- `의사결정 표`
- `risk register`
- 설명 문단
- 비교 문단
- 요약 문단
- 고객에게 설명하는 문장

## 작성 규칙

- 전체 문서는 한국어로 작성한다.
- 제품명, 서비스명, 포털 메뉴명, role 이름, 정책 이름, 파일명, 환경 변수명은 영어 원문을 유지한다.
- 각 섹션은 반드시 `## <번호>. <작업명>`으로 시작한다.
- 각 섹션 제목 바로 아래에 `Portal URL`과 `Docs URL`을 작성한다.
- `Portal URL`과 `Docs URL` 아래에는 numbered steps만 작성한다.
- numbered steps 외의 일반 문장을 작성하지 않는다.
- 숫자 단계는 화면 이동, 클릭, 생성, 저장, 업로드, 할당처럼 실제 행동이 바뀔 때만 사용한다.
- 같은 화면에서 여러 값을 확인하거나 복사하는 항목은 숫자로 나누지 말고 한 단계 아래 bullet list로 묶는다.
- 같은 종류의 role, policy, domain, user, application, workload 확인 대상은 숫자로 반복하지 말고 `확인 대상:` 아래 bullet list로 묶는다.
- 한 숫자 단계에는 하나의 작업 흐름만 작성한다.
- 포털 경로는 `Azure Portal > ...` 또는 `Microsoft Entra admin center > ...` 형식으로 작성한다.
- 입력값은 `Field name: <value>` 형식으로 작성하고 값은 backtick으로 감싼다.
- 복사해야 하는 값은 `<화면 위치> 복사 > <대상>` 형식으로 작성한다.
- 고객 환경마다 달라지는 값은 `<확인 필요>` 또는 `<PLACEHOLDER>`로 작성한다.
- 바로 변경하면 위험한 production 작업은 수행 단계로 쓰지 말고 `확인 대상:` 단계로만 작성한다.
- CLI, PowerShell, Terraform, Bicep 명령은 작성하지 않는다.
- 마지막 섹션은 필요한 경우 `.env 입력값`, `확인값 입력값`, 또는 `고객 확인값` 같은 값 목록 코드 블록으로만 작성한다.

## 이 케이스 작성 지시

다음 케이스를 대상으로 작성한다.

- 케이스명: `Request for ASfP Consulting on Azure Tenant Consolidation with Separate Domain Management`
- 목적: 여러 affiliated companies의 Azure tenant를 단일 target tenant 중심으로 통합 가능 여부를 검토한다.
- 추가 조건: 회사별 email domain과 identity domain을 분리 운영할 수 있는지 확인한다.

출력 문서에는 다음 작업만 포함한다.

1. 작업 계정 및 권한 확인
2. Tenant 정보 확인
3. Custom domain 확인
4. Subscription 확인
5. Target tenant 후보 확인
6. Domain 운영 기준 확인
7. Identity source 확인
8. Administrative units 확인 또는 생성
9. Conditional Access 확인
10. Management groups 및 Azure RBAC 확인
11. Cross-tenant synchronization 확인 또는 pilot 구성
12. Enterprise applications 및 app registrations 확인
13. Microsoft 365 workload 확인
14. 고객 확인값

최종 결과에는 프롬프트 설명을 포함하지 말고 완성된 `.md` 본문만 작성한다.
