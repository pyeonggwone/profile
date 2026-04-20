# Power Platform 구현 요구사항
## MedicalAI AiTiA ECO CENTER — Power Platform 연계 설계

---

## 개요

MedicalAI 플랫폼의 핵심 백엔드(AKS, CosmosDB, RabbitMQ 등)는 Azure 클라우드 기반으로 유지하되,
**운영자·병원 담당자·경영진이 사용하는 프론트엔드 레이어 전반을 Power Platform으로 구현**한다.

Power Platform은 MedicalAI 플랫폼의 다음 4개 영역을 담당한다.

| 영역 | Power Platform 구성 요소 | 대상 사용자 |
|------|--------------------------|------------|
| 병원 포털 (ECG 제출·결과 조회) | Power Pages + Power Apps | 병원 의사·관리자 |
| 운영 자동화 (온보딩·알림·승인) | Power Automate | MedicalAI 운영팀 |
| 경영·운영 대시보드 | Power BI | 경영진·AI팀·청구 담당 |
| AI 결과 설명 어시스턴트 | Copilot Studio | 병원 의사·환자 담당자 |

---

## PHASE 1 — 병원 포털 (Power Pages + Canvas App)

### 1-1. 외부 병원 포털 — Power Pages

**목적**: 병원 의사·관리자가 별도 앱 설치 없이 브라우저에서 ECG 제출 및 분석 결과를 조회한다.

**요구사항**

```
[인증]
- Microsoft Entra External ID (B2C) 연동
  · 병원 관리자 초대 → 이메일 인증 → 포털 접근
  · 역할 기반 접근: 병원관리자 / 의사(조회 전용) / 청구담당자
- 세션 타임아웃: 30분 비활성 시 자동 로그아웃
- MFA: 병원관리자 계정 필수, 의사 계정 선택

[메인 화면 — ECG 제출]
- ECG 파일 업로드 (DICOM, XML, PDF 지원)
  · 파일 크기 제한: 최대 50MB
  · 드래그앤드롭 + 파일 선택 모두 지원
- 제출 전 필수 입력 항목:
  · 환자 가명 ID (병원 자체 비식별 처리 후 입력)
  · ECG 측정 일시
  · 검사 유형 (12리드 표준 / 홀터 / 기타)
- 제출 → 접수 번호(Request ID) 즉시 반환 및 화면 표시
- 제출 이력: 최근 30일 목록 (상태: 대기/처리중/완료/실패)

[분석 결과 조회]
- Request ID 또는 날짜 범위 검색
- 결과 카드 표시:
  · AI 분석 소견 텍스트
  · 신뢰도 점수 (Confidence Score) 시각화 (게이지 차트)
  · 이상 소견 유무 (정상/요주의/이상) 배지
  · 분석 완료 시각, 사용 모델 버전
- 결과 PDF 다운로드 (병원 로고 포함 레이아웃)
- 결과 공유: 이메일 전송 (Power Automate 연동)

[알림 설정]
- 분석 완료 시 이메일 알림 수신 여부 설정
- Webhook URL 등록 (EMR 시스템 연동용)

[사용량 조회 — 청구 담당자 전용]
- 월별 ECG 제출 건수
- 예상 청구 금액 (단가 × 건수)
- CSV 다운로드
```

**데이터 연결**
```
Dataverse 테이블 (Power Pages ↔ 백엔드 중간 계층):
  - ecg_submission     : 제출 요청 기록
  - ecg_result         : AI 분석 결과 (백엔드 API에서 Webhook으로 수신)
  - hospital_user      : 병원별 사용자 정보
  - billing_summary    : 월별 사용량 집계

백엔드 연동:
  - ECG 제출 → Custom Connector → AKS REST API (POST /api/v1/ecg/submit)
  - 결과 조회 → Custom Connector → AKS REST API (GET /api/v1/ecg/{id}/result)
  - AI 분석 완료 → 백엔드 Webhook → Power Automate → Dataverse 업데이트
```

