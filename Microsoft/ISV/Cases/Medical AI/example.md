# MedicalAI AiTiA ECO CENTER — 서비스별 예시 데이터 설명

---

## Azure VPN Gateway

병원 온프레미스와 MedicalAI 클라우드를 암호화 터널로 연결한다.

### Site-to-Site VPN 연결

| 항목 | 예시 값 |
|------|---------|
| Gateway SKU | VpnGw2 |
| 연결 대상 | Hospital A 온프레미스 (서울 데이터센터) |
| 로컬 네트워크 CIDR | 192.168.10.0/24 |
| Azure VNet CIDR | 10.1.0.0/16 (Hub VNet) |
| 공유 키 (PSK) | Key Vault에서 주입 (직접 노출 금지) |
| BGP ASN | 65001 (온프레미스), 65515 (Azure) |

**흐름**: Hospital A 온프레미스 방화벽 → VPN Gateway (Hub Subscription) → VNet Peering → SW/AI Subscription

### 연결 상태 모니터링

- Azure Monitor 경보: 연결이 60초 이상 끊기면 PagerDuty 알림 발송
- 예시 메트릭: `TunnelEgressBytes` > 0 → 정상, = 0 → 단절

---

## Azure ExpressRoute

대용량 DICOM/ECG 데이터를 전용 회선으로 전송하는 병원 전용 연결 경로.

### ExpressRoute 회로

| 항목 | 예시 값 |
|------|---------|
| 파트너 (공급자) | KT (Korea Telecom) |
| Peering 위치 | Seoul2 |
| 대역폭 | 1 Gbps |
| SKU | Standard |
| BGP Peering 주소 (Azure 측) | 172.16.0.1/30 |
| BGP Peering 주소 (온프레미스 측) | 172.16.0.2/30 |
| VLAN ID | 200 |

### Private Peering 구성

```
Hospital A 핵심 PACS 서버 (온프레미스)
 └─ ExpressRoute 회로 (KT 전용선)
     └─ ExpressRoute Gateway (Hub Subscription)
         └─ VNet Peering → SW Subscription (AKS, MySQL)
         └─ VNet Peering → AI Subscription (AI 분석 모듈)
```

**사용 시나리오**: 1GB 이상의 DICOM 영상 파일 배치 전송 시 VPN 대신 ExpressRoute 경로 우선 사용.

### 페일오버 전략

- ExpressRoute 장애 시 S2S VPN으로 자동 페일오버 (BGP 우선순위로 제어)
- ExpressRoute AS Path: 더 짧음 → 정상 시 항상 우선 선택

---

## Microsoft Entra ID

플랫폼 전체의 아이덴티티 및 접근 제어를 담당한다.

### 테넌트 구조

| 항목 | 예시 값 |
|------|---------|
| Entra ID 테넌트 | medicalai.onmicrosoft.com |
| 구독 연결 | Hub / Shared / AI / SW Subscription 모두 동일 테넌트 |
| 디렉토리 ID | a1b2c3d4-e5f6-7890-abcd-ef1234567890 |

### 사용자 및 그룹

| 계정 | 역할 | 예시 |
|------|------|------|
| `dr.kim@hospitalA.com` | Guest 사용자 (B2B) | ECG 분석 결과 조회 전용 |
| `ops-team@medicalai.com` | AKS 운영자 그룹 | AKS Contributor 역할 부여 |
| `ai-engineer@medicalai.com` | AI Subscription 기여자 | AI 분석 모듈 배포 권한 |
| `billing-admin@medicalai.com` | 청구 관리자 | MySQL 결제 데이터 접근 |

### 앱 등록 (App Registration)

병원 시스템이 MedicalAI API를 호출할 때 사용한다.

```json
{
  "appName": "HospitalA-ECG-Client",
  "clientId": "11112222-3333-4444-5555-666677778888",
  "tenantId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "scope": "api://medicalai-ecg-api/.default",
  "grantType": "client_credentials"
}
```

### 조건부 액세스 정책

| 정책명 | 조건 | 제어 |
|--------|------|------|
| Require-MFA-Ops | 대상: ops-team 그룹, 앱: Azure Portal | MFA 필수 |
| Block-NonKorea | 국가: KR 외 모든 국가 | 차단 |
| Compliant-Device-AI | 대상: ai-engineer, 앱: AI Subscription | 준수 디바이스만 허용 |

### RBAC 역할 할당 예시

