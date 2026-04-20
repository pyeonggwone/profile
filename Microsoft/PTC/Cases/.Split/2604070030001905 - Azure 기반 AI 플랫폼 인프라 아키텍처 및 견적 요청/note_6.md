# PTC Case Note

## 1. Basic Information

- 담당자명: 윤홍욱
- 케이스명: Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청
- 지원 영역: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center
- 고객 문의 원문: 향후 사용자 수 및 처리량 증가에 대응하기 위해 개 서비스별로 어떤 확장 전략(Scale-up 또는 Scale-out)이 적합한지 기준과 방향성에 대한 정의가 필요하다. 고객이 명시한 기준: Storage는 Scale-out, 그 외 모든 서비스(Web/WAS/RAG/RDBMS/Vector DB)는 Scale-up.
- 우선순위 / Due Date:
- 현재 상태:

## 2. Pre-scoping

- In scope:
  - Scale-up strategy definition for all compute services (User Web/WAS, Admin Web/WAS, RAG WAS, RDBMS, Vector DB)
  - Scale-out strategy definition for Storage (Azure Blob Storage auto-scaling model)
  - Trigger criteria and process overview per service expansion type
- Out of scope:
  - Kubernetes-based horizontal pod autoscaling (AKS)
  - Application-level load testing or performance profiling
  - Multi-region scale-out (geo-distribution)
- Assumptions:
  - Customer has confirmed Scale-up for all compute, Scale-out for Storage only
  - RDBMS read replica option noted as supplementary horizontal option for read-heavy workloads
  - All Scale-up transitions are within the same Azure VM series
- Dependencies:
  - Initial VM SKU baseline from Note 2
  - Storage architecture confirmed as Azure Blob Storage
- Risks / Unknowns:
  - Scale-up requires VM restart — planned maintenance window needed; HA configuration mitigates downtime risk

## 3. Scoping

1. Define Scale-up path per compute service: upgrade within same VM series (D-series → larger D; E-series → larger E) to double vCPU and memory at each step
2. Define Scale-out model for Azure Blob Storage: consumption-based auto-scaling, no pre-provisioning required, cost increases linearly with used capacity
3. Note RDBMS supplementary Scale-out option: add read replica(s) to PostgreSQL Flexible Server for read-heavy query offloading without changing primary VM SKU
4. Define Vector DB Scale-up path: if self-managed (IaaS), upgrade E8s_v5 to E16s_v5/E32s_v5; if Cosmos DB, RU (Request Unit) auto-scaling is native
5. Summarize trigger criteria for each scale event: CPU utilization >70% sustained, memory pressure, storage capacity >80%

## 4. Requirement Evaluation

고객 문의를 분석하여 다음 핵심 답변 항목을 도출하였습니다.

1. Storage를 Scale-out으로 지정한 이유는 무엇이며, Azure Blob Storage에서 어떻게 자동 Scale-out이 동작하는가?
2. 각 컴퓨팅 서비스에 Scale-up을 적용하는 시점과 기준은?
3. RDBMS Scale-out(읽기 복제본)는 Scale-up과 어떻게 병용할 수 있는가?
4. Scale-up 전환 시 서비스 중단 없이 진행할 수 있는가?

## 5. IR Message Draft

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

요청 내용:
서비스별 확장 전략(Storage: Scale-out, 그 외: Scale-up) 기준과 방향성에 대한 정의를 요청하셨습니다.

요구 사항 평가:
- Storage를 Scale-out으로 지정한 이유는 무엇이며, Azure Blob Storage에서 어떻게 자동 Scale-out이 동작하는가?
- 각 컴퓨팅 서비스에 Scale-up을 적용하는 시점과 기준은?
- RDBMS Scale-out(읽기 복제본)는 Scale-up과 어떻게 병용할 수 있는가?
- Scale-up 전환 시 서비스 중단 없이 진행할 수 있는가?

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes

### 1. Inquiry Summary

Customer has specified that Storage uses Scale-out and all other services (Web, WAS, RAG, RDBMS, Vector DB) use Scale-up. This note defines the expansion strategy per service type including trigger criteria and process.

### 2. Confirmed Facts

- Azure Blob Storage Scale-out: fully automatic, consumption-based; no pre-provisioning or manual intervention; cost increases linearly with used GB
- Compute Scale-up: VM must be deallocated and resized; takes ~3–5 minutes; in AZ HA setup, rolling upgrade possible (upgrade one AZ at a time) to minimize impact
- RDBMS (PostgreSQL Flexible Server) Scale-up: compute tier change requires brief restart (~2–3 min); Zone-HA failover handles continuity
- RDBMS supplementary Scale-out: add read replica(s) — no primary downtime; replicas are async; useful for read-heavy analytics or reporting queries
- Vector DB self-managed Scale-up: standard IaaS VM resize process; Cosmos DB uses RU auto-scale which adjusts capacity dynamically without downtime

### 3. Items Requiring Further Confirmation

- Maintenance window availability for planned Scale-up events (VM restart)
- Maximum acceptable response time degradation during Scale-up resizing period
- Whether RDBMS read replica is desired as a planned scale-out option from the start

### 4. References

https://learn.microsoft.com/en-us/azure/virtual-machines/resize-vm
https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction
https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-read-replicas
