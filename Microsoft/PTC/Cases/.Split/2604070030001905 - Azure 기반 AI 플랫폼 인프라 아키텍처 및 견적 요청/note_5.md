# PTC Case Note

## 1. Basic Information

- 담당자명: 윤홍욱
- 케이스명: Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청
- 지원 영역: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center
- 고객 문의 원문: 고객이 제시한 사양을 기본 구성안으로 하고, 안정성·보안을 강화한 권장 구성안을 별도 제시하여 두 구성안 간 사양, 비용(월/연간), 가용성 수준의 차이를 비교하여 제시 요청.
- 우선순위 / Due Date:
- 현재 상태:

## 2. Pre-scoping

- In scope:
  - Basic configuration: customer-specified minimum specs, Azure Load Balancer L4, PostgreSQL single-AZ, Blob Storage LRS
  - Recommended configuration: memory-optimized SKUs, Application Gateway v2 (L7/WAF), PostgreSQL Zone-Redundant HA, Blob Storage ZRS, all VMs across AZ1/AZ2
  - Side-by-side cost comparison (monthly / annual) and SLA delta between both configurations
- Out of scope:
  - Custom hybrid configurations beyond the two defined options
  - Application-layer performance benchmarking
  - Third-party monitoring or security tooling costs
- Assumptions:
  - Basic config = customer specs as stated (minimum); recommended config = Microsoft best-practice additions
  - Both configurations use Korea Central region PAYG pricing
  - Recommended config adds zone-redundancy and WAF without changing core component count
- Dependencies:
  - Final VM SKU mapping from Note 2 (service spec → Azure SKU)
  - HA design from Note 3 (AZ placement details)
- Risks / Unknowns:
  - Customer budget ceiling not specified — may affect which recommendation tier is viable

## 3. Scoping

1. Define Basic configuration: minimum VM SKUs per customer spec, Azure Load Balancer (L4, ~$18/mo), PostgreSQL Flexible Server single-AZ (no standby), Blob Storage LRS
2. Define Recommended configuration: memory-optimized VM SKUs (E-series where applicable), Application Gateway v2 (L7/WAF, ~$125/mo+), PostgreSQL Zone-Redundant HA (+~30% premium), Blob Storage ZRS (+~25% vs. LRS)
3. Calculate monthly cost totals for both configurations; apply ×2 for all HA paired compute components
4. Present annual cost totals and show RI/Savings Plan discount potential for both configurations
5. Summarize SLA improvement from basic to recommended: LB 99.95% → 99.99%; RDBMS single-AZ → Zone-HA 99.99%; Storage LRS 99.9% → ZRS 99.9% (3-AZ durability)

## 4. Requirement Evaluation

고객 문의를 분석하여 다음 핵심 답변 항목을 도출하였습니다.

1. 기본 구성안과 권장 구성안의 VM SKU 및 서비스 구성 상의 차이는?
2. 두 구성안 간 월/연간 비용 차이는 얼마나 하는가?
3. SLA(가용성 보장 수준) 측면에서 권장 구성안은 기본 구성안대비 얼마나 향상되는가?
4. 예산 제약 시 어떤 항목에서 트레이드오프가 발생하는가?

## 5. IR Message Draft

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

요청 내용:
기본 구성안(고객 제시 사양 기준)과 권장 구성안(관리형 HA 포함)의 사양, 비용, SLA 수준 비교를 요청하셨습니다.

요구 사항 평가:
- 기본 구성안과 권장 구성안의 VM SKU 및 서비스 구성 상의 차이는?
- 두 구성안 간 월/연간 비용 차이는 얼마나 하는가?
- SLA 측면에서 권장 구성안은 기본 구성안대비 얼마나 향상되는가?
- 예산 제약 시 어떤 항목에서 트레이드오프가 발생하는가?

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes

### 1. Inquiry Summary

Customer requested two configuration options. Basic configuration follows the customer's stated minimum specs. Recommended configuration adds managed HA, WAF, and zone-redundant storage to maximize availability and security with associated cost increase.

### 2. Confirmed Facts

- Basic config differences vs. recommended: LB → Azure LB L4 (basic) vs. App Gateway v2 WAF (recommended); RDBMS → single-AZ (basic) vs. Zone-Redundant HA (recommended); Storage → LRS (basic) vs. ZRS (recommended)
- PostgreSQL Zone-Redundant HA adds ~30% cost premium over single-AZ deployment
- Azure Blob Storage ZRS pricing: approximately 25% higher than LRS per GB
- Application Gateway v2 WAF SKU: ~$125/mo base + Capacity Units; significantly higher than Azure LB L4 (~$18/mo) but adds L7 routing, SSL termination, and WAF protection
- SLA improvement: Azure LB zone-redundant = 99.99%; PostgreSQL Zone-HA = 99.99%; Blob ZRS = 99.9% availability (vs. 99.9% LRS, but 3-AZ durability)

### 3. Items Requiring Further Confirmation

- Customer's budget ceiling (determines whether recommended config is feasible)
- WAF requirement: is Layer 7 inspection and WAF policy a security/compliance requirement?
- Whether RI/Savings Plan discounts should be applied in the comparison table

### 4. References

https://azure.microsoft.com/en-us/pricing/calculator/
https://learn.microsoft.com/en-us/azure/storage/common/storage-redundancy
https://learn.microsoft.com/en-us/azure/application-gateway/overview
https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-high-availability