```
AI Subscription
 └─ ai-engineer@medicalai.com → Contributor
 └─ ops-team@medicalai.com   → Reader

SW Subscription
 └─ ops-team@medicalai.com   → AKS Cluster Admin (커스텀 역할)
 └─ billing-admin@medicalai.com → MySQL Flexible Server Reader
```

---

## Azure Key Vault

비밀키·인증서·연결 문자열을 중앙에서 관리한다 (Shared Subscription).

### 저장 항목 예시

| 시크릿 이름 | 내용 | 접근 주체 |
|-------------|------|-----------|
| `ecg-db-connection-string` | MongoDB Atlas 연결 URL | AKS 마이크로서비스 (Managed Identity) |
| `mysql-password` | MySQL Flexible Server 비밀번호 | AKS 마이크로서비스 (Managed Identity) |
| `rabbitmq-broker-password` | RabbitMQ 브로커 인증 | AKS, Azure VM |
| `pii-masking-aes-key` | PII 암호화 AES-256 키 | PII Masking Container (온프레미스) |
| `ssl-cert-api-gateway` | API Gateway TLS 인증서 | AKS Ingress Controller |
| `vpn-psk` | VPN Gateway 공유 키 | Hub Subscription 자동화 스크립트 |

### 접근 방식

- AKS Pod: Workload Identity + Managed Identity → Key Vault에 직접 비밀 주입
- 온프레미스 컨테이너: 배포 시점에 Key Vault에서 AES 키를 1회 Pull → 로컬 Volume에 임시 저장

---

## Azure Kubernetes Service (AKS)

마이크로서비스 실행 환경. SW Subscription과 AI Subscription에 각각 배치된다.

### 클러스터 구성 예시

| 항목 | SW AKS | AI AKS (Platform Controller) |
|------|--------|-------------------------------|
| 노드 풀 | Standard_D4s_v3 × 3 | Standard_D8s_v3 × 2 |
| 오토스케일 | 3 ~ 10 노드 | 2 ~ 6 노드 |
| 네트워크 플러그인 | Azure CNI | Azure CNI |
| Private Cluster | 활성화 | 활성화 |

### 배포된 마이크로서비스 (SW AKS)

```yaml
services:
  - name: ecg-ingest-service       # ECG 데이터 수신 및 분류
    replicas: 3
    image: medicalai.azurecr.io/ecg-ingest:v2.1.0
    resources:
      requests: { cpu: "500m", memory: "512Mi" }

  - name: ecg-result-service        # AI 분석 결과 조회 API
    replicas: 2
    image: medicalai.azurecr.io/ecg-result:v1.8.3

  - name: user-management-service   # 사용자/기관 관리
    replicas: 2
    image: medicalai.azurecr.io/user-mgmt:v3.0.1
```

### Ingress 예시

```yaml
host: api.medicalai.com
paths:
  /ecg/upload  → ecg-ingest-service:8080
  /ecg/result  → ecg-result-service:8080
  /auth        → user-management-service:8080
```

---

## Azure Container Apps (ACA)

AI 분석 모듈을 서버리스 컨테이너 환경에서 실행한다 (AI Subscription).

### 환경 구성

| 항목 | 예시 값 |
|------|---------|
| 환경 이름 | aca-env-medicalai-ai |
| 서브넷 | 10.2.3.0/24 (AI Subscription 내부망) |
| 접근 방식 | Private Endpoint만 허용 (인터넷 비노출) |

### AI Analysis Module 앱 설정

```yaml
app: ecg-ai-analysis
image: medicalai.azurecr.io/ecg-ai:v4.2.0
minReplicas: 1
maxReplicas: 10
scaleRule:
  type: rabbitmq
  queueName: ecg-analysis-queue
  messageThreshold: 50      # 큐 메시지 50건당 1 replica 추가
env:
  - name: MONGODB_URI
    secretRef: ecg-db-connection-string   # Key Vault 주입
  - name: MODEL_PATH
    value: /mnt/models/ecg-classifier-v4
volumes:
  - name: model-volume
    storageType: AzureFile
    storageName: medicalai-models         # Storage Account
```

**흐름**: RabbitMQ 큐 메시지 증가 → ACA 자동 Scale-out → MongoDB에서 ECG 데이터 로드 → AI 추론 → 결과 ACA Volume 저장

---

## RabbitMQ (Azure VM)

마이크로서비스 간 비동기 메시지 브로커. Azure VM 위에 클러스터로 운영된다.

