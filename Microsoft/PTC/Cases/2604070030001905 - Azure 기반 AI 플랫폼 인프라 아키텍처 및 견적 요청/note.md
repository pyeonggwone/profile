# PTC Case Note

## 1. Basic Information

- 담당자명: 윤홍욱
- 케이스명: Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청
- 지원 영역: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center
- 고객 문의 원문: 사내 전사 AI 플랫폼(사용자/관리자 플랫폼, RAG 데이터 파이프라인, RDBMS, Vector DB, 스토리지)의 Azure 클라우드 도입 검토. 싱글 테넌트 기준 전체 구축 비용(월/연간, 기본/권장 구성 분리), Active-Active HA 구조, Scale-up/Scale-out 전략, 외부 LLM 파트너 비용·보안·장점 비교 요청.
- 우선순위 / Due Date:
- 현재 상태:

## 2. Pre-scoping

- In scope:
  - Azure infrastructure sizing and cost estimation for all specified components (User/Admin Web+WAS, RAG WAS, RDBMS, Vector DB, Storage, LB) under single-tenant, Active-Active HA configuration
  - Scale-up path and cost model per compute service; Scale-out cost structure for storage
  - Azure-integrated LLM partner comparison (cost, security, key advantages)
- Out of scope:
  - On-premises or hybrid deployment scenarios
  - Multi-tenant architecture design
  - Application code review, CI/CD pipelines, or implementation support
- Assumptions:
  - Single-tenant Azure environment (dedicated subscription and VNet)
  - All ×2 paired servers require Active-Active HA across Azure Availability Zones
  - Storage expansion follows Scale-out; all compute services follow Scale-up
- Dependencies:
  - Target Azure region confirmation from customer
  - EA/MCA agreement type (affects Reserved Instance and savings plan eligibility)
  - LLM partner shortlist or preference from customer
- Risks / Unknowns:
  - GPU-class VM SKU availability varies by region — relevant for RAG pipeline if GPU inference is needed
  - LLM token consumption patterns not yet defined — cost estimates will be approximate
  - Data residency, compliance, or regulatory requirements not yet specified

## 3. Scoping

1. **VM sizing and cost estimation** for all compute tiers — User Platform Web (Standard_D4s_v5 ×2), User Platform WAS (Standard_E8s_v5 ×2), Admin Web (Standard_D4s_v5 ×2), Admin WAS (Standard_D8s_v5 ×2), RAG Data Pipeline WAS (Standard_E16s_v5 ×2), RDBMS (Azure Database for PostgreSQL Flexible Server, Standard_E8ds_v5 ×2), Vector DB (Standard_E8s_v5 ×2); monthly and annual cost, basic vs. recommended configuration
2. **Storage architecture** — Azure Blob Storage 3TB base (Hot tier, ~$0.018/GB/mo) with native auto-scaling; Scale-out cost structure by capacity tier; managed disk sizing for per-VM SSD requirements
3. **Load Balancer options** — Azure Load Balancer (L4, zone-redundant, ~$18/mo base) vs. Azure Application Gateway v2 (L7/WAF, zone-redundant, ~$125/mo base); HA behavior and cost comparison
4. **Active-Active HA architecture** — cross-zone deployment (AZ1/AZ2) for all paired VMs; zone-redundant managed services (PostgreSQL Flexible Server zone-redundant HA, Cosmos DB multi-zone, zone-redundant Blob Storage); failover scope and SLA
5. **LLM partner comparison on Azure** — Azure OpenAI (GPT-4o), Meta Llama 3.3 70B, Mistral Large 2, Cohere Command R+ via Azure AI Foundry; per-token pricing, security posture, compliance (data residency), and RAG use-case strengths

## 4. Requirement Evaluation

고객 문의를 분석하여 다음 핵심 답변 항목을 도출하였습니다.

1. Azure 기반 전사 AI 플랫폼 컴포넌트별 권장 VM SKU 및 관리형 서비스 구성은?
2. 싱글 테넌트 기준 월/연간 총 견적 — 기본 구성 대비 권장 구성 비교
3. Active-Active 고가용성 구조 설계 방안 및 가용성 보장 수준 (SLA)
4. 서비스별 Scale-up 최대 권장 사양 및 단계별 비용 증가 구조
5. Storage Scale-out 시 용량 증가에 따른 비용 구조
6. Azure 연계 외부 LLM 파트너 목록 및 비용 · 보안 · 장점 비교

## 5. IR Message Draft

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

요청 내용:
사내 전사 AI 플랫폼(사용자/관리자 플랫폼, RAG 데이터 파이프라인, RDBMS, Vector DB, 스토리지)의 Azure 클라우드 도입 검토. 싱글 테넌트 기준 전체 구축 비용(월/연간, 기본/권장 구성 분리), Active-Active HA 구조, Scale-up/Scale-out 전략, 외부 LLM 파트너 비용·보안·장점 비교를 요청하였습니다.

요구 사항 평가:
- Azure 기반 전사 AI 플랫폼 컴포넌트별 권장 VM SKU 및 관리형 서비스 구성은?
- 싱글 테넌트 기준 월/연간 총 견적 — 기본 구성 대비 권장 구성 비교
- Active-Active 고가용성 구조 설계 방안 및 가용성 보장 수준 (SLA)
- 서비스별 Scale-up 최대 권장 사양 및 단계별 비용 증가 구조
- Storage Scale-out 시 용량 증가에 따른 비용 구조
- Azure 연계 외부 LLM 파트너 목록 및 비용 · 보안 · 장점 비교

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes

### 1. Inquiry Summary

The customer is evaluating Azure as the cloud platform for an enterprise-wide AI system comprising web/app-tier services, a RAG data pipeline, RDBMS, vector DB, and object storage. They need VM sizing recommendations, single-tenant cost estimates (basic vs. recommended, monthly/annual), Active-Active HA architecture guidance, scale-up/out cost models, and a comparative analysis of Azure-integrated LLM partners.

### 2. Confirmed Facts

**VM SKU Recommendations (per Azure documentation):**
- User Platform Web (4vCPU / 16GB): Standard_D4s_v5 — general-purpose; ~$140/mo per instance (Korea Central, pay-as-you-go)
- User Platform WAS (8vCPU / 64GB): Standard_E8s_v5 — memory-optimized; ~$390/mo per instance
- Admin Platform Web (4vCPU / 16GB): Standard_D4s_v5
- Admin Platform WAS (8vCPU / 32GB): Standard_D8s_v5 — general-purpose; ~$280/mo per instance
- RAG Data Pipeline WAS (16vCPU / 128GB): Standard_E16s_v5 — memory-optimized; ~$780/mo per instance; upgrade to Standard_NC24ads_A100_v4 if GPU inference is required
- RDBMS (8vCPU / 32GB): Azure Database for PostgreSQL Flexible Server (General Purpose, Standard_D8ds_v5) — supports Zone-Redundant HA, automatic failover, PITR backup
- Vector DB (8vCPU / 32GB): Self-managed on Standard_E8s_v5 (Qdrant / Milvus / pgvector) or Azure Cosmos DB with DiskANN vector index (fully managed)

**Storage:**
- Azure Blob Storage (Hot tier): ~$0.018/GB/mo → 3TB base ≈ $56/mo; scales automatically with no pre-provisioning (native Scale-out)
- Premium SSD v2 (per-VM data disk): provisioned IOPS/throughput model; cost varies by disk size and performance tier

**Load Balancer:**
- Azure Load Balancer (L4, zone-redundant): ~$18/mo base + $0.005/GB processed — simple TCP/UDP routing
- Azure Application Gateway v2 (L7, WAF-enabled, zone-redundant): ~$125/mo base + Capacity Unit fee — HTTP/HTTPS routing, SSL offload, WAF protection; recommended for web-tier

**Active-Active HA:**
- Deploy paired VMs across Availability Zone 1 and Zone 2 within the same region
- Azure Load Balancer / Application Gateway provides zone-redundant frontend with 99.99% SLA
- Azure Database for PostgreSQL Flexible Server Zone-Redundant HA: synchronous standby in separate AZ, automatic failover within ~60–120 sec, 99.99% SLA
- Azure Blob Storage: Zone-Redundant Storage (ZRS) replicates across 3 AZs — 99.9999999999% durability, 99.9% read availability SLA

**LLM Partner Comparison (via Azure AI Foundry / Azure OpenAI):**

| Model | Provider | Input Price | Output Price | Security / Compliance | RAG Strength |
|---|---|---|---|---|---|
| GPT-4o | Azure OpenAI | $2.50 / 1M tokens | $10.00 / 1M tokens | Highest — data stays in Azure, SOC2/ISO27001/HIPAA | Excellent |
| Llama 3.3 70B | Meta (AI Foundry) | ~$0.23 / 1M tokens | ~$0.77 / 1M tokens | Open-source; self-hostable for full data control | Good |
| Mistral Large 2 | Mistral (AI Foundry) | ~$2.00 / 1M tokens | ~$6.00 / 1M tokens | European provider, GDPR-first, EU data residency | Good — strong multilingual |
| Command R+ | Cohere (AI Foundry) | ~$0.50 / 1M tokens | ~$1.50 / 1M tokens | Enterprise-grade; Azure-managed endpoint | Excellent — RAG-optimized |

### 3. Items Requiring Further Confirmation

- Which Azure region is targeted? (Korea Central or Korea South — affects VM SKU availability, especially GPU class, and pricing)
- Are there data residency, regulatory, or compliance requirements (ISMS, ISO 27001, government cloud)?
- Is the customer under an Enterprise Agreement (EA) or Microsoft Customer Agreement (MCA)? (Reserved Instances and Azure Savings Plans can reduce VM cost by 30–65%)
- Is LLM inference (GPU) required at the RAG pipeline tier, or is it CPU-only embedding/retrieval workload?
- Will Vector DB be self-managed (Qdrant/Milvus) or a managed Azure service (Cosmos DB)?

### 4. References

https://azure.microsoft.com/en-us/blog/announcing-azure-copilot-agents-and-ai-infrastructure-innovations/
https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/
https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/overview
https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-overview
https://learn.microsoft.com/en-us/azure/application-gateway/overview
https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction
https://learn.microsoft.com/en-us/azure/ai-foundry/
https://learn.microsoft.com/en-us/azure/ai-services/openai/overview
https://azure.microsoft.com/en-us/pricing/calculator/
