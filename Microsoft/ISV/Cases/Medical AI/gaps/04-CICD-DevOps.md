# CI/CD / DevOps — 부족한 디테일 상세

## 현황 요약
현재 문서에는 AKS, ACA, VM 등 운영 환경은 정의되어 있으나,
코드가 어떻게 테스트·빌드·배포되는지 전혀 언급이 없다.
운영팀이 서비스 업데이트를 어떻게 수행하는지 파악할 수 없는 상태이다.

---

## 1. 배포 파이프라인 없음

### 문제
AKS 마이크로서비스, ACA AI 모듈, 온프레미스 Docker 에이전트 각각의
배포 방법과 도구가 정의되어 있지 않다.

### 권고 파이프라인 구조 (Azure DevOps 기준)

```
[소스 관리]
GitHub 또는 Azure DevOps Repos → 브랜치 전략 정의 필요
  - main: 프로덕션 배포 트리거
  - develop: 통합 테스트 환경 배포 트리거
  - feature/*: PR 기반 자동 테스트

[파이프라인 종류]
1. 마이크로서비스 CI/CD (AKS 대상)
2. AI 모듈 CI/CD (ACA 대상)
3. 온프레미스 에이전트 패키징 파이프라인 (병원 납품 기기)
4. Infrastructure 파이프라인 (Bicep/Terraform)
```

**마이크로서비스 CI/CD 흐름**
```
PR 생성
  → 자동 테스트 (Unit Test + Integration Test)
  → 코드 품질 검사 (SonarCloud 또는 CodeQL)
  → 보안 취약점 스캔 (Snyk 또는 Trivy)

PR 머지 (develop 브랜치)
  → Docker 이미지 빌드
  → 이미지 취약점 스캔 (ACR 내장 Defender for Containers)
  → ACR 푸시 (이미지 태그: {브랜치}-{커밋 SHA})
  → AKS 개발 환경 자동 배포 (Helm upgrade)
  → 스모크 테스트 자동 실행

main 머지 (프로덕션 배포)
  → 승인 게이트 (운영 책임자 수동 승인)
  → AKS 프로덕션 환경 Blue/Green 또는 Canary 배포
  → 배포 후 헬스 체크 자동 검증 (5분)
  → 이상 시 자동 롤백
```

**AI 모듈 CI/CD 흐름**
```
모델 등록 (Azure ML Model Registry)
  → 이미지 빌드 (모델 + 추론 서버 패키징)
  → ACR 푸시
  → ACA 업데이트 (az containerapp update)
  → Private Endpoint 연결 확인
  → AI 응답 샘플 테스트 자동 실행
```

---

## 2. 컨테이너 이미지 관리 없음

### ACR(Azure Container Registry) 설계

```
[레지스트리 구성]
- ACR 위치: Shared Subscription 내 배치
- SKU: Premium (Private Link, 지역 복제 지원)
- Private Endpoint: AKS 및 ACA에서만 접근 (인터넷 비공개)

[이미지 네이밍 규칙 (없음 → 정의 필요)]
{acr-name}.azurecr.io/{서비스명}:{환경}-{버전}-{커밋SHA}
예: medai.azurecr.io/ecg-api:prod-1.2.3-a3f1c2d

[이미지 생명주기 정책]
- develop 이미지: 30일 후 자동 삭제
- staging 이미지: 90일 보관
- production 이미지: 영구 보관 (수동 정리)

[보안 스캔]
- Microsoft Defender for Containers: 이미지 푸시 시 자동 스캔
- 고위험 취약점(CRITICAL) 포함 이미지: 프로덕션 배포 차단
- 스캔 결과: Azure Security Center 통합 대시보드
```

---

## 3. Infrastructure as Code (IaC) 없음

### 문제
Azure 리소스(AKS, CosmosDB, MySQL 등)가 수동으로 생성된 경우,
재현·감사·버전 관리가 불가능하다.

### 권고 IaC 구조

```
[도구 선택]
- 권고: Bicep (Azure 네이티브, 학습 곡선 낮음)
- 대안: Terraform (멀티클라우드 일관성)

[모듈 구조]
infra/
├── modules/
│   ├── networking/       # Hub VNet, Spoke VNet, VPN GW
│   ├── aks/              # AKS 클러스터 + 노드 풀
│   ├── database/         # MySQL, CosmosDB
│   ├── messaging/        # RabbitMQ VM
│   ├── monitoring/       # Azure Monitor, Log Analytics
│   └── security/         # Key Vault, NSG, Private Endpoint
├── environments/
│   ├── dev/              # 개발 환경 파라미터
│   ├── staging/
│   └── prod/
└── pipelines/
    └── infra-deploy.yml  # IaC CI/CD 파이프라인

[배포 원칙]
- 모든 리소스 변경: PR → 리뷰 → 자동 배포
- What-if 미리보기: 배포 전 변경사항 자동 출력
- 드리프트 감지: 주 1회 실제 리소스와 IaC 상태 비교
```

