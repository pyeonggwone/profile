# Case Memo — ND Series GPU Allocation support (1000GPUs for one time use)

---

## 타임라인

### 2026-04-21 | 케이스 접수 및 초기 분석

- TPD 김민지로부터 케이스 접수
- 고객: Acryl AI (https://www.acryl.ai/)
- 요청 내용: Jonathan 플랫폼 멀티 GPU 오케스트레이션 검증을 위한 ND Series GPU 대규모 일회성 할당
- PO 발행 완료, $600K 확정 딜. GPU 가용성이 유일한 블로커

**초기 불명확 사항 (클라리피케이션 필요)**
- "1,000 GPUs"의 단위 불명확 (VM 수 vs GPU 수)
- PTC에 요청하는 지원 범위 미명시
- 대상 리전 미확인
- 사용 기간 미확인

---

### 2026-04-21 | 클라리피케이션 요청 발송

TPD 김민지에게 아래 4가지 확인 요청:
1. "1,000 GPUs" 단위 (GPU 개수 vs VM 대수) 및 희망 스펙
2. 예상 사용 기간
3. 대상 Azure 리전
4. PTC에 요청하는 지원 범위

---

### 2026-04-22 | 클라리피케이션 답변 수신

| 항목 | 답변 내용 |
|---|---|
| GPU 단위 | **GPU 개수 기준** (VM 수 아님) |
| 목표 수량 | 최대 **256 GPUs** 목표 (1,000은 단일 CSP에서 확보 어렵다고 판단) |
| GPU 스펙 | **ND 시리즈 + InfiniBand 지원** 필수 |
| 멀티 CSP | AWS, GCP 병행 예정 (Azure 단독 아님) |
| 사용 기간 | **1주일 기본, 최대 1개월** |
| 대상 리전 | 한국 선호하나 **리전 무관** / 3월에 **Sweden Central** 사용 이력 있음 |
| 과거 이력 | 2026년 3월, Sweden Central에서 1주일 테스트 진행한 이력 있음 |

**수량 재계산 (ND96asr_v4 기준, GPU 8개/VM)**
- 256 GPUs ÷ 8 = **32 VMs**

---

## 현황 분석

### 권장 과금 모델: PAYG + On-demand Capacity Reservation

| 이유 | 근거 |
|---|---|
| 일회성 단기 사용 | 약정(Reserved/Savings Plan) 불필요 |
| 분산 학습 워크로드 | Spot VM 중단 위험 → PAYG 필수 |
| 32 VM 규모 | Capacity Reservation으로 사전 확보 후 PAYG 배포 |

### 비용 추정 (32 VMs 기준)

| 기간 | 비용 |
|---|---|
| 1주일 | 약 **$148,000** |
| 1개월 | 약 **$635,000** |

→ 1개월 비용이 PO 금액($600K)과 유사한 수준. 사용 기간 관리 중요.

### 리전 전략

- Sweden Central: 이전 사용 이력 → **가장 현실적인 첫 번째 후보**
- Korea Central: ND A100 v4 지원 가능성 낮음 (CLI로 확인 필요)
- 대안: East US, West Europe, Southeast Asia

---

## 다음 액션

- [ ] Sweden Central ND96asr_v4 가용성 CLI 확인
- [ ] 32 VM 규모 쿼터 신청 가능 여부 Portal에서 확인
- [ ] 고객 답변 작성: 리전별 신청 방법 및 Capacity Reservation 가이드 제공
- [ ] Azure 외 AWS/GCP 병행 부분은 PTC 범위 외임을 명시