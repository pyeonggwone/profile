# PTC가 연결할 수 있는 Microsoft 부서 / 시스템 정리

PTC(Partner Technical Consultant)는 최종 승인권이나 제품 수정 권한을 가진 부서는 아니지만, 파트너/ISV의 기술 문제를 분석한 뒤 적절한 Microsoft 내부/외부 지원 경로로 연결하는 역할을 한다.

## 1. PTC 위치 요약

```text
Partner / ISV / CSP
↓
PTC
↓
Support / Field / Specialist / Escalation 경로
↓
Product Group / Engineering / Service Owner
```

PTC의 핵심 역할은 다음과 같다.

- 파트너 질문을 기술 문제, 운영 문제, 상업 문제, 제품 문제로 분류
- 파트너가 직접 열어야 하는 공식 ticket 경로 안내
- 필요한 경우 CSA, Support, Marketplace, Capacity, UAT 등으로 연결
- Engineering이 볼 수 있는 수준으로 blocker, impact, repro, evidence 정리
- 단순 문의는 PTC 선에서 guidance 제공

## 2. PTC가 연결할 수 있는 주요 경로

| 연결 대상 | 연결하는 경우 | PTC의 역할 | 링크 / 경로 |
|---|---|---|---|
| Azure Support / CSS | Azure resource 장애, quota, service issue, technical support | SR 생성 안내, 문제 설명 정리, support plan/권한 확인 | [Create Azure support request](https://learn.microsoft.com/azure/azure-portal/supportability/how-to-create-azure-support-request) |
| Partner Center Support | Partner Center access, CSP, benefits, incentives, customer relationship 문제 | 파트너가 Partner Center에서 support request 생성하도록 안내 | [Partner Center support](https://learn.microsoft.com/partner-center/support/report-problems-with-partner-center) |
| Microsoft Marketplace Support | SaaS offer, Managed Application, private plan, publish/certification 문제 | offer ID, validation error, listing 상태 정리 후 지원 경로 안내 | [Marketplace support](https://learn.microsoft.com/partner-center/marketplace-offers/support) |
| CSA | 고객/파트너 architecture, Azure solution design, workload validation | 기술 검토 결과와 blocker 전달, 공동 architecture 논의 | 내부 account / workload owner 확인 필요 |
| CSAM | 고객 escalation, support coordination, strategic customer issue | 고객 impact와 SR/UAT 상태를 정리해 전달 | 내부 customer account 확인 필요 |
| Account Team | deal 영향, opportunity blocker, executive pressure 필요 | business impact, close date, revenue 영향 정리 | MSX opportunity / milestone 기준 |
| SSP / Solution Specialist | 특정 workload/product sales motion, 제품별 deal blocker | workload별 기술/상업 이슈 정리 | MSX / 내부 specialist 확인 필요 |
| GPS / Partner Team | 파트너 business, co-sell, partner motion, partner program 이슈 | 파트너 기술 blocker와 business blocker 구분 | [Partner Center support](https://learn.microsoft.com/partner-center/support/report-problems-with-partner-center) |
| FastTrack | migration, adoption, deployment guidance | PTC guidance 범위를 넘어서는 도입 지원 연결 | [Microsoft FastTrack](https://www.microsoft.com/fasttrack) |
| Billing Support | invoice, payment, billing account, subscription charge 문제 | 기술 문제가 아님을 구분하고 billing ticket 경로 안내 | [Azure support ticket](https://azure.microsoft.com/support/create-ticket/) |
| Commerce Support | MCA, CSP, purchase, entitlement, subscription transaction 문제 | Partner Center / commerce issue로 분리 | [Partner support options](https://learn.microsoft.com/partner-center/support/support-resource-options) |
| Licensing Support | license eligibility, BYOL, product terms, entitlement 해석 | Product Terms 근거 정리, 필요 시 licensing 경로 안내 | [Microsoft Product Terms](https://www.microsoft.com/licensing/terms) |
| Azure Capacity Team | regional capacity, VM SKU unavailable, GPU quota/capacity | SKU, region, quantity, workload, business impact 정리 | [Azure quotas](https://learn.microsoft.com/azure/quotas/quotas-overview), [Azure Capacity internal](https://aka.ms/AzureCapacity) |
| Azure AI Capacity Triage | ND/H100/H200/GB series 등 AI Infra GPU capacity | MSX milestone/UAT 조건 확인, request 분리 기준 정리 | [AI UAT cases](https://aka.ms/aiuatcases) |
| Deal Desk | discount, pricing exception, commitment, commercial validation | 가격/commitment 관련 blocker를 Account/SSP 쪽으로 넘김 | 내부 process 확인 필요 |
| Security Support / MSRC | security incident, vulnerability, suspected compromise | 일반 기술 문의와 분리해 보안 incident 경로 안내 | [Security event support ticket](https://learn.microsoft.com/azure/security/fundamentals/event-support-ticket), [MSRC report](https://msrc.microsoft.com/report) |
| Microsoft Entra Support | identity, tenant, authentication, conditional access, cross-tenant 문제 | Entra issue로 분리, tenant/로그/impact 정리 | [Get support for Microsoft Entra](https://learn.microsoft.com/entra/fundamentals/how-to-get-support) |
| Microsoft 365 Support | Teams, Exchange, SharePoint, M365 admin 문제 | Azure/PTC 범위가 아닌 경우 admin center support 안내 | [Microsoft 365 support](https://learn.microsoft.com/microsoft-365/admin/get-help-support) |
| Power Platform Support | Power Apps, Power Automate, Dataverse, Dynamics environment 문제 | environment ID, tenant, error, repro 정리 | [Power Platform support](https://learn.microsoft.com/power-platform/admin/get-help-support) |
| UAT | Engineering / Product Group escalation이 필요한 blocker | MSX milestone과 business impact 기반으로 escalation 준비 | [UAT guide](https://aka.ms/uatUnified-Action-Tracker-(UAT)-Guide) |
| Action 360 | MSX milestone blocker 추적, field escalation 관리 | UAT/MSX blocker 상태와 next action 정리 | 내부 portal 확인 필요 |
| ICM | high severity incident, live site issue, service outage | PTC가 직접 owner는 아니며 Support/Service team과 연결 | [Microsoft IcM portal](https://portal.microsofticm.com/) |
| OneAsk | GBB/specialist help, internal expert request | 내부 specialist 도움 요청 경로로 활용 | [OneAsk](https://oneask.microsoft.com/) |
| Product Group / Engineering | product bug, feature gap, backend mitigation 필요 | 직접 접근보다 SR/UAT/ICM/field owner를 통해 연결 | 내부 product owner 확인 필요 |
| CxE / CAT | customer experience issue, adoption blocker, product feedback | 반복 이슈/field feedback으로 정리 | 내부 조직별 확인 필요 |

## 3. 문제 유형별 PTC 연결 판단

| 파트너 요청 | PTC가 먼저 할 일 | 연결 대상 | 핵심 준비물 |
|---|---|---|---|
| Azure 서비스가 동작하지 않음 | 기술 문제인지 설정 문제인지 1차 분류 | Azure Support / CSS | subscription ID, resource ID, region, timestamp, error, impact |
| quota 증가 요청 | quota 종류와 SKU/region 확인 | Azure Support, Azure Capacity Team | current quota, requested quota, SKU, region, business reason |
| GPU capacity 요청 | AI Infra인지 일반 GPU인지 분리 | Azure Support, Azure AI Capacity Triage, UAT | SKU, GPU 수량, region, workload, commitment, customer impact |
| Marketplace 등록 문제 | offer type과 publish 단계 확인 | Marketplace Support | offer ID, plan ID, validation error, screenshot |
| SaaS transactable offer 구현 | technical guidance 가능 여부 확인 | Marketplace Support, CSA, Engineering via support | fulfillment API, landing page, webhook, tenant model |
| Partner Center access 문제 | PTC 기술 범위 밖으로 분류 | Partner Center Support | partner tenant, workspace, role, screenshot |
| CSP 고객 대신 support 필요 | CSP 권한과 delegated admin 확인 | Partner Center Customer Support, Azure Support | customer tenant, subscription, relationship, issue detail |
| billing / invoice 문제 | 기술 문제가 아님을 명확히 분리 | Billing Support, Commerce Support | invoice, billing account, subscription, charge detail |
| license / BYOL 질문 | Product Terms와 eligibility 확인 | Licensing Support, Commerce Support | SKU, license type, agreement, Product Terms 근거 |
| Entra / tenant migration | architecture guidance와 support issue 분리 | Entra Support, CSA | tenant ID, domain, sync model, risk, rollback plan |
| Power Platform / Dynamics 문제 | admin center support 경로 확인 | Power Platform Support | environment ID, tenant, app ID, error, repro |
| 보안 사고 / 취약점 | 일반 technical support와 분리 | Security Support, MSRC | incident timeline, affected resource, evidence, severity |
| deal blocker | technical blocker와 business impact 정리 | Account Team, CSAM, CSA, SSP, UAT | opportunity ID, close date, revenue impact, blocked milestone |
| 제품 버그 의심 | 재현 가능성 확인 | Azure Support, Product Group via SR/UAT | repro steps, logs, correlation ID, expected/actual behavior |
| 기능 요청 / product gap | workaround 여부와 business impact 정리 | CSA, CxE/CAT, Product Group via UAT | scenario, customer value, blocker level, alternative options |
| architecture review | PTC 선에서 검토 후 필요 시 확장 | CSA, FastTrack, specialist | architecture diagram, workload, constraints, security/compliance requirement |

## 4. PTC가 직접 해결하기 좋은 영역

| 영역 | PTC 선에서 가능한 일 |
|---|---|
| Architecture guidance | Azure 서비스 조합, reference architecture, 보안/네트워크/운영 관점 검토 |
| Presales technical support | 파트너가 고객에게 설명할 기술 구조, 장단점, 옵션 정리 |
| Marketplace readiness | SaaS/Managed Application/VM offer 방향성, 준비 항목, 기술 요구사항 안내 |
| AI / Azure solution design | Azure OpenAI, AI Search, App Service, AKS, Container Apps 등 구성 가이드 |
| Entra / identity 설계 | cross-tenant, B2B, authentication pattern, conditional access 영향 검토 |
| Cost / sizing rough estimate | VM/service 선택지, PAYG/RI 비교, 초기 산정 가이드 |
| Documentation | partner-facing guide, architecture summary, email response, meeting follow-up 작성 |

## 5. PTC가 직접 해결하기 어려운 영역

| 영역 | 이유 | 연결 대상 |
|---|---|---|
| 제품 버그 수정 | 코드/서비스 backend 수정 권한 없음 | Azure Support, Product Group, Engineering |
| live site 장애 조치 | service DRI 권한 없음 | Azure Support, ICM, Service DRI |
| quota/capacity 승인 | capacity allocation 권한 없음 | Azure Capacity Team, AI Capacity Triage |
| billing 조정 | 청구/계약 권한 없음 | Billing Support, Commerce Support |
| license/legal 해석 확정 | 공식 계약/법무 권한 없음 | Licensing Support, Commerce, Legal/Compliance |
| Partner Center backend 수정 | Partner Center owner 아님 | Partner Center Support, Product Group |
| Marketplace certification 승인 | certification owner 아님 | Marketplace Support, Certification team |
| discount / pricing exception | commercial approval 권한 없음 | Deal Desk, Account Team, SSP |
| customer executive escalation | account ownership 없음 | Account Team, CSAM |

## 6. PTC 연결 시 권장 문장

### Azure Support로 보낼 때

```text
This appears to require an official Azure Support Request because it involves service-side investigation or subscription/resource-specific access. Please open an Azure SR with the subscription ID, resource ID, region, timestamps, error details, and business impact. PTC can help refine the technical problem statement before submission.
```

### Marketplace Support로 보낼 때

```text
This issue is related to Microsoft Marketplace publishing/certification rather than general architecture guidance. Please open a Partner Center Marketplace support request with the offer ID, plan ID, validation error, screenshots, and current publishing stage. PTC can help clarify the technical context and expected behavior.
```

### UAT / escalation으로 올릴 때

```text
This should be positioned as a business-impacting technical blocker. Before raising a UAT action, confirm the MSX opportunity/milestone, blocked status, customer impact, close date, requested help, and evidence from the support case or partner technical analysis.
```

### Account / CSAM / CSA에 공유할 때

```text
The partner issue has a potential customer/deal impact and may require field alignment. PTC has summarized the technical blocker, current evidence, expected impact, and recommended next support/escalation path for Account/CSAM/CSA review.
```

## 7. PTC의 실질적 파워

PTC는 승인권자가 아니라 연결자다. 다만 다음 3가지를 잘 만들면 영향력이 커진다.

| PTC 산출물 | 왜 중요한가 |
|---|---|
| 정확한 problem statement | Support와 Engineering이 바로 이해할 수 있음 |
| business impact 정리 | Account Team, CSAM, UAT가 움직일 근거가 됨 |
| evidence package | 로그, screenshot, repro, region/SKU, subscription 정보가 있어야 escalation이 막히지 않음 |

## 8. 관련 문서

- [Microsoft 케이스 / 티켓 접수 부서 정리](./ticket-receiving-teams.md)
- [Microsoft 내부 시스템 정리](./internal-systems.md)
- [Microsoft TPD | PTC 직접 기술 지원 케이스](./PTC/README.md)
- [Microsoft ISV Success Program | PTC 기술 자문 케이스](./ISV/README.md)
- [AI Infra (3P GPU) UAT Escalation 정리](./UAT/1.%20GPU.md)

## 9. 핵심 기억

- PTC는 대부분의 문제를 직접 끝내는 부서가 아니라, 올바른 owner로 연결하는 부서다.
- 기술 상담과 architecture guidance는 PTC 선에서 처리 가능하다.
- 제품 수정, 장애 조치, capacity 승인, billing 조정은 PTC 권한 밖이다.
- PTC가 강해지는 순간은 문제를 `technical blocker + business impact + evidence`로 정리했을 때다.
- 연결 대상은 문제 유형에 따라 Support, CSA, Account/CSAM, Marketplace, Capacity, UAT, Engineering으로 달라진다.