---

### 1-2. 내부 운영 앱 — Canvas App (MedicalAI 운영팀 전용)

**목적**: MedicalAI 운영·개발팀이 플랫폼 상태와 병원 현황을 모바일·PC에서 조회·조치한다.

**요구사항**

```
[화면 구성]
1. 플랫폼 현황 화면
   - AKS Pod 상태 (Azure Monitor API 연동)
   - RabbitMQ 큐 깊이 현황 (Azure Monitor Metrics)
   - 병원별 온라인/오프라인 에이전트 상태 (Azure Arc 상태)
   - 최근 24시간 ECG 처리 건수 추이 (Power BI Embedded 타일)

2. 병원 관리 화면
   - 온보딩된 병원 목록 (상태: 활성/비활성/온보딩중)
   - 병원 상세: Subscription Set 정보, VPN 연결 상태, 에이전트 버전
   - 병원별 이번달 ECG 처리 건수 및 오류율

3. AI 모델 현황 화면
   - 현재 Production 배포 모델 버전
   - 최근 분석 응답시간 p50/p95/p99 (Azure Monitor)
   - 드리프트 감지 결과 최신 보고서

4. 알림·인시던트 화면
   - Azure Monitor 경보 수신 목록
   - 처리 상태 (신규/처리중/해결됨) 관리
   - 담당자 할당 및 메모 기록

[오프라인 지원]
- 병원 목록, 최근 인시던트 목록: 오프라인 캐시 지원
- 온라인 복구 시 자동 동기화
```

---

## PHASE 2 — 운영 자동화 (Power Automate)

### 2-1. 병원 온보딩 자동화 플로우

**트리거**: MedicalAI 영업팀이 SharePoint 온보딩 목록에 신규 병원 행 추가

```
[플로우 단계]

Step 1: 계약 정보 검증
  - 필수 필드 존재 여부 확인 (병원명, 담당자 이메일, 규모 분류)
  - 미완성 시 영업팀 담당자에게 이메일 반환

Step 2: 환경 준비 요청 생성
  - Azure DevOps Work Item 자동 생성
    ("병원명 Subscription Set 프로비저닝" 태스크)
  - 담당 인프라팀 Teams 채널 알림

Step 3: 승인 게이트
  - 운영 책임자 → Adaptive Card 승인 요청 (Teams)
  - 승인 기한: 2영업일
  - 기한 초과 시 리마인드 알림 1회 발송

Step 4: 승인 완료 후 자동 처리
  - Dataverse에 병원 레코드 생성 (hospital_config)
  - API Key 생성 요청 → Custom Connector → 백엔드 관리 API
  - 생성된 API Key → Key Vault 저장 (Azure Key Vault Connector)
  - 병원 관리자 초대 이메일 발송 (Power Pages 접근 링크 포함)

Step 5: 온보딩 체크리스트 추적
  - Dataverse Onboarding_checklist 테이블 행 생성
  - 각 단계 완료 시 상태 업데이트
  - 최종 완료 시 병원 담당자·영업팀에 완료 알림

[예외 처리]
  - 단계별 실패 시 운영팀 이메일 알림 + SharePoint 목록 상태 "오류"로 업데이트
  - 재시도: 수동 트리거 버튼 (Canvas App에서 호출 가능)
```

---

### 2-2. ECG 분석 완료 알림 플로우

**트리거**: 백엔드 Webhook → Power Automate HTTP 트리거

