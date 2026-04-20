# PTC Case Note

## 1. Basic Information

- 담당자명: 윤홍욱
- 케이스명: Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청
- 지원 영역: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center
- 고객 문의 원문: Data Storage(3TB 기본)의 용량이 증가할 경우 Auto Scaling 조건 하에서 용량 증가에 따른 비용 구조(단가, 구간별 차이 등)가 어떻게 되는지 파악이 필요하다.
- 우선순위 / Due Date:
- 현재 상태:

## 2. Pre-scoping

- In scope:
  - Azure Blob Storage pricing structure by capacity tier (Hot, Cool, Archive) and replication option (LRS, ZRS, GRS)
  - Auto-scaling model explanation: no pre-provisioning, pay-per-actual-use
  - Cost projection at key capacity milestones (3TB, 10TB, 50TB, 100TB)
- Out of scope:
  - Azure Files or Azure Managed Disk (not applicable — customer specified object storage)
  - CDN or caching layer costs
  - Data transfer / egress pricing (requires actual usage pattern data)
- Assumptions:
  - Storage type: Azure Blob Storage (object storage) as specified
  - Data access pattern: primary workload uses Hot tier; Cool/Archive tiers noted for lifecycle management
  - Replication: ZRS recommended (see Note 5); LRS noted as basic option
- Dependencies:
  - Replication tier decision (LRS vs. ZRS) from Note 3 / Note 5
  - Data access frequency pattern from customer (determines tier mix)
- Risks / Unknowns:
  - Actual data growth rate unknown — projections are illustrative
  - LLM training data or embedding storage volume not included in base 3TB estimate

## 3. Scoping

1. Explain Azure Blob Storage auto-scaling: capacity grows automatically with data written; no provisioning step; billing is per GB stored per month
2. Define Hot tier pricing: ~$0.018/GB/mo (Korea Central, LRS); ZRS: ~$0.023/GB/mo; calculate cost at 3TB, 10TB, 50TB, 100TB milestones
3. Define Cool tier pricing: ~$0.01/GB/mo storage + $0.01/10,000 read operations; suitable for data accessed less than once per month
4. Define Archive tier pricing: ~$0.002/GB/mo storage; rehydration to Hot/Cool required before access (hours to ~15 hours latency)
5. Recommend lifecycle management policy: auto-transition blobs from Hot → Cool after 30 days inactive, Hot/Cool → Archive after 90 days, to optimize cost as data grows

## 4. Requirement Evaluation

고객 문의를 분석하여 다음 핵심 답변 항목을 도출하였습니다.

1. Azure Blob Storage의 Auto Scaling은 어떻게 동작하며 별도 조작 없이 용량이 자동 증가하는가?
2. 용량 증가에 따른 비용 증가 구조는 단순 비례인가, 구간별 단가 변동이 있는가?
3. Hot / Cool / Archive 티어별 단가 차이는 얼마이며, 데이터 접근 매턴에 따라 어떤 티어를 선택하는게 적합한가?
4. LRS와 ZRS 관리형 옵션 간 비용 차이는?

## 5. IR Message Draft

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

요청 내용:
Data Storage(3TB 기본) 용량 증가 시 Auto Scaling 조건 하에서 비용 구조 안내를 요청하셨습니다.

요구 사항 평가:
- Azure Blob Storage의 Auto Scaling은 어떻게 동작하며 별도 조작 없이 용량이 자동 증가하는가?
- 용량 증가에 따른 비용 증가 구조는 단순 비례인가, 구간별 단가 변동이 있는가?
- Hot / Cool / Archive 티어별 단가 차이는 얼마이며, 데이터 접근 매턴에 따라 어떤 티어를 선택하는게 적합한가?
- LRS와 ZRS 관리형 옵션 간 비용 차이는?

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes

### 1. Inquiry Summary

Customer's storage starts at 3TB and grows via Scale-out (auto-scaling). This note details Azure Blob Storage's automatic capacity expansion mechanism and the cost structure by capacity milestone and tier.

### 2. Confirmed Facts

- Azure Blob Storage: no pre-provisioning needed; capacity grows automatically as data is written; billing is per GB actually stored per month
- Hot tier (Korea Central, LRS): ~$0.018/GB/mo — 3TB: ~$56/mo, 10TB: ~$184/mo, 50TB: ~$922/mo, 100TB: ~$1,843/mo
- Hot tier ZRS: ~$0.023/GB/mo — 3TB: ~$72/mo, 10TB: ~$235/mo
- Cool tier (LRS): ~$0.01/GB/mo storage + $0.0025 per read operation/10,000 — suitable for data accessed < once/month
- Archive tier (LRS): ~$0.002/GB/mo storage; rehydration to Hot = ~1 hour; to Cool = ~15 hours; rehydration charged separately
- Lifecycle management policy: automate Hot → Cool (30d inactive) → Archive (90d) transitions to minimize cost as data grows

### 3. Items Requiring Further Confirmation

- Estimated annual data growth rate (needed for 3-year cost projection)
- Data access frequency per data category (determines tier mix and lifecycle rule design)
- Whether compliance requires data to remain in Hot tier (affects lifecycle policy)

### 4. References

https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction
https://azure.microsoft.com/en-us/pricing/details/storage/blobs/
https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-overview
