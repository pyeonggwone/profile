# FinOps / 운영 비용 관리 — 부족한 디테일 상세

## 현황 요약
현재 문서에는 Azure 서비스 목록과 아키텍처 구성은 잘 되어 있으나
각 서비스의 비용 규모, 비용 최적화 전략, 구독 간 비용 배분 기준이 전혀 없다.
멀티테넌트 SaaS 모델에서는 병원별 원가 산정이 매출 분석의 핵심이다.

---

## 1. 주요 비용 구성 요소 (현재 정의 없음)

### 구독별 예상 주요 비용 항목

```
[Shared Subscription — 플랫폼 공통]
- Log Analytics Workspace: 데이터 수집량 기반 (GB/월)
- Key Vault: 작업 수 기반 (10,000건당 약 $0.03)
- Azure Monitor Alerts: 경보 규칙 수 × 신호 유형
- AKS Controller 클러스터: 노드 타입·수 기반
- Storage Account: 저장 용량 + 트랜잭션 수

[Hub Subscription — 네트워크 중심]
- VPN Gateway: SKU 기반 고정 + 데이터 전송량
  예: VpnGw2AZ ≈ $560/월 고정
- Azure Firewall Premium: ≈ $1,200/월 고정 + 처리량
- VNet Peering: 처리 데이터량 기반 (intra-region)

[AI Subscription — 병원/고객 Set당]
- ACA (Azure Container Apps): vCPU·메모리 사용 시간 + 요청 수
  (유휴 시간은 Scale to Zero로 비용 0 가능)
- Private Endpoint: $0.01/시간 + 처리 데이터량

[SW Subscription — 병원/고객 Set당]
- AKS 노드 풀: VM 타입 × 노드 수 × 시간
  예: Standard_D4s_v5 × 3노드 ≈ $420/월
- MySQL Flexible Server (HA): 컴퓨팅 + 스토리지
  예: General Purpose 4vCore + Zone-HA ≈ $350/월
- CosmosDB: RU/s 프로비저닝 또는 Serverless
  예: 1,000 RU/s ≈ $58/월 (고정 처리량)
- RabbitMQ VM × 3: VM 타입부터 결정 필요
  예: Standard_D2s_v5 × 3 ≈ $210/월
```

---

## 2. 비용 배분 모델 없음 (멀티테넌트 핵심)

### 문제
Shared 인프라 비용을 병원별로 어떻게 나누는지 기준이 없으면
SaaS 구독 요금제 설계가 불가능하다.

### 비용 배분 전략

```
[직접 비용 (병원 전용 — Set당 직접 귀속)]
SW Subscription AKS: 병원별 할당
MySQL Flexible Server: 병원별 할당
CosmosDB 병원 전용 인스턴스: 병원별 할당
→ Azure Cost Management: Resource Tag로 추적
  Tag 예: hospital=hosp-001, env=prod, tier=dedicated

[공유 비용 (Shared Subscription — 배분 필요)]
배분 기준 옵션:
  A. 균등 분배: (총 Shared 비용) ÷ 병원 수
  B. 사용량 비례: ECG 처리 건수 또는 데이터 전송량 기준
  C. 고정 + 변동: 기본료(고정) + 사용량 추가료(변동)

→ 권고: C 방식 (SaaS 요금제와 일치)
```

### Azure Cost Management 태그 전략

```
[필수 태그 정의]
태그 키         | 예시 값              | 목적
─────────────|─────────────────── |──────────────────
hospital       | hosp-001           | 병원별 비용 추적
env            | prod / staging / dev| 환경별 비용 추적
service        | ecg-api / ai-module | 서비스별 비용 추적
billing-unit   | set-1 / shared     | 청구 단위 구분
cost-center    | sw / ai / platform  | 팀별 비용 배분

[경보 설정]
- Subscription별 월 예산 설정 → 80% / 100% 도달 시 알림
- 이상 지출 감지: Azure Cost Anomaly Detection 활성화
- 주간 비용 리포트: Azure Cost Management → 이메일 자동 발송
```

---

## 3. 비용 최적화 전략 없음

### AKS 비용 최적화

```
[노드 타입 최적화]
- 시스템 노드풀: Standard_D4s_v5 (범용) — 안정성 우선
- 사용자 노드풀: Standard_D4as_v5 (AMD, 10~15% 저렴) — 비용 절감
- AI 학습 노드풀: Spot VM 활용 (최대 90% 할인, 중단 가능 워크로드)
  → Azure ML 학습 작업은 Spot 인터럽트 시 체크포인트 재시작

[자동 스케일링]
- Cluster Autoscaler: 유휴 노드 자동 축소 (--scale-down-delay 10분)
- KEDA(Kubernetes Event-Driven Autoscaling): RabbitMQ 큐 깊이 기반 Pod 수 조절
  → 새벽 시간 소비자 Pod 0으로 축소 가능

[VPA (Vertical Pod Autoscaler)]
- CPU/메모리 요청값 자동 조정 → 과할당 방지
```

