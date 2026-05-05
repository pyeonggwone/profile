# PTC Case Note

## 1. Basic Information

- 담당자명: 윤홍욱
- 케이스명: Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청
- 지원 영역: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center
- 고객 문의 원문: 싱글 테넌트 환경 기준으로 전체 플랫폼 구축 비용(월/연간)을 산정해야 하며, 초기 구축비와 운영비를 분리하여 제시받기를 원함. 기본 구성안과 권장 구성안을 구분하여 제시 요청.
- 우선순위 / Due Date:
- 현재 상태:

## 2. Pre-scoping

- In scope:
  - Monthly and annual cost estimation for all platform components under single-tenant configuration
  - Separation of initial setup cost vs. recurring operational (running) cost
  - Pricing basis: Korea Central region, Pay-As-You-Go; note on Reserved Instance / Savings Plan discount potential
- Out of scope:
  - Cost estimation for application development or deployment labor
  - Networking egress cost (requires actual traffic data)
  - Support plan cost (Basic / Developer / Standard / Premier)
- Assumptions:
  - Pricing based on Korea Central region public PAYG rates as of April 2026
  - Initial setup cost = one-time resource provisioning; operational cost = monthly recurring compute + storage + managed service fees
  - EA/MCA agreement type not yet confirmed — RI savings noted separately
- Dependencies:
  - Agreement type (EA/MCA) for Reserved Instance eligibility
  - Basic vs. recommended configuration scope (see Note 5)
- Risks / Unknowns:
  - GPU-class VM availability in Korea Central may affect RAG pipeline cost estimate
  - LLM token consumption volume unknown — excluded from infrastructure cost estimate

## 3. Scoping

1. Define cost components: VM compute (PAYG), managed disks (Premium SSD v2), PostgreSQL Flexible Server, Blob Storage, Load Balancer / Application Gateway, VNet and public IP (free or minimal)
2. Calculate monthly cost per component per instance, then apply ×2 for HA paired components
3. Separate initial setup items (none for cloud — no upfront hardware cost) vs. monthly recurring operational costs
4. Present basic configuration total (monthly / annual) and recommended configuration total (monthly / annual) side by side
5. Note Reserved Instance (1-year / 3-year) and Azure Savings Plan discount percentages (30–65%) as cost reduction levers

## 4. Requirement Evaluation

고객 문의를 분석하여 다음 핵심 답변 항목을 도출하였습니다.

1. 싱글 테넌트 전체 구성 기준 월 비용 및 연간 비용 총액은?
2. 초기 구축비와 월 운영비를 어떻게 구분하는가?
3. EA/MCA 계약 적용 시 Reserved Instance로 절감 가능한 비용 규모는?
4. 비용 산정에 포함되는 항목과 제외되는 항목은 무엇인가?

## 5. IR Message Draft

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

요청 내용:
싱글 테넌트 환경 기준 전체 플랫폼 구축 비용(월/연간)을 산정하고, 초기 구축비와 운영비를 분리하여 기본/권장 구성안별로 제시받기를 요청하셨습니다.

요구 사항 평가:
- 싱글 테넌트 전체 구성 기준 월 비용 및 연간 비용 총액은?
- 초기 구축비와 월 운영비를 어떻게 구분하는가?
- EA/MCA 계약 적용 시 Reserved Instance로 절감 가능한 비용 규모는?
- 비용 산정에 포함되는 항목과 제외되는 항목은 무엇인가?

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes

### 1. Inquiry Summary

Customer requires a full cost estimate for the single-tenant AI platform on Azure, separated into initial setup and monthly operational costs, with basic and recommended configurations presented separately.

### 2. Confirmed Facts

- Azure cloud has no upfront hardware cost — initial setup cost = provisioning time/labor only; all costs are operational (monthly recurring)
- Korea Central PAYG monthly estimates per component (×1 instance): User Web D4s_v5 ~$140, User WAS E8s_v5 ~$390, Admin WAS D8s_v5 ~$280, RAG WAS E16s_v5 ~$780, PostgreSQL Flexible Server D8ds_v5 ~$560, Blob Storage 3TB ~$56, App Gateway v2 ~$125+
- Reserved Instance (1-year): ~30–40% discount; (3-year): ~50–65% discount vs. PAYG for eligible VM SKUs
- Azure Savings Plan: compute-level discount (up to ~65%) applicable across flexible VM SKUs
- VNet, subnets, and private peering are free; public IP minimal cost (~$3/mo)

### 3. Items Requiring Further Confirmation

- EA or MCA agreement type (determines RI eligibility and purchase process)
- Whether customer wants Reservation cost pre-paid upfront or monthly installment
- Egress bandwidth volume estimate (for network cost inclusion)

### 4. References

https://azure.microsoft.com/en-us/pricing/calculator/
https://learn.microsoft.com/en-us/azure/cost-management-billing/reservations/save-compute-costs-reservations
https://learn.microsoft.com/en-us/azure/cost-management-billing/savings-plan/savings-plan-compute-overview