### 클러스터 구성

| 항목 | 예시 값 |
|------|---------|
| VM SKU | Standard_D4s_v3 × 3 (3노드 클러스터) |
| RabbitMQ 버전 | 3.13.x |
| 미러링 정책 | ha-all (전 노드 미러링) |
| 관리 포트 | 15672 (VNet 내부만 허용) |
| AMQP 포트 | 5672 |

### 큐 구조

| 큐 이름 | 생산자 | 소비자 | 설명 |
|---------|--------|--------|------|
| `ecg.realtime.queue` | 온프레미스 RabbitMQ Producer | ecg-ingest-service | 실시간 스트리밍 ECG |
| `ecg.batch.queue` | File Format Container (온프레미스) | ecg-ingest-service | 배치 파일 업로드 |
| `ecg.analysis.queue` | ecg-ingest-service | ACA AI Analysis Module | AI 분석 요청 |
| `ecg.result.queue` | ACA AI Analysis Module | ecg-result-service | 분석 결과 전달 |

### 메시지 예시 (`ecg.analysis.queue`)

```json
{
  "messageId": "msg-20260420-0923-00187",
  "patientToken": "anon-7f3a9b2c",
  "recordedAt": "2026-04-20T09:21:00Z",
  "format": "XML",
  "storageRef": "mongodb://ecg-data/records/anon-7f3a9b2c",
  "priority": "normal"
}
```

---

## Azure Cosmos DB (MongoDB API)

비식별화된 ECG 데이터를 저장하는 NoSQL 데이터베이스 (SW Subscription).

### 계정 구성

| 항목 | 예시 값 |
|------|---------|
| API | MongoDB (4.2 호환) |
| 일관성 수준 | Session |
| 지역 | Korea Central (쓰기) + Korea South (읽기 복제) |
| 자동 스케일 | 최대 10,000 RU/s |
| Private Endpoint | 활성화 (퍼블릭 접근 차단) |

### 컬렉션 구조

```
Database: ecg-platform
├── ecg_records           # 원본 ECG 데이터 (비식별화 완료)
├── analysis_results      # AI 분석 결과
└── audit_logs            # 접근 감사 로그
```

### 문서 예시 (`ecg_records`)

```json
{
  "_id": "rec-20260420-000187",
  "patientToken": "anon-7f3a9b2c",
  "tenantId": "hospital-a",
  "recordedAt": "2026-04-20T09:21:00Z",
  "format": "XML",
  "leads": 12,
  "durationSeconds": 30,
  "rawDataRef": "/ecg-data/anon-7f3a9b2c/20260420-000187.xml",
  "piiMasked": true,
  "uploadedAt": "2026-04-20T09:23:47Z"
}
```

### 문서 예시 (`analysis_results`)

```json
{
  "_id": "result-20260420-000187",
  "recordId": "rec-20260420-000187",
  "analyzedAt": "2026-04-20T09:24:12Z",
  "modelVersion": "ecg-classifier-v4",
  "findings": [
    { "label": "Atrial Fibrillation", "confidence": 0.94 },
    { "label": "Normal Sinus Rhythm", "confidence": 0.04 }
  ],
  "riskLevel": "high",
  "reportRef": "/aca-volumes/reports/result-20260420-000187.pdf"
}
```

---

## Azure Database for MySQL Flexible Server

서비스 운영 데이터(사용자·기관·결제 정보)를 저장하는 관계형 DB (SW Subscription).

### 서버 구성

| 항목 | 예시 값 |
|------|---------|
| SKU | Standard_D4ds_v4 (4 vCore, 16 GiB) |
| MySQL 버전 | 8.0 |
| 백업 보존 기간 | 35일 |
| 고가용성 | Zone Redundant HA 활성화 |
| Private DNS Zone | privatelink.mysql.database.azure.com |

### 테이블 구조 예시

```sql
-- 병원/기관 정보
CREATE TABLE organizations (
    org_id      VARCHAR(36) PRIMARY KEY,  -- 'hospital-a'
    name        VARCHAR(200),             -- 'A대학교병원'
    tier        ENUM('standard','enterprise'),
    region      VARCHAR(50),              -- 'KR-Seoul'
    created_at  DATETIME
);

-- 결제 정보
CREATE TABLE billing_records (
    bill_id     VARCHAR(36) PRIMARY KEY,
    org_id      VARCHAR(36),
    period      VARCHAR(7),              -- '2026-04'
    ecg_count   INT,                     -- 4823
    amount_krw  DECIMAL(12,0),          -- 2411500
    status      ENUM('pending','paid','overdue'),
    FOREIGN KEY (org_id) REFERENCES organizations(org_id)
);
```

