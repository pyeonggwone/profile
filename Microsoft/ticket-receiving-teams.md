# Microsoft 케이스 / 티켓 접수 부서 정리

Microsoft에서 고객, 파트너, ISV, 내부 field 팀의 문제를 받는 주요 부서와 시스템을 정리한다. 실제 라우팅은 tenant, 계약, support plan, partner role, internal access, region, workload에 따라 달라질 수 있다.

## 1. 전체 흐름

```text
Customer / Partner / ISV / CSP
↓
External front door
Azure Portal SR, Partner Center Support, Microsoft 365 Admin Center, Power Platform Admin Center
↓
Support / Field / Partner-facing team
Azure Support, CSS, PTC, CSA, CSAM, Account Team, GPS / Partner Team, FastTrack
↓
Specialized queue
Billing, Commerce, Licensing, Marketplace, Capacity, Security, Identity, Deal Desk
↓
Internal escalation
ICM, UAT, Action 360, OneAsk, ADO
↓
Product owner
Product Group, Engineering, CxE / CAT, Service DRI
```

## 2. 파워 구조 요약

| 단계 | 구분 | 대표 팀 / 시스템 | 영향력 |
|---|---|---|---|
| 1 | 접수 입구 | Azure SR, Partner Center Support, MCAPSHelp, GetHelp | 낮음. 접수와 라우팅 중심 |
| 2 | 1차 처리 | Azure Support, CSS, Partner Support, PTC | 중간. 문제 분석과 고객 커뮤니케이션 중심 |
| 3 | Field 영향력 | Account Team, CSAM, CSA, SSP, GPS / Partner Team | 중간~높음. business impact와 priority 형성 |
| 4 | 전문 queue | Marketplace, Billing, Commerce, Capacity, Security, Identity | 높음. 특정 문제 유형의 owner |
| 5 | 공식 escalation | ICM, UAT, Action 360, OneAsk | 높음. Engineering / Product Group 연결 |
| 6 | 최종 결정 | Product Group, Engineering, Service DRI | 최상. 제품 수정, backend 조치, service-side mitigation 결정 |

## 3. 외부 고객 / 파트너 티켓 입구