```
[플로우 단계]

Step 1: Webhook 수신 및 검증
  - HMAC-SHA256 서명 검증 (Request Header의 X-Signature)
  - 서명 불일치 시 400 응답 + 보안 로그 기록

Step 2: Dataverse 결과 업데이트
  - ecg_result 테이블 상태 "completed"로 업데이트
  - AI 소견, 신뢰도 점수, 모델 버전 기록

Step 3: 알림 발송 분기
  분기 A — 이상 소견 없음 (Normal):
    - 병원 담당자 이메일: 분석 완료 안내
    - Power Pages 포털 알림 뱃지 업데이트

  분기 B — 요주의/이상 소견 (Abnormal):
    - 병원 담당자 이메일: 긴급 알림 (제목에 [긴급] 접두어)
    - Teams Adaptive Card: 환자 가명 ID, 소견 요약, 포털 결과 링크
    - 설정된 Webhook URL로 결과 Push (병원 EMR 연동)

Step 4: 처리 로그 기록
  - Dataverse automation_log 테이블에 처리 결과 기록
```

---

### 2-3. AI 모델 드리프트 감지 알림 플로우

**트리거**: Azure Monitor 경보 → Power Automate

```
[플로우 단계]

Step 1: 경보 수신
  - Azure Monitor Alert Webhook → Power Automate

Step 2: 심각도 판단
  - Severity 0~2: AI팀 Teams 긴급 알림 + Dataverse 인시던트 생성
  - Severity 3~4: Dataverse 로그 기록 + 주간 보고서에 포함

Step 3: 긴급 알림 (Severity 0~2)
  - AI팀 리드에게 Adaptive Card 발송:
    · 드리프트 지표, 측정 시각, 영향 병원 수
    · 버튼: [재학습 요청] / [일시 무시] / [상세 보기]
  - [재학습 요청] 클릭 시 Azure DevOps 파이프라인 트리거

Step 4: 상태 업데이트
  - Dataverse incident 테이블: 생성 → 처리중 → 해결됨 추적
```

---

### 2-4. 정기 리포팅 자동화 플로우

**트리거**: 매월 1일 오전 9시 (스케줄)

```
[월간 리포트 생성 플로우]

Step 1: 데이터 집계
  - Dataverse ecg_submission 집계: 병원별 제출 건수, 성공률, 평균 응답시간
  - Azure Cost Management API: 구독별 월 실사용 비용

Step 2: Power BI 리포트 새로고침
  - Power BI REST API: 월간 리포트 데이터셋 Refresh 트리거

Step 3: 리포트 PDF 내보내기
  - Power BI REST API: 리포트 PDF Export
  - SharePoint 문서 라이브러리에 저장
    (경로: /Reports/YYYY-MM/monthly_report.pdf)

Step 4: 배포 알림
  - 경영진 배포 목록에 이메일 발송 (PDF 첨부)
  - Teams 채널 게시: "4월 월간 리포트가 발행되었습니다"
```

---

## PHASE 3 — 경영·운영 대시보드 (Power BI)

### 3-1. 경영진 대시보드

**목적**: C레벨·사업 담당자가 플랫폼 비즈니스 지표를 한눈에 파악한다.

**요구사항**

```
[페이지 1 — 서비스 개요]
시각화 항목:
  - 이번달 총 ECG 분석 건수 (KPI 카드)
  - 활성 병원 수 / 전월 대비 증감 (KPI 카드)
  - 월별 분석 건수 추이 — 12개월 선형 차트
  - 병원별 분석 건수 분포 — 도넛 차트
  - 지역별 병원 분포 — 지도 시각화

[페이지 2 — 매출·비용]
  - 월별 예상 매출 vs 실제 청구액 (묶음 막대 차트)
  - 병원별 월 수익 기여도 (게이지 + 테이블)
  - Azure 구독별 실사용 비용 (Shared/AI/SW 분리)
  - 병원당 원가 vs 수익 비교 (산점도)
  - Reserved Instance 절감 효과 누적 (누적 영역 차트)

[페이지 3 — 서비스 품질]
  - AI 분석 응답시간 p50/p95/p99 — 일별 꺾은선
  - 월별 서비스 가용률 vs SLA 목표선 — 참조선 포함
  - 분석 실패율 추이
  - AI 소견 분류 분포: 정상/요주의/이상 비율

슬라이서: 기간 선택 (월/분기/연), 병원 선택, 구독 Set 선택
새로고침 주기: 매일 새벽 3시 자동 갱신
```

