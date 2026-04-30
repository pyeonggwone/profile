# Unified Action Tracker (UAT) 정리

## 개요

Unified Action Tracker (UAT)는 Microsoft 내부에서 고객 이슈, 요청, blocker, 제품 피드백, escalation action을 중앙에서 등록하고 추적하는 도구다. Field 조직과 Corp/Engineering 조직 사이의 action item을 한곳에서 관리하여, 고객-facing blocker의 상태, 담당자, 진행 상황, resolution을 투명하게 확인할 수 있게 한다.

| 항목 | 내용 |
|---|---|
| 정식 명칭 | Unified Action Tracker |
| 약어 | UAT |
| 목적 | 고객 blocker, escalation, technical feedback, 내부 action item 관리 |
| 주요 사용자 | MCAPS field, support, CSA, CSM, Technical Specialist, Account Manager 등 |
| 기본 URL | https://uatracker.microsoft.com |
| Shortcut | aka.ms/uat |

## UAT의 역할

UAT는 field escalation의 single source of truth 역할을 한다.

- 고객 engagement 중 발생한 technical blocker를 action item으로 등록
- Field와 Corp/Engineering 간 ownership과 next action 추적
- MSX Opportunity 또는 Milestone과 연결된 blocker 관리
- 제품 개선 요청 또는 feature request를 feedback 흐름으로 연결
- action의 state, priority, due date, discussion, resolution을 기록
- dashboard와 notification을 통해 requestor, owner, follower에게 상태 공유

## 접근 및 권한

MCAPS 소속 field 및 support 인력은 기본적으로 UAT 접근 권한을 갖는다. 접속 시 Microsoft work account 기반 SSO를 사용한다.

접근이 되지 않거나 Access Denied가 발생하면 UAT 상단 toolbar의 **Request Access** 기능을 사용해 권한을 요청한다. 여전히 문제가 있으면 UAT SharePoint에 명시된 support alias 또는 owner에게 문의한다.

## 사용해야 하는 경우

UAT는 일반적인 제품 문의나 단순 제안보다는 고객 성공에 영향을 주는 action을 추적할 때 사용한다.

| 사용 사례 | 설명 |
|---|---|
| Customer blocker | 고객 프로젝트, deployment, migration, adoption이 막힌 경우 |
| Corp escalation | Field에서 해결하기 어려워 Corp/Engineering 지원이 필요한 경우 |
| Technical feedback | 제품 기능, 제한 사항, 개선 요청을 engineering에 전달해야 하는 경우 |
| Capacity request | Azure AI, GPU, regional capacity 등 capacity 관련 요청 |
| Milestone risk | MSX milestone이 Blocked 또는 At-Risk 상태인 경우 |
| Leadership action | RoB, review meeting, executive escalation에서 나온 action 추적 |

가벼운 제품 아이디어나 즉시 고객 영향이 없는 일반 제안은 Feedback 360 등 별도 feedback 채널이 더 적합할 수 있다.

## 주요 Domain

UAT는 여러 Microsoft 내부 workflow domain을 지원한다.

| Domain | 주요 내용 |
|---|---|
| Marketing / MaaS | Marketing as a Service 요청 및 campaign 지원 |
| Partner Marketing Yield Tracker | Partner co-marketing investment 추적 |
| Deal Assist / AMM Offer Desk | Azure Migration & Modernization offer desk 지원 |
| Investment / ECIF Pre-Approval | End Customer Investment Fund pre-approval 관리 |
| GPS Partner Investments | Partner investment workflow 및 승인 관리 |
| Co-Sell Operations | Partner co-sell process 중앙화 |
| Azure AI Capacity Intake | Azure AI, GPU 등 capacity 요청 수집 |
| Service Capacity / Non-AI Capacity | Azure service capacity 관련 요청 |
| MACC Exception | MACC Purple Exception 및 exception approval 추적 |
| Strategic Growth Shaping | Datacenter policy cap 등으로 인한 growth shaping 요청 |
| Solution Area Scrum / Tech RoB | Blocked consumption milestone 및 feature request escalation |
| Red Button | 긴급 post-sales support escalation |
| MCAPS Leader RoB | Leadership meeting action 추적 |
| MCAPSHelp Problem Management | MCAPS process/tool 문제 관리 |
| Microsoft Federal | U.S. Federal 전용 workflow |

## Request Type

UAT action 생성 시 대표적으로 Field Request와 General Request를 선택한다.

| Request Type | 설명 | 사용 예 |
|---|---|---|
| Field Request | 고객-facing 활동에서 발생한 이슈 또는 blocker | 고객 deployment blocker, opportunity/milestone risk, technical escalation |
| General Request | 특정 고객과 직접 연결되지 않은 내부 action 또는 broad feedback | 내부 tool 개선, cross-team process issue, 일반 product feedback |

고객 문제나 MSX milestone blocker와 관련된 경우 대부분 Field Request가 적합하다.

## Action 생성 절차

1. UAT에 접속한다.
2. **Create** 또는 해당 domain tab에서 새 request를 시작한다.
3. Request Type을 선택한다.
4. Title, Description, Customer Scenario, Customer Impact 등 필수 정보를 입력한다.
5. 고객 또는 milestone 관련 정보가 있으면 Account, TPID, Opportunity ID, Milestone ID를 연결한다.
6. Corp/Engineering 지원이 필요하면 **Assign to Corp**를 선택한다.
7. product feedback 성격이면 **Feedback** 옵션을 선택한다.
8. Action Owner, Assigned Team, Priority, Due Date를 확인한다.
9. Create 또는 Save로 제출한다.

제출 후 action은 Action ID를 부여받고, dashboard와 search를 통해 추적할 수 있다.

## MSX Milestone 연계

Blocked 또는 At-Risk MSX milestone은 UAT action과 연결하는 것이 원칙이다. FY26 기준 adoption 목표는 eligible blocked/at-risk milestone의 80% 이상을 UAT request와 연결하는 것이다.

권장 흐름은 다음과 같다.

1. MSX에서 Opportunity를 연다.
2. Milestone status를 Blocked 또는 At-Risk로 설정하고 reason과 estimated usage를 최신화한다.
3. Deal Assistance tab에서 **New Request**를 선택한다.
4. **UAT Action**을 선택해 UAT form을 연다.
5. customer blocker, desired outcome, customer impact, workaround를 입력한다.
6. Corp 지원이 필요하면 Assign to Corp를 Yes로 설정한다.

여러 milestone이 같은 고객/TPID에 영향을 받는 경우 Multiple Milestones 기능으로 하나의 UAT action에 여러 Opportunity와 Milestone을 연결할 수 있다.

## 주요 필드

| 필드 | 의미 | 작성 기준 |
|---|---|---|
| Title | action의 한 줄 요약 | 문제와 요청을 짧고 명확하게 작성 |
| Requestor | 요청 제출자 | 보통 생성자 본인으로 자동 입력 |
| Action Owner | resolution을 drive할 담당자 | 실제 follow-up을 수행할 사람 지정 |
| Assigned Team | 처리 queue 또는 담당 team | blocker 성격에 맞는 team 선택 |
| State | action의 큰 상태 | In Progress, On Hold, Done, Removed 등 |
| Sub State | 세부 진행 단계 | triage, investigation, reopened 등 세부 상태 |
| Action Category | issue 유형 | technical blocker, feature request, capacity 등 |
| Priority | 긴급도 | 고객 영향과 시간 민감도 기준으로 설정 |
| Meeting Type | action이 제기된 forum | Tech RoB, QBR, SLT Review 등 |
| Due Date | 목표 resolution 날짜 | go-live, executive meeting, quarter end 등 기준일 입력 |
| Description | 필요한 도움 | 무엇을 해달라는 요청인지 먼저 작성 |
| Workaround Details | 이미 시도한 우회 방법 | support ticket, mitigation, 실패한 조치 포함 |
| Customer Scenario & Desired Outcome | 고객 상황과 원하는 결과 | 고객이 달성하려는 목표와 성공 조건 설명 |
| Customer Impact | 미해결 시 영향 | revenue, user count, deadline, risk를 구체적으로 작성 |
| Milestone ID | MSX milestone 연결 정보 | blocked/at-risk milestone과 정확히 연결 |
| Est. Monthly Usage | 예상 월간 사용량 또는 consumption | usage, ACR, seat 수 등 impact 규모 기재 |
| Help Needed | 필요한 지원의 세부 유형 | capacity, bug, feature enablement 등 선택 |

