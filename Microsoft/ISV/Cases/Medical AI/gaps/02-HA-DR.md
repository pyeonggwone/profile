# 고가용성(HA) / 재해복구(DR) — 부족한 디테일 상세

## 현황 요약
현재 문서에는 각 컴포넌트의 구성 목록은 있으나, 장애 발생 시 어떻게 동작하는지,
얼마 만에 복구해야 하는지에 대한 정의가 전혀 없다.

---

## 1. RTO / RPO 목표 미정의

### 문제
병원이 플랫폼과 계약할 때 서비스 수준 협약(SLA)의 핵심 지표가 없다.

### 정의 필요 항목

| 용어 | 설명 | 예시 목표 (업계 기준) |
|------|------|-----------------------|
| **RTO** (Recovery Time Objective) | 장애 발생 후 서비스 복구까지 허용 시간 | ECG 분석 서비스: 4시간 이내 |
| **RPO** (Recovery Point Objective) | 복구 후 허용 가능한 데이터 손실 시점 | 환자 ECG 데이터: 1시간 이내 |
| **가용성 SLA** | 월간 서비스 가용률 목표 | 99.9% (월 43분 허용 다운) |

### 컴포넌트별 RTO/RPO 권고 설정

| 컴포넌트 | 장애 영향 | 권고 RTO | 권고 RPO |
|----------|-----------|----------|----------|
| AI Analysis Module (ACA) | ECG 분석 불가 | 1시간 | 없음 (Stateless) |
| MySQL Flexible Server | 서비스 운영 불가 | 2시간 | 5분 |
| CosmosDB (MongoDB) | ECG 데이터 조회 불가 | 1시간 | 1시간 |
| AKS 마이크로서비스 | 전체 서비스 불가 | 30분 | 없음 |
| RabbitMQ Cluster | 데이터 수집 중단 | 2시간 | 메시지 큐 기준 |
| VPN Gateway | 병원 연결 불가 | 4시간 | 없음 |

---

## 2. 컴포넌트별 HA 구성 현황 및 미비점

### AKS (Azure Kubernetes Service)

**현재**: 단순 AKS 클러스터 언급만 있음

**필요한 구성**
```
[노드 풀 구성]
- System Node Pool: 3개 노드 (가용 영역 1, 2, 3 분산) — 컨트롤 플레인 관리
- User Node Pool: 최소 3개 노드 ~ 최대 10개 노드 (HPA 기반 자동 확장)
- Spot Node Pool: 비용 절감용 (배치성 AI 학습 작업)

[Pod 가용성]
- 핵심 서비스: PodDisruptionBudget 설정 (최소 1개 항상 유지)
- 배포 전략: RollingUpdate (maxSurge=1, maxUnavailable=0)
- Liveness/Readiness Probe: 모든 서비스에 필수 설정

[가용 영역]
- Korea Central: Zone 1, 2, 3 지원 확인 필요
- Zone 분산 스케줄링: topologySpreadConstraints 적용
```

### CosmosDB (MongoDB API)

**현재**: "MongoDB Clusters에 저장" 언급만 있음

**필요한 구성**
```
[복제 구성]
- 단일 리전 기준: 자동 3복제본 (Azure 내부 처리)
- 멀티리전 필요 시: Korea Central (쓰기) + 읽기 복제본 1개 추가

[일관성 수준]
- ECG 원본 데이터 쓰기: Session 일관성 (기본값)
- AI 분석 결과 읽기: Eventual 일관성 (성능 우선)

[백업]
- Continuous Backup 모드: 30일 내 특정 시점으로 복원 가능
- 최대 백업 보존: 30일 (기본) ~ 7일 구간 지정 복원
```

### MySQL Flexible Server

**현재**: "MySQL Flexible Server" 언급만 있음

**필요한 구성**
```
[HA 모드]
- Zone-Redundant HA 활성화: 주 서버(Zone 1) + 대기 서버(Zone 2)
- 자동 장애조치(Failover): 60~120초 내 대기 서버로 자동 전환

[백업]
- 자동 백업 보존: 7일 (최대 35일)
- 지역 중복 백업: 활성화 권고 (Korea South에 복사본)
- Point-in-Time Restore 목표: RPO 5분 이내

[연결 재시도]
- AKS 마이크로서비스에서 MySQL 연결 끊김 시 자동 재시도 로직 필수
- 연결 풀(Connection Pool) 설정: ProxySQL 또는 PgBouncer 계층 검토
```

### RabbitMQ Cluster (Azure VM 기반)

