# Acryl AI GPU Capacity Request

## 현재 상태

- UAT Action 생성 완료
- Action 상태: `In Progress`
- UAT 확인 경로: https://aka.ms/UA-Tracker-ManageAction?id=731388
- 최신 업데이트: Product Availability by Region 기준으로 A100 256장 및 H100 256장 요청 가능 후보 확인

## 케이스 기본 정보

| 항목 | 내용 |
|---|---|
| Tracking ID | `2604200010000568` |
| Action ID | `731388` |
| Action Title | `[Capacity][Acryl AI] ND96asr_v4 1,000 GPU quota request` |
| Work Item Type | `Actions` |
| Customer | Acryl AI |
| Partner CSP | Cloukers / 클루커스 |
| Requested Date | April 27 2026 |
| Request Type | GPU capacity / quota request |
| Primary SKU | `Standard_ND96asr_v4` |
| GPU Type | NVIDIA A100 40GB |
| Request Quantity | 125 VMs / 1,000 A100 GPUs / 12,000 vCPU |
| Preferred Region | Canada Central |
| Duration | 1 week, maximum 1 month |
| Business Impact | $600K PO confirmed, GPU capacity is main blocker |

## 케이스 상세

| 필드 | 내용 |
|---|---|
| Customer | Acryl AI (CSP via Cloukers / 클루커스) |
| VM SKU | `Standard_ND96asr_v4` (NVIDIA A100 40GB, 8 GPU/VM) |
| Requested | 125 VMs / 1,000 A100 GPUs / 12,000 vCPU |
| Region Priority | Canada Central, East US, West US 2, Sweden Central, West Europe |
| Duration | 1 week, maximum 1 month |
| Use Case | Large-scale distributed multi-GPU orchestration validation for Jonathan MLOps/LLMOps platform |
| Prior History | Same SKU deployed in Canada Central, March 2026 via Azure Support ticket |
| PO | $600K confirmed |
| Allocation Flexibility | Split-region allocation acceptable |

## 최신 요청 조건

A100과 H100 각각 256장씩 요청 예정입니다.

### 확인 결과

- A100 256장: 가능 후보 있음
- H100 256장: 가능 후보 있음
- A100 256장 + H100 256장 동시 요청: 조건부 가능

### A100 256장

| 항목 | 내용 |
|---|---|
| 우선 SKU | `Standard_ND96asr_v4` |
| 대체 SKU | `Standard_ND96amsr_A100_v4` |
| 필요 수량 | 32 VMs |
| 필요 vCPU | 3,072 vCPU |
| GPU 구성 | 256 A100 GPUs |
| InfiniBand/RDMA | 지원 |

확인 리전:

- `Standard_ND96asr_v4`: USGov Arizona `**`, USGov Texas, China North 2, UK South, East US, North Central US, South Central US, West US 2
- `Standard_ND96amsr_A100_v4`: Malaysia West, West US 3

### A100 대체안

| 항목 | 내용 |
|---|---|
| SKU | `Standard_NC96ads_A100_v4` |
| 필요 수량 | 64 VMs |
| 필요 vCPU | 6,144 vCPU |
| GPU 구성 | 256 A100 GPUs |

확인 리전:

- South Africa West `*`, Australia Central, USGov Virginia, Belgium Central, Brazil Southeast, China East, North Europe, West Europe, France Central, Central India, Japan East, Japan West, Korea South `*`, Switzerland West `*`, UAE Central `*`, UK South, East US, North Central US, South Central US, West Central US, West US, West US 2

### H100 256장

| 항목 | 내용 |
|---|---|
| 우선 SKU | `Standard_ND96isr_H100_v5` |
| 필요 수량 | 32 VMs |
| 필요 vCPU | 3,072 vCPU |
| GPU 구성 | 256 H100 GPUs |
| InfiniBand/RDMA | 지원 |

확인 리전:

- Non Regional, Australia Central, Australia Southeast, China North 3, Italy North, Japan West, Sweden South `*`, UAE Central `*`, UK South, UK West, East US, East US 2, North Central US, West US 2

## 진행 히스토리

| 일시 | 내용 |
|---|---|
| 2026-04-27 13:44 | 김민지 담당자에게 UAT Action 생성 및 기본 정보 공유 |
| 2026-04-28 15:47 | 문수영 GBB에게 UAT 진행 상황 히스토리 공유 |
| 최신 | Product Availability by Region 기준으로 A100/H100 256장 조건 확인 및 추후 업데이트 시 Teams로 연락 예정 |

## 관련자

| 역할 | 이름 / 이메일 |
|---|---|
| PTC | Kim Pyeong Gwon / v-kimpy@microsoft.com |
| Customer contact | 김 민지 / mjkim@cloocus.com |
| Microsoft GBB | Sooyoung Moon / somoon@microsoft.com |
| Microsoft | Minsuk Shin / minsukshin@microsoft.com |
| Support | Microsoft Support / supportmail@microsoft.com |