---

### 3-2. 운영팀 대시보드

**목적**: 운영·인프라팀이 실시간에 가까운 시스템 상태를 모니터링한다.

```
[페이지 1 — 실시간 파이프라인 현황]
  - ECG 수신 → 처리중 → 완료 → 오류 깔때기(Funnel) 차트
  - 병원별 에이전트 온/오프라인 상태 테이블
  - RabbitMQ 큐 깊이 현황 (시간별 꺾은선)
  - 최근 1시간 DLQ(Dead Letter Queue) 발생 건수 (KPI 카드)
  - 처리 지연 상위 5개 병원 (테이블)

[페이지 2 — AKS 인프라]
  - 구독 Set별 AKS 노드 사용률 CPU/메모리 (히트맵)
  - Pod 재시작 횟수 추이 (비정상 징후 감지)
  - HPA 스케일 이벤트 타임라인
  - 노드 비용 vs 가용률 상관 산점도

[페이지 3 — AI 모델 성능]
  - 모델 버전별 응답시간 분포 (박스플롯)
  - 드리프트 지표 추이 (임계값 참조선 포함)
  - 병원별 월간 AI 소견 분포 변화
  - 재학습 이력 타임라인

데이터 소스:
  - Dataverse: ecg_submission, ecg_result, incident
  - Azure Monitor Log Analytics: KQL 쿼리 연동
  - Azure Cost Management API: DirectQuery
새로고침 주기: 15분
```

---

### 3-3. 병원 전용 Power BI Embedded

**목적**: Power Pages 포털 내 병원 관리자 화면에 Power BI 리포트를 임베드한다.

```
[병원별 전용 리포트]
  - 자원 내 ECG 제출 현황 (이번달 일별 건수)
  - 소견 분류 분포 (정상/요주의/이상)
  - 평균 분석 완료 소요 시간 추이
  - 미확인 결과 목록 (클릭 시 포털 상세 페이지로 이동)

보안:
  - Row-Level Security (RLS): hospital_id 기준
    · 각 병원 관리자는 자기 병원 데이터만 조회
  - Embed Token: Power Pages 유저 세션당 발급
  - 데이터 만료: 토큰 유효기간 60분
```

---

## PHASE 4 — AI 결과 설명 어시스턴트 (Copilot Studio)

### 4-1. 병원 포털 내 AI 소견 설명 Copilot

**목적**: 병원 의사·담당자가 AI 분석 결과에 대해 자연어로 질문하고 설명을 받는다.

**요구사항**

```
[기본 기능]
- Power Pages 포털 내 채팅 위젯으로 삽입
- 인증된 포털 사용자만 접근 (Entra External ID 연동)
- 현재 조회 중인 ECG 결과를 컨텍스트로 자동 전달

[대화 시나리오]

시나리오 1: 소견 설명
  사용자: "이 결과에서 요주의 소견이 뭔가요?"
  Copilot: AI 분석 결과 JSON을 참조하여 해당 소견의 의미를
           일반인 언어로 설명 (의료 전문가 확인 필수 고지 포함)

시나리오 2: 결과 비교
  사용자: "지난달 검사 결과와 비교해줘"
  Copilot: Dataverse에서 동일 환자 가명 ID의 이전 결과 조회 후 비교 요약

시나리오 3: 후속 조치 안내
  사용자: "이상 소견이 나왔는데 어떻게 해야 하나요?"
  Copilot: 일반적 후속 조치 안내 (전문의 상담 권고 등)
           + MedicalAI 고객지원 연결 옵션 제공

시나리오 4: 포털 사용 안내
  사용자: "결과 PDF는 어떻게 받나요?"
  Copilot: 포털 기능 안내 (단계별 설명 + 해당 버튼 위치 표시)

시나리오 5: 처리 지연 문의
  사용자: "제출한 지 1시간이 지났는데 왜 결과가 안 나오나요?"
  Copilot: Dataverse 제출 상태 조회 → 상태에 따른 안내
           지연(처리중 1시간 초과) 시 운영팀 에스컬레이션 Power Automate 트리거

[제한 사항 (필수 고지)]
- 모든 AI 소견 설명 말미에 자동 첨부:
  "본 내용은 AI 참고 정보이며, 최종 판단은 반드시 의료 전문가의 확인이 필요합니다."
- 진단 행위에 해당하는 질문 → 응답 거부 + 전문의 상담 안내
- 개인 환자 식별 정보 수집 금지 (가명 ID 외 입력 거부)

[Knowledge Base]
- MedicalAI 서비스 FAQ (SharePoint 문서)
- ECG 주요 소견 용어 사전 (Dataverse 참조 테이블)
- 포털 사용 가이드 문서
```