### 샘플 데이터

```sql
INSERT INTO organizations VALUES
  ('hospital-a', 'A대학교병원', 'enterprise', 'KR-Seoul', '2025-01-15'),
  ('hospital-b', 'B의원', 'standard', 'KR-Busan', '2025-06-01');

INSERT INTO billing_records VALUES
  ('bill-2026-04-ha', 'hospital-a', '2026-04', 4823, 2411500, 'pending'),
  ('bill-2026-04-hb', 'hospital-b', '2026-04',  312,  156000, 'paid');
```

---

## Azure Monitor + Grafana

플랫폼 전체의 관찰성(Observability)을 담당한다 (Shared Subscription).

### 수집 메트릭 예시

| 메트릭 | 임계값 | 경보 수신자 |
|--------|--------|-------------|
| AKS CPU 사용률 | > 80% (5분 지속) | ops-team Slack |
| RabbitMQ `ecg.analysis.queue` 적체 | > 500건 | ops-team PagerDuty |
| CosmosDB RU 소비 | > 9,000 RU/s | ops-team 이메일 |
| VPN Gateway 터널 상태 | = Disconnected | ops-team PagerDuty (P1) |
| ExpressRoute 회로 상태 | = NotProvisioned | ops-team PagerDuty (P1) |
| MySQL 복제 지연 | > 30초 | DBA 팀 이메일 |
| ACA 분석 모듈 오류율 | > 1% | ai-engineer 이메일 |

### Grafana 대시보드 구성

```
MedicalAI Platform Overview
├── Network Health       ← VPN/ExpressRoute 연결 상태
├── AKS Workloads        ← Pod 수, CPU/Memory 사용률
├── Message Queue        ← RabbitMQ 큐별 메시지 수/처리 속도
├── AI Analysis          ← 분석 처리량, 지연시간, 오류율
├── Database             ← CosmosDB RU, MySQL QPS
└── Tenant Usage         ← 병원별 ECG 업로드/분석 건수
```

### Log Analytics 쿼리 예시 (분석 오류 추적)

```kql
ContainerLog
| where TimeGenerated > ago(1h)
| where ContainerName == "ecg-ai-analysis"
| where LogEntry contains "ERROR"
| summarize ErrorCount = count() by bin(TimeGenerated, 5m)
| order by TimeGenerated desc
```

---

## Azure Storage Account

AI 모델 파일, 분석 결과 리포트, 공용 스토리지를 제공한다 (Shared Subscription).

### 컨테이너 구조

| 컨테이너 이름 | 용도 | 접근 수준 |
|---------------|------|-----------|
| `ai-models` | ECG AI 모델 파일 (.pt, .onnx) | Private (ACA만 접근) |
| `ecg-reports` | 분석 결과 PDF 리포트 | Private (AKS result-service만 접근) |
| `diag-logs` | 진단 로그 보관 | Private (Monitor만 쓰기) |
| `temp-upload` | 온프레미스 배치 파일 임시 수신 | Private (File Sync 전용) |

### 파일 예시

```
ai-models/
  ecg-classifier-v4/
    model.onnx              (240 MB)
    config.json
    labels.json             {"0": "Normal", "1": "AF", "2": "VT", ...}

ecg-reports/
  2026/04/20/
    result-20260420-000187.pdf
```

### Azure File Sync 연동

온프레미스 Hospital A의 배치 ECG 파일을 Azure File Share로 자동 동기화.

```
Hospital A 파일 서버 (\\fileserver\ecg-export)
 └─ Azure File Sync Agent
     └─ Storage Account: medicalaistorage
         └─ File Share: ecg-batch-sync
             └─ Azure Data Factory 트리거 → ecg-ingest-service 배치 처리
```

---

## Azure Arc

온프레미스 VM 및 K3S 엣지 클러스터를 Azure에서 중앙 관리한다.

### 연결된 리소스

| 리소스 | 유형 | 위치 | 관리 기능 |
|--------|------|------|-----------|
| Hospital A - ECG VM (Windows Server 2022) | Arc-enabled Server | 서울 데이터센터 | 패치 관리, 확장, 모니터링 |
| Hospital B - K3S 클러스터 | Arc-enabled Kubernetes | 부산 의원 내부 | GitOps 배포, 정책 적용 |
| Hospital C - K3S 클러스터 | Arc-enabled Kubernetes | 대구 의원 내부 | GitOps 배포, 정책 적용 |