## Assign to Corp

**Assign to Corp**는 action을 Microsoft Corp/Engineering triage queue로 즉시 escalation한다는 의미다. Field에서 해결하기 어렵고 engineering 또는 specialist team의 개입이 필요한 critical blocker에 사용한다.

선택 시 일반적으로 corporate triage team이 action을 확인하고 약 1~2 business days 내에 corporate owner 또는 담당 team을 지정한다. 선택하지 않아도 나중에 action을 수정해 Corp escalation으로 전환할 수 있다.

## Feedback 옵션

**Feedback**은 action이 product feedback 또는 feature request 성격임을 표시한다. 즉시 장애 해결보다는 제품 개선, feature delivery, limitation 해소를 engineering에 전달하는 경우 사용한다. 관련 feedback item이 GA 또는 closed 상태가 되면 UAT action이 자동으로 Done 처리될 수 있다.

## State 관리

| State | 의미 |
|---|---|
| In Progress | active 상태이며 작업 중 |
| On Hold | customer input, feature release, dependency 등으로 일시 정지 |
| Done | resolution 완료 또는 action 종료 |
| Removed | 중복, 오등록, scope out 등으로 취소 |

닫힌 action을 다시 진행해야 할 경우 State를 In Progress로 되돌리고 Sub State를 Re-opened로 설정한다. 관련 triage team이나 owner를 discussion에서 tag해 재개 사실을 알리는 것이 좋다.

## Triage 및 처리 흐름

UAT action 제출 후 일반적인 흐름은 다음과 같다.

1. **Submission**: requestor가 action을 생성한다.
2. **Triage**: field lead 또는 triage manager가 내용 완성도와 routing을 확인한다.
3. **Assignment**: field owner 또는 corp owner가 지정된다.
4. **Investigation / Engagement**: owner가 원인, 해결책, 필요한 추가 정보를 검토한다.
5. **Updates**: discussion, email, Teams notification을 통해 진행 상황이 공유된다.
6. **Resolution**: blocker가 해결되면 State를 Done으로 변경하고 closure statement를 남긴다.

내부 triage가 완료되고 alignment가 이뤄지기 전에는 고객에게 직접 답변하거나 참여시키지 않는 것이 원칙이다.

## Tech RoB SLO

Tech RoB 관련 UAT support는 다음과 같은 기준을 따른다.

| 항목 | 목표 |
|---|---|
| Initial Assignment | Corp escalation action은 1 business day 내 acknowledge 및 assignment |
| Follow-up Cadence | P1~P3 action은 최소 5 business days마다 update 또는 feedback 요청 |
| Feature Request Check-in | 중요 feature request는 월 단위 check-in |
| Resolution Timeline | IAR Tech Office Hours 수준의 high-priority case는 60일 내 solution 또는 reasonable answer 목표 |

## 추가 Escalation

표준 Corp engagement 이후에도 해결되지 않는 critical blocker는 추가 escalation path를 사용할 수 있다.

| Escalation | 사용 상황 | 비고 |
|---|---|---|
| IAR Technical Office Hours | senior engineer 검토가 필요한 major technical issue | UAT action이 entry ticket 역할 |
| IAR Executive Escalation | VP-level attention이 필요한 strategic/customer risk | Regional Business Lead endorsement 필요 |
| Restricted Region Shaping (RRS) | 고객에게 특정 Azure region/datacenter 확장이 필요한 경우 | Title 앞에 `[RRS]` 추가, Assign to Corp = Yes |