---

### 4-2. 내부 운영 Copilot (MedicalAI 운영팀 전용)

**목적**: Teams 내에서 운영팀이 자연어로 플랫폼 상태를 조회하고 조치를 요청한다.

```
[Teams 채널 통합]
- MedicalAI 내부 Teams 채널에 Copilot 봇 배포

[대화 시나리오]

시나리오 1: 상태 조회
  "현재 몇 개 병원이 오프라인이야?"
  → Azure Arc Connector 호출 → 오프라인 에이전트 목록 반환

시나리오 2: 인시던트 생성
  "Hospital B VPN 연결 오류 인시던트 생성해줘"
  → Dataverse에 인시던트 레코드 생성 + 담당자 할당 요청

시나리오 3: 온보딩 현황
  "이번달 온보딩 진행 중인 병원 알려줘"
  → Dataverse onboarding_checklist 조회 → 진행 단계별 요약 반환

시나리오 4: 비용 현황
  "이번달 Azure 비용 어떻게 돼?"
  → Azure Cost Management API 호출 → 구독별 비용 요약 반환

시나리오 5: 배포 승인 요청
  "Service AKS v1.3.2 프로덕션 배포 승인 요청해줘"
  → Power Automate 배포 승인 플로우 트리거
  → 승인자 Adaptive Card 발송
```

---

## 데이터모델 — Dataverse 테이블 설계

```
[핵심 테이블]

hospital (병원)
  - hospital_id          : Text (PK, 고유 식별자)
  - display_name         : Text
  - tier                 : Choice (dedicated / shared)
  - subscription_set     : Text
  - status               : Choice (active / inactive / onboarding)
  - notification_email   : Email
  - webhook_url          : URL
  - created_at           : DateTime
  - contract_start_date  : Date
  - contract_end_date    : Date

ecg_submission (ECG 제출)
  - request_id           : Text (PK, UUID)
  - hospital_id          : Lookup → hospital
  - patient_hash         : Text (비식별 환자 식별자)
  - ecg_format           : Choice (DICOM / XML / PDF)
  - status               : Choice (pending / processing / completed / failed)
  - submitted_at         : DateTime
  - completed_at         : DateTime
  - file_size_bytes      : Integer

ecg_result (AI 분석 결과)
  - result_id            : Text (PK)
  - request_id           : Lookup → ecg_submission
  - ai_finding           : Text (소견 텍스트)
  - severity             : Choice (normal / caution / abnormal)
  - confidence_score     : Decimal
  - model_version        : Text
  - analyzed_at          : DateTime
  - is_acknowledged      : Yes/No (병원 확인 여부)

onboarding_checklist (온보딩 체크리스트)
  - id                   : AutoNumber (PK)
  - hospital_id          : Lookup → hospital
  - phase                : Choice (환경준비 / 기술구성 / 통합테스트 / 운영이관)
  - status               : Choice (대기 / 진행중 / 완료 / 오류)
  - assignee             : Text
  - due_date             : Date
  - completed_at         : DateTime
  - notes                : Multiline Text

incident (인시던트)
  - incident_id          : AutoNumber (PK)
  - title                : Text
  - description          : Multiline Text
  - severity             : Choice (0-Critical / 1-High / 2-Medium / 3-Low)
  - status               : Choice (신규 / 처리중 / 해결됨)
  - assignee             : Text
  - hospital_id          : Lookup → hospital (해당 시)
  - source               : Choice (Azure Monitor / 수동 / Copilot)
  - created_at           : DateTime
  - resolved_at          : DateTime

billing_summary (청구 요약)
  - id                   : AutoNumber (PK)
  - hospital_id          : Lookup → hospital
  - billing_year_month   : Text (YYYY-MM)
  - ecg_count            : Integer
  - unit_price           : Currency
  - total_amount         : Currency (Calculated)
  - azure_cost_direct    : Currency
  - azure_cost_shared    : Currency
```

