# PTC Case Note

## 1. Basic Information

- 담당자명: 윤홍욱
- 케이스명: Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청
- 지원 영역: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center
- 고객 문의 원문: 사내 전사 AI 플랫폼 각 서비스(사용자/관리자 플랫폼 Web·WAS, RAG WAS, RDBMS, Vector DB, 스토리지, LB)별로 고객이 제시한 사양에 맞는 Azure 인프라 구성 및 역할 정의를 요청함.
- 우선순위 / Due Date:
- 현재 상태:

## 2. Pre-scoping
#Pre-scoping
- In scope:
  - Azure VM SKU recommendation for each compute component based on customer-specified vCPU/memory requirements
  - Managed service selection for RDBMS and Storage; Load Balancer option evaluation (L4 vs. L7)
  - Managed disk sizing (Premium SSD) per VM based on customer SSD requirements
- Out of scope:
  - Network security group rules or firewall policy details
  - OS-level or application-level configuration
  - Alternative architectures using containerization (AKS)
- Assumptions:
  - Customer-specified specs are minimum requirements; recommended SKUs may exceed them
  - RDBMS to be deployed as managed service (Azure Database for PostgreSQL Flexible Server)
  - Storage to be Azure Blob Storage (object storage), not file or disk storage
- Dependencies:
  - Target Azure region confirmation (affects SKU availability)
  - Vector DB technology choice (Qdrant / Milvus / pgvector / Cosmos DB)
- Risks / Unknowns:
  - GPU inference requirement for RAG WAS not confirmed
  - SSD type requirement (OS disk vs. data disk) not specified

## 3. Scoping

1. Map each service to recommended Azure VM SKU: User Web → Standard_D4s_v5, User WAS → Standard_E8s_v5, Admin Web → Standard_D4s_v5, Admin WAS → Standard_D8s_v5, RAG WAS → Standard_E16s_v5
2. Define managed disk configuration per VM (OS disk: Standard SSD; data disk: Premium SSD v2 per customer SSD spec)
3. Select RDBMS managed service: Azure Database for PostgreSQL Flexible Server (General Purpose, Standard_D8ds_v5) with Zone-Redundant HA
4. Define Vector DB options: self-managed on Standard_E8s_v5 (Qdrant / Milvus) or Azure Cosmos DB with DiskANN vector index
5. Select Load Balancer: Azure Load Balancer v2 (L4) or Azure Application Gateway v2 (L7/WAF); compare cost and capabilities

## 4. Requirement Evaluation

고객 문의를 분석하여 다음 핵심 답변 항목을 도출하였습니다.

1. 각 서비스별 고객 요구 사양에 매핑되는 Azure VM SKU는?
2. RDBMS는 IaaS VM과 관리형 서비스(PostgreSQL Flexible Server) 중 무엇이 적합한가?
3. Vector DB는 자체 관리형(IaaS)과 완전 관리형(Cosmos DB) 중 어떤 구성을 선택해야 하는가?
4. Load Balancer는 L4(Azure LB)와 L7(Application Gateway) 중 어떤 것이 적합한가?

## 5. IR Message Draft

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

요청 내용:
각 서비스(사용자/관리자 플랫폼 Web·WAS, RAG WAS, RDBMS, Vector DB, 스토리지, LB)별로 고객이 제시한 사양에 맞는 Azure 인프라 구성 및 역할 정의를 요청하셨습니다.

요구 사항 평가:
- 각 서비스별 고객 요구 사양에 매핑되는 Azure VM SKU는?
- RDBMS는 IaaS VM과 관리형 서비스(PostgreSQL Flexible Server) 중 무엇이 적합한가?
- Vector DB는 자체 관리형(IaaS)과 완전 관리형(Cosmos DB) 중 어떤 구성을 선택해야 하는가?
- Load Balancer는 L4(Azure LB)와 L7(Application Gateway) 중 어떤 것이 적합한가?

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes
#Research
### 1. Inquiry Summary

Customer has specified exact vCPU/memory/storage requirements per service. The request is to map these to appropriate Azure VM SKUs and managed services, and define the role of each component in the overall architecture.

### 2. Confirmed Facts

- User Platform Web (4vCPU/16GB): Standard_D4s_v5 — general-purpose; ~$140/mo per instance (Korea Central, PAYG)
- User Platform WAS (8vCPU/64GB): Standard_E8s_v5 — memory-optimized; ~$390/mo per instance
- Admin Platform Web (4vCPU/16GB): Standard_D4s_v5
- Admin Platform WAS (8vCPU/32GB): Standard_D8s_v5 — general-purpose; ~$280/mo per instance
- RAG Data Pipeline WAS (16vCPU/128GB): Standard_E16s_v5 — memory-optimized; ~$780/mo per instance; upgrade to Standard_NC24ads_A100_v4 if GPU inference required
- RDBMS (8vCPU/32GB): Azure Database for PostgreSQL Flexible Server (Standard_D8ds_v5) — Zone-Redundant HA, PITR, auto-failover
- Vector DB (8vCPU/32GB): Standard_E8s_v5 (Qdrant/Milvus self-managed) or Azure Cosmos DB with DiskANN vector index
- Storage (3TB): Azure Blob Storage Hot tier — ~$0.018/GB/mo; ~$56/mo base; auto-scales with usage
- Load Balancer: Azure Load Balancer L4 (~$18/mo) or Application Gateway v2 L7/WAF (~$125/mo base)

### 3. Items Requiring Further Confirmation

- Is GPU inference required at the RAG pipeline tier? (Determines whether E16s_v5 or NC-series VM is needed)
- Vector DB technology preference (Qdrant, Milvus, pgvector, or managed Cosmos DB)?
- SSD requirement: OS disk only, or separate high-performance data disk (Premium SSD v2)?

### 4. References

https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/
https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/overview
https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction
https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-overview
https://learn.microsoft.com/en-us/azure/application-gateway/overview