### GitOps 배포 예시 (Hospital B K3S)

```yaml
# Flux GitOps 설정
sourceRef:
  kind: GitRepository
  url: https://github.com/medicalai/k3s-config
  branch: hospital-b
path: ./k3s/hospital-b/
interval: 5m

# 배포 대상 매니페스트
k3s/hospital-b/
  pii-masking-deployment.yaml    # PII Masking Container
  rabbitmq-producer-config.yaml  # RabbitMQ Producer 설정
  data-collector-daemonset.yaml  # ECG 수집 DaemonSet
```

### Azure Policy (Arc 서버 준수 확인)

| 정책 | 대상 | 결과 예시 |
|------|------|-----------|
| Windows 보안 패치 자동 설치 | Hospital A VM | 준수 |
| TLS 1.2 이상 강제 | 모든 Arc 서버 | Hospital A: 준수, Hospital B: 비준수 → 경보 |

---

## PII Masking / Anonymization Pipeline

온프레미스 Docker Container에서 동작하는 비식별화 처리 파이프라인.

### 처리 흐름

```
ECG Raw Data (환자 이름, 생년월일, 주민번호 포함)
 └─ Real-time Data Container 또는 File Format Data Container
     └─ PII Masking Container (Python + Java)
         ├─ 환자 이름 → SHA-256 해시 토큰  (예: "홍길동" → "anon-7f3a9b2c")
         ├─ 생년월일 → 연도만 보존          (예: "1985-03-22" → "1985")
         ├─ 의료기관 코드 → 내부 테넌트 ID  (예: "42601234" → "hospital-a")
         └─ 주민번호 → 완전 삭제
     └─ 비식별화 완료 데이터 → Volume 임시 저장
         └─ RabbitMQ Producer → ecg.realtime.queue 또는 ecg.batch.queue
```

### 입력/출력 예시

**입력 (원본 ECG XML 헤더)**
```xml
<PatientInfo>
  <Name>홍길동</Name>
  <BirthDate>1985-03-22</BirthDate>
  <SSN>850322-1234567</SSN>
  <HospitalCode>42601234</HospitalCode>
</PatientInfo>
```

**출력 (비식별화 완료)**
```xml
<PatientInfo>
  <PatientToken>anon-7f3a9b2c</PatientToken>
  <BirthYear>1985</BirthYear>
  <TenantId>hospital-a</TenantId>
</PatientInfo>
```

---

## AWS DataSync / Azure Data Factory / Azure File Sync (멀티클라우드 연동)

이기종 클라우드 및 온프레미스 데이터를 MedicalAI Azure로 통합한다.

### AWS DataSync

| 항목 | 예시 값 |
|------|---------|
| 소스 | AWS S3 버킷 `hospital-d-ecg-raw` (ap-northeast-2) |
| 대상 | Azure Storage Account `medicalaistorage` / `ecg-batch-sync` |
| 연결 경로 | VPN Gateway (AWS VGW ↔ Azure VPN GW) |
| 동기화 주기 | 매일 02:00 KST |
| 전송량 예시 | 약 15 GB/일 (DICOM 이미지 포함) |

### Azure Data Factory

| 파이프라인 | 소스 | 대상 | 주기 |
|-----------|------|------|------|
| `gcp-ecg-import` | GCP Cloud Storage `hospital-e-ecg` | Azure Blob `ecg-batch-sync` | 매시간 |
| `oracle-billing-sync` | Oracle DB (병원 내부 HIS) | MySQL `billing_records` | 매일 01:00 KST |
| `mssql-patient-token` | Azure SQL DB (외부 연계 시스템) | MongoDB `ecg_records` | 실시간 (트리거) |

### Azure File Sync

Hospital A 파일 서버의 ECG 배치 내보내기 폴더를 Azure File Share와 실시간 동기화.

```
Hospital A 파일 서버
  C:\ecg-export\              ← 매 10분마다 신규 파일 생성
   └─ Azure File Sync Agent (v16.x)
       └─ Sync Group: medicalai-ecg-sync
           └─ Cloud Endpoint: medicalaistorage / ecg-batch-sync
               └─ ADF 트리거 → ecg-ingest-service 배치 처리
```