---

## 보안 요구사항 (Power Platform 레이어)

```
[환경 분리]
- Power Platform 환경: dev / staging / prod 분리
- Dataverse 데이터: prod 환경 실제 병원 데이터, dev/staging은 합성 데이터

[접근 제어]
- Power Pages: Entra External ID B2C 인증 + Table Permission (병원 ID 기준 RLS)
- Canvas App: Entra ID + Azure AD 그룹 기반 역할 할당
- Power BI: RLS (hospital_id 기준) + Workspace 단위 접근 제어
- Copilot Studio: 인증된 사용자만 접근, 응답에 환자 식별 정보 포함 금지

[데이터 보호]
- Dataverse 열 암호화: patient_hash, webhook_url
- DLP(Data Loss Prevention) 정책:
  · 업무용 커넥터만 허용 (SharePoint, Teams, Azure, Dataverse)
  · 비업무용 커넥터 (개인 OneDrive, Google Drive 등) 차단
- Custom Connector: API Key를 Power Platform 환경 변수로 관리 (코드 노출 금지)

[감사 로그]
- Power Platform 관리자 센터: 모든 플로우 실행 이력 90일 보관
- Dataverse 감사: 핵심 테이블 (hospital, ecg_result, incident) 변경 이력 추적
```

---

## 단계별 구현 로드맵

| 단계 | 기간 | 구현 항목 | 우선순위 |
|------|------|-----------|---------|
| **Phase 1** | 1~4주 | Power Pages 기본 포털 (ECG 제출·결과 조회) + Custom Connector | 최우선 |
| **Phase 2** | 3~6주 | Power Automate 온보딩 자동화 + ECG 알림 플로우 | 높음 |
| **Phase 3** | 5~8주 | Power BI 경영·운영 대시보드 | 높음 |
| **Phase 4** | 7~10주 | Canvas App (내부 운영 앱) | 중간 |
| **Phase 5** | 9~12주 | Copilot Studio AI 소견 설명 어시스턴트 | 중간 |
| **Phase 6** | 11~14주 | Power BI Embedded 병원 포털 내 삽입 | 낮음 |
| **Phase 7** | 13~16주 | 내부 운영 Copilot (Teams 연동) | 낮음 |

---

## 라이선스 요구사항

| 구성 요소 | 필요 라이선스 | 대상 |
|-----------|--------------|------|
| Power Pages | Power Pages 외부 사용자 용량 (월별 로그인 수 기준) | 병원 외부 사용자 |
| Power Automate | Power Automate Premium (HTTP, Custom Connector 포함) | MedicalAI 운영팀 |
| Power BI | Power BI Premium Per User 또는 Embedded (A SKU) | 경영진·운영팀 |
| Canvas App | Power Apps Premium (Custom Connector 사용 시) | MedicalAI 내부 사용자 |
| Copilot Studio | Copilot Studio 메시지 용량 (월별 메시지 수 기준) | 병원 포털 + 내부 |
| Dataverse | Power Apps Premium 포함 (1GB 기본 제공) | 전체 |