### CosmosDB 비용 최적화

```
[처리량 모드 선택]
- Serverless 모드: ECG 분석이 간헐적인 경우 적합 (요청당 과금)
  예: 병원별 처리량이 낮은 초기 단계
- Provisioned Throughput: 일정 처리량 보장 필요 시
  → Autoscale RU/s: 최소 400 ~ 최대 4,000 RU/s 자동 조절 권고

[데이터 수명주기]
- Analytical Store 활성화: 분석 쿼리를 OLAP으로 분리 (OLTP RU 절약)
- TTL 설정: 만료 데이터 자동 삭제 (무료)
```

### MySQL 비용 최적화

```
[컴퓨팅 구매 옵션]
- Reserved Instance (1년): 최대 37% 할인
  → 장기 계약 병원이 확정되면 즉시 구매 권고
- Burstable 티어: 개발/스테이징 환경 (B2ms 등)

[스토리지]
- 자동 확장 활성화: 필요 시에만 증가 (불필요한 예약 스토리지 방지)
```

### RabbitMQ VM 비용 최적화

```
[Reserved VM (1년)]
- VM 3개 × D2s_v5 Reserved: 최대 37% 절감
  조건: MQ 클러스터는 상시 운영이므로 RI 적합

[Azure VM Scale Set 전환 검토]
- Spot VM 혼합: Spot 노드 1개 추가로 부하 분산 (중단 허용 가능 여부 확인 필요)
```

---

## 4. 스케일링 트리거 임계값 없음

### 현재
"RabbitMQ 클러스터 수평 확장 + AKS 노드 증설" 언급만 있고
구체적 조건이 없다.

### 스케일링 기준 정의 (예시)

| 컴포넌트 | 스케일 아웃 조건 | 스케일 인 조건 | 지연 |
|----------|-----------------|----------------|------|
| AKS Consumer Pod (KEDA) | RabbitMQ 큐 메시지 수 > 500건 | 큐 < 10건 5분 지속 | 즉시 |
| AKS API Pod (HPA) | CPU > 70% 또는 메모리 > 80% | CPU < 30% 10분 지속 | 3분 |
| AKS 노드 (Cluster Autoscaler) | Pod Pending 상태 발생 | 노드 CPU < 30% 10분 지속 | 10분 |
| ACA AI 모듈 | 동시 요청 수 > N | 동시 요청 < M | 1분 |

---

## 5. 서비스 SLA 정의 없음

### 병원과의 계약에 포함될 SLA 항목

| 항목 | 목표값 (미정의 → 정의 필요) | Azure 기반 SLA |
|------|---------------------------|----------------|
| 서비스 가용성 | 99.9% (월 43분 허용 down) | AKS+DB 조합 기준 |
| ECG 분석 응답시간 | p95 ≤ 30초 | ACA SLA 99.95% |
| 데이터 수집 지연 | 전송 후 5분 내 클라우드 수신 | VPN + RabbitMQ 기준 |
| 포털 조회 응답시간 | p95 ≤ 2초 | AKS + CosmosDB |

### SLA 위반 시 크레딧 정책 예시

```
[Service Credit 체계]
가용성 99.0% ~ 99.9%: 해당 월 서비스 요금 10% 크레딧
가용성 95.0% ~ 99.0%: 해당 월 서비스 요금 25% 크레딧
가용성 < 95.0%: 해당 월 서비스 요금 50% 크레딧
```

---

## 6. 구독별 비용 분석 리포팅 없음

### 필요한 리포트

```
[월간 비용 리포트 구성]
1. 전체 비용 요약 (구독별)
2. 병원별 원가 (직접 비용 + 공유 비용 할당)
3. 서비스별 비용 (ECG API, AI 모듈, DB 등)
4. 전월 대비 변동 분석 (급증 항목 강조)
5. 예산 대비 실적

[도구]
- Azure Cost Management: 내장 리포트 + 커스텀 뷰
- Power BI + Azure Cost Management 커넥터: 경영진 대시보드
- 자동 이메일: 월 1일 자동 발송
```

---

## 권고 우선순위

| 순위 | 항목 | 이유 |
|------|------|------|
| 1 | 리소스 태그 체계 즉시 적용 | 현재 비용 추적 불가 상태 — 소급 적용 어려움 |
| 2 | 예산 경보 설정 | 비용 이상 급증 즉시 감지 |
| 3 | Reserved Instance 구매 계획 | 안정 운영 시점에 최대 37% 절감 |
| 4 | AKS KEDA 스케일링 기준 정의 | 비용과 성능의 균형점 설정 |
| 5 | 병원별 원가 분석 체계 | SaaS 요금제 설계 기반 데이터 |
| 6 | 월간 비용 리포트 자동화 | 경영진 의사결정 지원 |
