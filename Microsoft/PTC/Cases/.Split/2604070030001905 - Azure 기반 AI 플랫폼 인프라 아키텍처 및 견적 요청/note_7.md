# PTC Case Note

## 1. Basic Information

- 담당자명: 윤홍욱
- 케이스명: Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청
- 지원 영역: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center
- 고객 문의 원문: 각 서비스에 Scale-up을 적용할 경우 초기 제안 스펙 대비 확장 가능한 최대 권장 사양이 어느 수준인지, 단계별 업그레이드에 따라 비용이 어떤 구조로 증가하는지 파악이 필요하다.
- 우선순위 / Due Date:
- 현재 상태:

## 2. Pre-scoping

- In scope:
  - Maximum recommended VM SKU per compute service (User Web/WAS, Admin Web/WAS, RAG WAS, RDBMS, Vector DB)
  - Step-by-step cost increment structure for Scale-up within each VM series
  - Special consideration for RAG WAS GPU migration path (E-series → NC-series)
- Out of scope:
  - Scale-out (horizontal) cost modeling for compute (covered in Note 6 / Note 9)
  - Storage Scale-up (not applicable — Blob Storage is Scale-out only)
  - Cost modeling for AKS or containerized workloads
- Assumptions:
  - Scale-up stays within the same Azure VM series where possible
  - Maximum recommended SKU is the largest SKU before cost-efficiency diminishes or GPU migration becomes preferable
  - Cost estimates are Korea Central PAYG; RI savings noted separately
- Dependencies:
  - Baseline VM SKUs from Note 2
  - GPU inference requirement confirmation for RAG WAS
- Risks / Unknowns:
  - Some large SKUs (E32s_v5, NC-series) may have limited availability in Korea Central — requires quota check

## 3. Scoping

1. Map Scale-up path per service: User/Admin Web D4s_v5 → D8s_v5 → D16s_v5 → D32s_v5; User WAS E8s_v5 → E16s_v5 → E32s_v5; Admin WAS D8s_v5 → D16s_v5 → D32s_v5
2. RAG WAS Scale-up: E16s_v5 → E32s_v5 (CPU-only path); GPU path: Standard_NC24ads_A100_v4 (24vCPU / 220GB / A100 40GB GPU, ~$3,600/mo per instance)
3. RDBMS (PostgreSQL Flexible Server) Scale-up: Standard_D8ds_v5 → D16ds_v5 → D32ds_v5 → D64ds_v5
4. Vector DB Scale-up (self-managed): E8s_v5 → E16s_v5 → E32s_v5; monthly cost approximately doubles at each step
5. Define maximum recommended SKU as largest E-series or D-series before switching to specialty (GPU/HPC) class; cost increment is ~2× per vCPU doubling step (PAYG)

## 4. Requirement Evaluation

고객 문의를 분석하여 다음 핵심 답변 항목을 도출하였습니다.

1. 각 서비스별 Scale-up 시 추청 가능한 최대 권장 VM SKU는?
2. SKU 단계 업그레이드에 따른 월 비용 증가율은 어떻게 되는가?
3. RAG WAS에서 CPU 기반 Scale-up과 GPU VM 전환은 어떤 기준으로 선택하는가?
4. RDBMS Scale-up 시 복제본(read replica) 없이 단독으로 충분한가?

## 5. IR Message Draft

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

요청 내용:
각 서비스에 Scale-up 적용 시 최대 권장 사양 및 단계별 비용 증가 구조에 대한 안내를 요청하셨습니다.

요구 사항 평가:
- 각 서비스별 Scale-up 시 추청 가능한 최대 권장 VM SKU는?
- SKU 단계 업그레이드에 따른 월 비용 증가율은 어떻게 되는가?
- RAG WAS에서 CPU 기반 Scale-up과 GPU VM 전환은 어떤 기준으로 선택하는가?
- RDBMS Scale-up 시 복제본(read replica) 없이 단독으로 충분한가?

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes

### 1. Inquiry Summary

Customer needs to understand the maximum Scale-up ceiling per service and the associated cost increment per step. This enables budget planning for future capacity growth.

### 2. Confirmed Facts

- User/Admin Platform Web (D4s_v5 base): max recommended D32s_v5 (32vCPU/128GB); cost progression: ~$140 → ~$280 → ~$560 → ~$1,120/mo per instance
- User Platform WAS (E8s_v5 base): max recommended E32s_v5 (32vCPU/256GB); cost progression: ~$390 → ~$780 → ~$1,560/mo per instance
- RAG WAS (E16s_v5 base): E32s_v5 (~$1,560/mo) as CPU max; GPU upgrade to Standard_NC24ads_A100_v4 (~$3,600/mo per instance) if inference workload requires GPU acceleration
- RDBMS PostgreSQL Flexible Server: D8ds_v5 → D16ds_v5 → D32ds_v5 → D64ds_v5; costs approximately double at each step
- Cost increment rule: each vCPU doubling step within same series = ~2× monthly cost (PAYG); RI discount ratio remains consistent across SKU sizes

### 3. Items Requiring Further Confirmation

- GPU inference requirement for RAG WAS (determines whether NC-series quota needed in Korea Central)
- Large SKU availability in Korea Central: E32s_v5, D32s_v5 — require subscription quota check
- Customer's performance headroom target (determines at what utilization threshold to trigger Scale-up)

### 4. References

https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/memory-optimized/
https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/
https://azure.microsoft.com/en-us/pricing/calculator/
https://learn.microsoft.com/en-us/azure/virtual-machines/resize-vm