---

## 4. GitOps / AKS 배포 전략 없음

### AKS 배포 방식 정의 필요

```
[옵션 비교]
옵션 A: Helm + Azure DevOps Pipeline (직접 배포)
  - 배포 속도 빠름
  - 산발적 드리프트 발생 가능
  - 소규모 팀에 적합

옵션 B: GitOps (Flux v2 또는 Argo CD)
  - Git 상태와 클러스터 상태를 자동 동기화
  - 드리프트 자동 감지·복구
  - AKS GitOps 확장(Extension)으로 Flux v2 네이티브 지원
  - 권고: 멀티테넌트 AKS(Set 1, 2, 3) 관리에 유리

[Helm Chart 구조]
charts/
├── ecg-api/           # ECG 처리 마이크로서비스
├── patient-portal/    # 웹 포털 서비스
├── notification/      # 알림 서비스
└── platform-controller/ # Platform AKS Controller
```

---

## 5. 온프레미스 에이전트 배포/업데이트 관리 없음

### 문제
병원 납품 기기(Windows Server + Docker)의 소프트웨어를 어떻게 원격 업데이트하는지 없음
현재 문서에서는 "Azure Arc를 통해 원격 SW 업데이트"만 언급됨

### 필요한 구체적 방법

```
[Azure Arc + Azure Update Manager]
1. 병원 온프레미스 VM을 Azure Arc 연결
2. Azure Update Manager로 OS 패치 정책 설정
   - Windows Server 보안 패치: 월 1회 자동 적용
   - 점검 시간: 병원 비업무 시간(새벽 2시) 설정

[Docker 컨테이너 업데이트]
- Azure Arc + GitOps(Flux)로 온프레미스 K3S 클러스터 업데이트
- Hospital A Windows Server Docker:
  - Azure Arc에 Custom Script Extension 배포
  - 업데이트 스크립트: docker pull + docker-compose up -d

[업데이트 롤아웃 정책]
단계 1: 테스트 병원(1개) 업데이트 후 24시간 모니터링
단계 2: 중소 병원(Hospital B, C, D) 순차 업데이트
단계 3: 주요 병원(Hospital A) 업데이트
→ 각 단계 이상 시 자동 롤백

[버전 호환성 관리]
온프레미스 에이전트 버전과 클라우드 서비스 버전 간 호환 매트릭스 문서화 필요
```

---

## 6. 환경 분리 전략 없음

### 필요한 환경 구성

| 환경 | 목적 | 인프라 규모 | 비용 |
|------|------|-------------|------|
| **dev** | 개발자 로컬 테스트 | 최소 (AKS 1노드) | 최소 |
| **staging** | 통합 테스트, QA | 프로덕션 60% 규모 | 중간 |
| **prod** | 실제 서비스 | 풀 스펙 | 최대 |

```
[환경별 데이터 분리]
- dev: 합성 ECG 데이터(Mock) 사용 — 실제 환자 데이터 사용 금지
- staging: 비식별화된 샘플 데이터 사용
- prod: 실제 비식별 ECG 데이터

[환경 간 승격(Promotion) 기준]
dev → staging: 자동화 테스트 통과율 ≥ 95%
staging → prod: 성능 테스트 통과 + 운영 책임자 승인
```

---

## 7. 배포 실패 시 롤백 전략 없음

```
[AKS 마이크로서비스 롤백]
- Helm: helm rollback {release} {revision}
- GitOps(Flux): Git 이전 커밋 revert → 자동 동기화

[ACA AI 분석 모듈 롤백]
- az containerapp revision activate --revision {이전 revision}

[자동 롤백 조건]
배포 후 5분 내:
  - Readiness Probe 실패율 > 30%
  - HTTP 5xx 에러율 > 5%
  → 위 조건 발생 시 이전 버전으로 자동 롤백 + 알림
```

---

## 권고 우선순위

| 순위 | 항목 | 이유 |
|------|------|------|
| 1 | CI/CD 파이프라인 기본 구성 | 배포 자동화 없이 빠른 서비스 개선 불가 |
| 2 | ACR + 이미지 취약점 스캔 | 보안 취약 이미지 배포 방지 |
| 3 | IaC (Bicep) 작성 | 인프라 재현성·감사 가능성 |
| 4 | 환경 분리 (dev/staging/prod) | 프로덕션 장애 예방 |
| 5 | GitOps (Flux v2) 도입 | 멀티 AKS 드리프트 방지 |
| 6 | 온프레미스 에이전트 업데이트 자동화 | 병원 납품 후 유지보수 효율화 |