**현재**: "RabbitMQ Clusters(VM)"만 언급, 클러스터 구성 불명확

**필요한 구성**
```
[클러스터 토폴로지]
- 최소 3개 노드 (홀수 개 필수 — Quorum Queue 기준)
- 노드: VM 3개 (Availability Zone 1, 2, 3 각 1개)

[Quorum Queue 사용]
- Classic Queue 대신 Quorum Queue 사용 (장애 내성 강화)
- 메시지 영속성: durable=true, delivery_mode=2

[장애 시나리오]
- 노드 1개 장애: 자동 리더 재선출, 서비스 영향 없음
- 노드 2개 장애: 큐 중단 → 온프레미스 에이전트가 로컬 버퍼에 데이터 저장
- 전체 장애: 로컬 Volume 재가동 후 보관 메시지 일괄 전송

[VM 재시작 자동화]
- Azure VM Scale Set으로 전환 검토 (자동 복구 정책) 또는
- Azure Monitor 알림 → Azure Automation Runbook으로 자동 재시작
```

---

## 3. 재해복구(DR) 전략 없음

### 단일 리전 장애 시나리오

```
[시나리오: Korea Central 리전 전체 장애]
영향: 모든 서비스 중단
복구 목표: RTO 4시간

[DR 옵션 비교]
옵션 A — Passive DR (비용 최소)
  - CosmosDB 지역 복제본: Korea South 읽기 전용 유지
  - MySQL 백업: Korea South Storage에 주기적 내보내기
  - AKS 워크로드: Helm Chart + GitOps로 빠른 재배포
  - 예상 RTO: 2~4시간 / 비용 추가: 낮음

옵션 B — Active-Passive DR
  - Korea South에 Standby AKS 클러스터 유지 (최소 노드)
  - Azure Traffic Manager로 자동 페일오버
  - CosmosDB 멀티리전 쓰기 활성화
  - 예상 RTO: 30분 이내 / 비용 추가: 높음
```

### 병원 온프레미스 연결 장애 시나리오

```
[시나리오: VPN Gateway 장애]
영향: Hospital A 데이터 전송 불가, K3S 병원 연결 불가

[대응 방안]
1. VPN Gateway Zone-Redundant SKU 사용 (VpnGw1AZ 이상)
   → 단일 Zone 장애 시 자동 전환
2. 온프레미스 에이전트 로컬 버퍼
   → VPN 복구 전까지 로컬 Volume에 데이터 보관 후 재전송
3. 보조 연결: ExpressRoute 검토 (주요 병원 대상)
```

---

## 4. 모니터링 → 자동 복구 연동 없음

### 현재
"Azure Monitor + Grafana"로 관찰만 가능한 상태

### 필요한 자동화

```
[Alert → 자동 조치 흐름]

AKS Node NotReady 감지
  → Azure Monitor Alert 발생
  → Logic App / Automation Runbook 트리거
  → 노드 재시작 시도 또는 신규 노드 추가 요청

RabbitMQ 큐 깊이 > 10,000 감지
  → AKS HPA 트리거 (Consumer Pod 스케일 아웃)
  → 지정 임계값 내 자동 해소

MySQL 연결 수 > 최대치 80% 감지
  → 알림 발송 (PagerDuty / Teams)
  → 읽기 부하는 Read Replica로 자동 분산 (애플리케이션 레벨)
```

---

## 5. 백업 / 복원 절차 문서화 없음

### 필요한 RunBook 목록

| RunBook | 담당자 | 예상 소요 시간 |
|---------|--------|----------------|
| MySQL 특정 시점 복원 | DBA / 운영팀 | 30분 |
| CosmosDB 복원 | 클라우드 운영팀 | 1시간 |
| AKS 재배포 (신규 클러스터) | DevOps팀 | 1시간 |
| RabbitMQ 노드 교체 | 인프라팀 | 2시간 |
| VPN Gateway 재구성 | 네트워크팀 | 4시간 |

---

## 권고 우선순위

| 순위 | 항목 | 이유 |
|------|------|------|
| 1 | RTO/RPO 목표 정의 | 병원과의 계약 SLA 기준 |
| 2 | MySQL Zone-Redundant HA | 서비스 운영 데이터 단일 장애점 제거 |
| 3 | RabbitMQ Quorum Queue 전환 | 메시지 유실 방지 |
| 4 | CosmosDB Continuous Backup 활성화 | RPO 보장 |
| 5 | DR 전략 선택 (Passive vs Active-Passive) | 비용과 RTO 트레이드오프 결정 |