IAR 관련 상세 deck은 aka.ms/iarintake를 참고한다.

## Dashboard와 검색

UAT homepage는 personal dashboard 역할을 한다.

| View | 설명 |
|---|---|
| Assigned to Me | 내가 Action Owner인 항목 |
| Requested by Me | 내가 제출한 항목 |
| Followed by Me | 내가 follow한 항목 |

Global Search는 Action ID, customer name, keyword 등으로 UAT 전체를 검색한다. View Search는 현재 열어 둔 list 안에서만 keyword filtering을 수행한다.

## Follow와 Notification

Action을 follow하면 직접 owner나 requestor가 아니어도 해당 action의 업데이트를 받을 수 있다. Follow한 항목은 **Followed by Me** view에 표시된다.

UAT는 action 생성, assignment 변경, state 변경, comment 추가, closure 등 주요 이벤트에 대해 email 또는 Teams notification을 보낼 수 있다. 기본적으로 Requestor, Action Owner, Follower가 notification 대상이다.

## Bulk Import

여러 action을 한 번에 등록해야 할 경우 UAT의 bulk import 기능을 사용한다.

1. Create Action menu에서 bulk import template을 다운로드한다.
2. Excel template에 action별 필수 필드를 작성한다.
3. UAT에서 Bulk Import Actions를 선택해 파일을 업로드한다.
4. 생성된 Action ID를 확인한다.

대량 등록 시 최신 template을 사용하고 필수 필드 누락 여부를 사전에 확인해야 한다.

## UAT Copilot

UAT Copilot은 UAT 데이터 위에서 동작하는 내부 AI assistant다. 접근 권한이 있는 데이터 범위 안에서 자연어 질의로 action 정보를 조회하거나 요약할 수 있다.

주요 활용 예시는 다음과 같다.

- 특정 customer의 open action 요약
- Action ID 기준 상태 요약
- 내가 owner인 action 목록 조회
- 고객별 risk 또는 blocker 요약
- 특정 action page 열기

## UI 및 Dashboard 개선 사항

UAT는 Manage Action 및 homepage UI를 개선했다. action 상세 화면은 tab 기반 one-page layout으로 정리되어 request details, related items, attachments, history를 한 화면에서 접근하기 쉬워졌다. Homepage는 collapsible navigation, reorganized command bar, personal dashboard, filter, pagination을 제공한다.

관련 SharePoint 자료:

https://microsoft.sharepoint.com/teams/CSUOneListEngineering/_layouts/15/Doc.aspx?sourcedoc={258D6B46-6041-449B-A642-FC12635F9C17}&file=UnifiedActionTracker-UX -Manage View and Dashboard.pptx&action=edit&mobileredirect=true

## 작성 Best Practices

- Title은 짧지만 action의 핵심 blocker가 드러나게 작성한다.
- Description에는 필요한 도움을 먼저 쓴다.
- Customer Scenario에는 고객이 달성하려는 목표를 쓴다.
- Customer Impact에는 미해결 시 business impact를 구체적으로 쓴다.
- Workaround Details에는 이미 시도한 조치, support ticket, 임시 대응을 남긴다.
- Priority와 Due Date는 실제 고객 영향과 deadline에 맞춘다.
- MSX milestone 정보는 최신 상태로 유지한다.
- Corp escalation이 필요하면 늦추지 말고 Assign to Corp를 사용한다.
- Discussion 질문에는 빠르게 답변해 triage 지연을 줄인다.
- 해결되면 MSX milestone 상태와 UAT State를 모두 최신화한다.

## 참고 링크

| 항목 | 링크 |
|---|---|
| UAT Portal | https://uatracker.microsoft.com |
| UAT Shortcut | aka.ms/uat |
| Tech RoB Playbook | aka.ms/techrob |
| IAR Intake | aka.ms/iarintake |

## 한 줄 요약

UAT는 Microsoft field가 고객 blocker와 escalation을 Corp/Engineering까지 연결해 추적하는 내부 action management system이며, MSX milestone risk와 Tech RoB escalation을 관리하는 핵심 도구다.