| 팀 / 시스템 | 받는 문제 | 주 사용 대상 | 링크 | 메모 |
|---|---|---|---|---|
| Azure Support / SR | Azure 기술 문제, quota, 장애, subscription, billing | 고객, 파트너, CSP | [Create an Azure support request](https://learn.microsoft.com/azure/azure-portal/supportability/how-to-create-azure-support-request), [Azure support ticket](https://azure.microsoft.com/support/create-ticket/) | Azure Portal의 Help + Support에서 생성 |
| Azure Support Plans | 기술 지원 가능 여부, severity별 응답 기준 | 고객, partner admin | [Azure support plans](https://azure.microsoft.com/support/plans/), [Support scope and responsiveness](https://azure.microsoft.com/support/plans/response/) | Technical support는 support plan 필요 |
| Azure Quotas | quota increase, vCPU quota, 일부 service quota | 고객, partner admin | [Azure quotas overview](https://learn.microsoft.com/azure/quotas/quotas-overview) | 일반 quota는 portal Quotas에서 직접 요청, non-adjustable quota는 support request 필요 |
| Partner Center Support | Partner Center, workspace, CSP, customer management, benefits, incentives | Microsoft partner | [Get help and contact support in Partner Center](https://learn.microsoft.com/partner-center/support/report-problems-with-partner-center), [Which support portal should I use?](https://learn.microsoft.com/partner-center/support/support-resource-options) | Partner Center Help 또는 AI assistant에서 support request 생성 |
| Partner Center Customer Support | CSP가 고객 대신 service issue를 제기 | CSP, indirect provider | [Report problems on behalf of a customer](https://learn.microsoft.com/partner-center/customers/report-problems-on-behalf-of-a-customer) | 고객 대신 여는 ticket은 권한과 역할 확인 필요 |
| Microsoft Marketplace Support | Marketplace publisher onboarding, offer publish, certification, listing, rewards | ISV, publisher | [Support for Microsoft Marketplace program](https://learn.microsoft.com/partner-center/marketplace-offers/support), [Marketplace publisher support](https://go.microsoft.com/fwlink/?linkid=2165533) | Marketplace offer 관련은 Partner Center support와 연결 |
| Microsoft 365 Admin Center Support | Microsoft 365 tenant, Exchange, Teams, SharePoint, admin issue | 고객 admin, partner delegated admin | [Get support for Microsoft 365 for business](https://learn.microsoft.com/microsoft-365/admin/get-help-support) | Microsoft 365 admin center에서 생성 |
| Power Platform Admin Center Support | Power Apps, Power Automate, Dataverse, Power Platform admin issue | 고객 admin, partner | [Get Help + Support for Power Platform](https://learn.microsoft.com/power-platform/admin/get-help-support) | Power Platform admin center의 Help + Support 사용 |
| Dynamics 365 Support | Dynamics 365 app issue, environment issue | 고객 admin, partner | [Get Help + Support for Power Platform](https://learn.microsoft.com/power-platform/admin/get-help-support) | Dynamics 365 환경 문제도 Power Platform admin center로 들어가는 경우가 많음 |
| Microsoft Entra Support | Identity, tenant, authentication, conditional access, roles | 고객 admin, partner | [Get support for Microsoft Entra](https://learn.microsoft.com/entra/fundamentals/how-to-get-support) | Azure Portal 또는 Entra admin center에서 생성 |
| Security Event Support | Azure 보안 사고, vulnerability, suspected compromise | 고객, publisher, security admin | [Log a security event support ticket](https://learn.microsoft.com/azure/security/fundamentals/event-support-ticket) | 보안 사고는 일반 기술 문의보다 빠른 분류가 필요 |
| Microsoft Support | 일반 제품 지원, consumer/business support 진입 | 고객 | [Contact Microsoft Support](https://support.microsoft.com/contactus) | Azure/Partner/Enterprise 문제는 전용 portal이 더 정확함 |
| Microsoft Q&A | 공개 기술 질의, community answer | 고객, 개발자, 파트너 | [Microsoft Q&A](https://learn.microsoft.com/answers/) | 공식 support ticket은 아님. SLA 없음 |

## 4. MS 내부 / Field 티켓 입구

| 팀 / 시스템 | 받는 문제 | 주 사용 대상 | 링크 | 메모 |
|---|---|---|---|---|
| MCAPSHelp | 내부 tool access, sales system, process support, field 문의 | Microsoft 내부, vendor 계정 가능 범위 | [MCAPSHelp](https://mcapshelp.microsoft.com/) | MSX D365 접근 문제 지원 경로로도 사용 |
| GetHelp | 내부 지원 요청, capacity / service request trigger | Microsoft 내부 | 내부 portal 확인 필요 | 일부 문서에서 phase-out 예정 언급 |
| MSX D365 | Opportunity, milestone, sales pipeline, blocker 표시 | Account Team, CSA, SSP, field team | [MSX D365](https://aka.ms/MSXD365) | UAT 생성 전 milestone 상태 설정에 중요 |
| MSX Insights | MSX reporting, opportunity insight | field team | [MSX Insights](https://aka.ms/MSXi) | MSX 데이터 확인용 |
| MS Sales Access | MSX/MSXi 접근 권한 확인 | field team, vendor | [CheckMyAccess](https://aka.ms/CheckMyAccess), [MSSales access request](https://euaaccessportal.microsoft.com/request/access/MSSales) | assigned customer 기준 접근 제약 가능 |
| UAT | Unified Action Tracker. product / engineering escalation | field team, support, PTC, CSA | [UAT guide](https://aka.ms/uatUnified-Action-Tracker-(UAT)-Guide) | MSX milestone에서 Add UAT Action으로 생성하는 flow가 중요 |
| Action 360 | MSX milestone blocker, technical blocker tracking | field team, escalation owner | 내부 portal 확인 필요 | UAT와 강하게 연결되는 blocker 관리 체계 |
| ICM | Incident Management, service incident, high severity issue | service team, support, engineering | [Microsoft IcM portal](https://portal.microsofticm.com/) | 내부 권한 필요. 장애/incident 처리 power가 큼 |
| OneAsk | 내부 request intake, GBB / specialist help 요청 | field team | [OneAsk](https://oneask.microsoft.com/) | AI Infra UAT 내 GBB 지원 요청 경로로 사용된 사례 있음 |
| ADO | Azure DevOps work item, engineering task tracking | engineering, PM, support | [Azure DevOps](https://dev.azure.com/) | UAT 대체용으로 쓰는 것은 비권장. Engineering work tracking에 가까움 |

## 5. 티켓을 실제로 처리하는 주요 팀

| 팀 / 조직 | 받는 문제 | 주 연결 시스템 | 파워 포인트 | 링크 |
|---|---|---|---|---|
| CSS / Azure Support | Azure technical support, subscription issue, service problem | Azure SR, ICM | 공식 support ticket owner | [Create Azure support request](https://learn.microsoft.com/azure/azure-portal/supportability/how-to-create-azure-support-request) |
| PTC / CSS Partner Enablement | partner technical consultation, presales, deployment blocker | PTC case, SR, UAT, MSX | 파트너 기술 blocker 정리와 escalation 준비 | [PTC README](./PTC/README.md) |
| ISV Success / TPD | ISV architecture, Marketplace, Azure/AI solution guidance | PTC case, Partner Center, Marketplace support | ISV partner technical advisory | [ISV README](./ISV/README.md) |
| Account Team | customer relationship, deal, opportunity, executive pressure | MSX, UAT, email | business priority와 revenue impact 형성 | 내부 조직/고객별 확인 필요 |
| CSAM | customer success, support coordination, escalation alignment | SR, ICM, MSX | 고객 성공/지원 escalation 조율 | 내부 조직/고객별 확인 필요 |
| CSA | architecture, technical validation, solution design | MSX, UAT, SR | 기술 설계와 blocker 설명력 | 내부 조직/고객별 확인 필요 |
| SSP / Solution Specialist | workload/product sales motion, solution opportunity | MSX | 제품별 business priority | 내부 조직/고객별 확인 필요 |
| GPS / Partner Team | partner motion, co-sell, partner business issue | Partner Center, MSX, email | partner business escalation | [Partner Center support](https://learn.microsoft.com/partner-center/support/report-problems-with-partner-center) |
| FastTrack | adoption, migration, deployment guidance | FastTrack engagement | 도입/마이그레이션 실행 지원 | [Microsoft FastTrack](https://www.microsoft.com/fasttrack) |
| Deal Desk | pricing, commercial exception, discount, commitment | MSX, internal process | commercial approval 영향 | 내부 portal 확인 필요 |
| Billing Support | invoice, billing profile, payment, subscription billing | Azure SR, Microsoft 365 admin center | 청구 문제 owner | [Azure support ticket](https://azure.microsoft.com/support/create-ticket/) |
| Commerce Support | commerce platform, MCA, CSP, entitlement, purchase flow | Partner Center, SR | 계약/구매/entitlement 문제 owner | [Partner support options](https://learn.microsoft.com/partner-center/support/support-resource-options) |
| Licensing Support | license assignment, product terms, license eligibility | Partner Center, admin center, support | license 해석과 entitlement 영향 | [Microsoft Product Terms](https://www.microsoft.com/licensing/terms) |
| Partner Center Support | partner account, CSP, incentives, benefits, Partner Center access | Partner Center | 파트너 운영 이슈 owner | [Partner Center support](https://learn.microsoft.com/partner-center/support/report-problems-with-partner-center) |
| Marketplace Support | offer publishing, certification, private plan, transactable offer | Partner Center, Marketplace support | Marketplace publish blocker owner | [Marketplace support](https://learn.microsoft.com/partner-center/marketplace-offers/support) |
| Azure Capacity Team / Capacity Customer Experience | quota, regional capacity, constrained SKU, GPU capacity | Azure SR, UAT, AI capacity queue | capacity 승인/불가 판단에 영향 | [Azure quotas](https://learn.microsoft.com/azure/quotas/quotas-overview), [Azure Capacity internal](https://aka.ms/AzureCapacity) |
| Azure AI Capacity Triage | AI Infra GPU capacity, ND/H100/H200/GB series demand | MSX UAT, AI UAT report | AI Infra capacity queue owner | [AI UAT cases](https://aka.ms/aiuatcases) |
| SCM Team | 일부 GPU/compute SKU assistance, quota/capacity exception | SR, email | 특정 SKU 예외 처리 보조 | SCMTeam@microsoft.com |
| Security Support / Microsoft Security Response | security incident, vulnerability, compromise | security support ticket, ICM | 보안 사고 우선순위 | [Security event support ticket](https://learn.microsoft.com/azure/security/fundamentals/event-support-ticket), [MSRC](https://msrc.microsoft.com/report) |
| Identity / Microsoft Entra Support | authentication, tenant, Entra ID, conditional access | Azure SR, Entra admin center | identity issue owner | [Get support for Microsoft Entra](https://learn.microsoft.com/entra/fundamentals/how-to-get-support) |
| Product Group / Engineering | product bug, backend mitigation, feature gap, service-side fix | ICM, UAT, ADO | 최종 기술 결정권 | 내부 조직별 확인 필요 |
| CxE / CAT | field feedback, customer experience, product adoption blockers | UAT, email, internal channels | Product Group과 가까운 field engineering 성격 | 내부 조직별 확인 필요 |
| Service DRI / Live Site Team | live site incident, mitigation, rollback, hotfix | ICM | 장애 상황 최종 실행력 | 내부 조직별 확인 필요 |

## 6. 문제 유형별 라우팅

| 문제 유형 | 1차 접수 | 2차 / 전문 queue | 최종 escalation |
|---|---|---|---|
| Azure service 장애 | Azure SR | Azure Support / CSS, ICM | Service DRI, Engineering |
| Azure quota 증가 | Azure Portal Quotas 또는 Azure SR | Azure Capacity Team | UAT, Capacity Triage, Product Group |
| AI Infra GPU capacity | Azure SR + MSX UAT | Azure AI Capacity Triage, AI GBB, Deal Desk | Engineering / Capacity owner |
| Partner Center access / CSP 문제 | Partner Center Support | Partner Support / Commerce | Product Group / Engineering |
| Marketplace offer publish | Marketplace Support | Certification / Marketplace publisher support | Marketplace Product Group |
| SaaS transactable offer | Marketplace Support | Partner Center / Marketplace / Fulfillment API support | Marketplace Engineering |
| Billing / invoice | Azure SR 또는 admin center support | Billing Support | Commerce / backend team |
| MCA / CSP / entitlement | Partner Center Support | Commerce Support | Commerce Engineering |
| Microsoft 365 tenant 문제 | Microsoft 365 Admin Center Support | Microsoft 365 Support | Product Group / Service DRI |
| Power Platform / Dynamics 환경 문제 | Power Platform Admin Center Support | Power Platform Support | Product Group / Engineering |
| Entra ID / authentication 문제 | Azure SR 또는 Entra support | Identity Support | Entra Product Group / Engineering |
| 보안 사고 | Security support ticket | Security Support / MSRC / ICM | Security Engineering / Service DRI |
| 고객 deal blocker | Account Team / CSAM / CSA | MSX milestone, UAT | Product Group / Engineering |
| 파트너 기술 blocker | PTC / CSA / Partner Team | SR, UAT, Action 360 | Product Group / Engineering |
| 도입 / migration blocker | FastTrack / CSA / Support | Product specialist, support | Product Group / Engineering |

## 7. 내부 escalation 판단 기준

| 기준 | 의미 | 주로 움직이는 팀 |
|---|---|---|
| Severity | 서비스 장애, production impact, outage 여부 | Azure Support, ICM, Service DRI |
| Business impact | deal, renewal, strategic customer, revenue 영향 | Account Team, CSAM, SSP, MSX, UAT |
| Customer / Partner importance | 전략 고객, ISV, managed partner 여부 | Account Team, GPS, PTC, CSAM |
| Product gap | 제품 기능 부족, bug, roadmap 필요 | Product Group, Engineering, CxE / CAT |
| Capacity scarcity | region/SKU capacity 부족, GPU 공급 제약 | Capacity Team, AI Capacity Triage, Deal Desk |
| Compliance / Security | 침해, vulnerability, regulatory risk | Security Support, MSRC, ICM |

## 8. 실무용 빠른 선택

| 상황 | 먼저 열 곳 | 같이 준비할 것 |
|---|---|---|
| 고객 Azure resource가 실제로 안 됨 | Azure SR | subscription ID, resource ID, timestamp, region, error, impact |
| GPU quota / capacity 필요 | Azure SR + MSX UAT | SKU, GPU 수량, region, workload, commitment, customer impact |
| Partner Center에서 작업이 막힘 | Partner Center Support | workspace, partner tenant, screenshot, request ID |
| Marketplace publish가 막힘 | Marketplace Support | offer ID, plan ID, validation error, screenshot |
| 청구서 / 비용 / invoice 문제 | Azure SR 또는 admin center support | invoice number, billing account, subscription ID |
| license entitlement 문제 | Partner Center / admin center support | tenant ID, SKU, license assignment, product terms 근거 |
| deal 영향이 큼 | Account Team / CSAM / CSA + MSX update | opportunity ID, milestone, close date, revenue impact |
| 제품 버그로 보임 | Azure SR에서 재현 근거 제출 | repro steps, logs, correlation ID, expected/actual behavior |
| 서비스 장애로 보임 | Azure SR + ICM 가능성 확인 | impact scope, severity, time range, affected customers |

## 9. 관련 내부 문서

- [Microsoft 내부 시스템 정리](./internal-systems.md)
- [AI Infra (3P GPU) UAT Escalation 정리](./UAT/1.%20GPU.md)
- [Microsoft PTC README](./PTC/README.md)
- [Microsoft ISV README](./ISV/README.md)

## 10. 핵심 기억

- Ticket front door와 실제 owner는 다르다.
- Azure 문제는 보통 Azure SR이 가장 정식 입구다.
- Partner 운영 문제는 Partner Center Support가 가장 정확하다.
- Marketplace 문제는 Marketplace Support로 분리하는 것이 좋다.
- Deal blocker는 MSX milestone과 Account / CSAM / CSA 영향력이 중요하다.
- Product Group / Engineering을 움직이려면 SR, ICM, UAT, Action 360 같은 공식 escalation 근거가 필요하다.
- Capacity 문제는 SR만으로 끝나지 않고 MSX / UAT / Capacity Triage까지 이어질 수 있다.
