# PTC Case Note

## 1. Basic Information

- 담당자명: 윤홍욱
- 케이스명: Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청
- 지원 영역: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center
- 고객 문의 원문: 향후 사용자 수 및 처리량 증가 시 각 서비스 계층별로 어떤 순서와 방식으로 인프라를 증설·확장해야 하는지 구체적인 시나리오 파악이 필요하다.
- 우선순위 / Due Date:
- 현재 상태:

## 2. Pre-scoping

- In scope:
  - Growth scenarios: user count increase, RAG processing throughput increase, data volume increase
  - Per-scenario expansion sequence covering all affected service tiers (Web, WAS, RAG, RDBMS, Vector DB, Storage, LB)
  - Operational considerations for Scale-up events in HA configuration (rolling upgrade, maintenance window)
- Out of scope:
  - Auto-scaling policies or Azure Monitor alert rule configuration
  - Application performance load testing methodology
  - Multi-region expansion (geo-distribution)
- Assumptions:
  - Growth scenarios are independent; customer can combine them as needed
  - All Scale-up for compute follows the path defined in Note 7
  - Storage Scale-out is automatic (no action needed for Blob Storage)
- Dependencies:
  - Scale-up paths from Note 7; expansion strategy from Note 6
  - HA design from Note 3 (rolling upgrade relies on AZ pair setup)
- Risks / Unknowns:
  - VM Scale-up requires brief restart; minimize impact via rolling AZ upgrade in HA setup
  - Exact growth triggers (user count thresholds) not yet specified by customer

## 3. Scoping

1. Scenario A — User count doubles: Scale-up User Platform Web (D4s_v5 → D8s_v5) and WAS (E8s_v5 → E16s_v5), one AZ at a time; Application Gateway CU auto-adjusts
2. Scenario B — RAG throughput increases: Scale-up RAG WAS (E16s_v5 → E32s_v5); if GPU inference needed, migrate to NC24ads_A100_v4; Scale-up Vector DB VMs in parallel
3. Scenario C — Data volume increases: Blob Storage auto-scales (no action); evaluate RDBMS performance — if read-heavy, add PostgreSQL read replica; if write-heavy, Scale-up RDBMS VM SKU
4. Rolling upgrade procedure for compute Scale-up in HA (AZ1/AZ2): deregister AZ1 VM from LB → resize AZ1 VM → verify → re-register AZ1 → repeat for AZ2
5. Recommended trigger thresholds: CPU >70% sustained 15 min, memory >80%, disk I/O at cap → initiate next Scale-up step

## 4. Requirement Evaluation

고객 문의를 분석하여 다음 핵심 답변 항목을 도출하였습니다.

1. 사용자 수가 두 배로 늘어났을 때 가장 먼저 확장이 필요한 서비스 계층은?
2. RAG 처리 데이터 양이 증가할 때 WAS와 Vector DB를 어떤 순서로 확장하는가?
3. 데이터 용량 증가 시 Storage는 자동 대응되지만 RDBMS는 언제 조치가 필요한가?
4. HA 구성에서 Scale-up 메인터넌스를 서비스 중단 없이 진행하는 절차는?

## 5. IR Message Draft

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

요청 내용:
향후 사용자 수 및 처리량 증가 시 각 서비스 계층별 인프라 증설·확장 시나리오 안내를 요청하셨습니다.

요구 사항 평가:
- 사용자 수가 두 배로 늘어났을 때 가장 먼저 확장이 필요한 서비스 계층은?
- RAG 처리 데이터 양이 증가할 때 WAS와 Vector DB를 어떤 순서로 확장하는가?
- 데이터 용량 증가 시 Storage는 자동 대응되지만 RDBMS는 언제 조치가 필요한가?
- HA 구성에서 Scale-up 메인터넌스를 서비스 중단 없이 진행하는 절차는?

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes

### 1. Inquiry Summary

Customer needs concrete scale-out and scale-up scenarios per growth trigger. This note covers three growth scenarios (user count, RAG throughput, data volume) and defines the per-tier expansion sequence and operational procedure.

### 2. Confirmed Facts

- Scenario A (user count ×2): Scale-up User Web and WAS first (highest user-facing impact); Admin platform scales independently based on admin user growth; Application Gateway CU auto-adjusts without configuration change
- Scenario B (RAG throughput increase): RAG WAS is the primary bottleneck — Scale-up to next E-series SKU; Vector DB should scale in parallel as embedding query volume increases; if GPU inference required, migrate to NC-series
- Scenario C (data volume): Blob Storage auto-scales (no action); RDBMS action depends on workload type: read-heavy → add read replica, write-heavy → Scale-up primary VM SKU
- Rolling upgrade in HA setup: deregister one AZ VM from Load Balancer → resize (3–5 min restart) → verify health → re-register → repeat for second AZ; zero-downtime achievable with proper sequencing

### 3. Items Requiring Further Confirmation

- Specific user count thresholds that trigger each Scale-up step (for capacity planning)
- Whether GPU inference is expected from initial deployment or only as a future upgrade path
- RDBMS workload split (read% vs. write%) to determine whether read replica or Scale-up is the primary expansion path

### 4. References

https://learn.microsoft.com/en-us/azure/virtual-machines/resize-vm
https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-read-replicas
https://learn.microsoft.com/en-us/azure/application-gateway/application-gateway-autoscaling-zone-redundant
https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction
