# Microsoft ISV Success Program | PTC 기술 자문 케이스

## 역할 정의

**ISV Success Program Tech Specialist (PTC: Partner Technical Consultant)**

ISV 파트너사가 Azure/Microsoft 플랫폼 기반으로 솔루션을 설계·배포·Marketplace 등록하도록 1:1 기술 자문 및 아키텍처 검토를 수행.

---

## 케이스 목록

### ① Elex Ratio Pty Ltd (호주) — ME-124027

| 항목 | 내용 |
|---|---|
| 케이스 | ME-124027 |
| 컨설팅 날짜 | 2026.04.10 (회의), 2026.04.13 (후속 이메일) |
| 솔루션 | 법원(Courts) 대상 청문 일정 자동화 AI 에이전트 (호주·캐나다·미국 법원 사용 중) |

**주요 논의**
- Azure OpenAI Private Endpoint 구성 (VNet 내부 트래픽, 공용 인터넷 미경유)
- Managed Identity 인증 (.NET Core → Azure OpenAI, API Key 미사용)
- Azure AI Search + ADLS Gen2 Gold Layer 연결 (Hearing Scheduling Agent용)
- Agent Groundedness Evaluation 구현 권장 (Azure AI Foundry 기반)
- 아키텍처: AKS + .NET Core Agentic Layer + Azure OpenAI + Azure AI Search + ADLS Gen2 Medallion

---

### ② Agentware AI Technologies Private Limited (인도) — ME-124326

| 항목 | 내용 |
|---|---|
| 케이스 | ME-124326 |
| 담당자 | Kumar Rajendran (kumar@zeeproc.com) |
| 컨설팅 날짜 | 2026.04.07 → 2026.04.15 → 2026.05.05 재조정 |

**주요 논의**
- 기술 자문 세션 준비 항목 요청 (Architecture Diagram, Blockers, Marketplace Listing Plan)
- ISV Success Program 혜택 검토 중으로 일정 지연

---

### ③ Pratham Software Pvt Ltd / PSI Cloud Office (인도) — ME-109216

| 항목 | 내용 |
|---|---|
| 케이스 | ME-109216 |
| 담당자 | Mrigraj Singh Chundawat (mrigraj.chundawat@thepsi.com) |
| 컨설팅 날짜 | 2026.02.26 → 2026.03.19 재조정 |

**주요 논의**
- Architecture Review Session
- Azure 기반 Build and Modernize AI Apps (Azure Web PubSub 등)
- 케이스 심각도 C / 아키텍처 준비도 약 25%

---

### ④ AIngineer (말레이시아) — ME-121368

| 항목 | 내용 |
|---|---|
| 케이스 | ME-121368 |
| 담당자 | Crystal, Lee, Wan |
| 컨설팅 날짜 | 2026.03.27 (회의 직접 진행) |
| 솔루션 | 엔지니어링 AI Copilot (압력용기 설계기준, 오일·가스 산업 특화) |

**주요 논의**
- 자체 TTS 모델 운영 (말레이시아 언어 정확도 이유로 Azure 미사용)
- 아키텍처: Azure App Service + Cosmos DB + Blob Storage + Azure DevOps
- Marketplace 등록 방식: SaaS 형태 확정
- Azure Marketplace 수수료: 3% (standard store service fee) 안내
- 제안: 모니터링 구현, WAF/방화벽 추가, Landing Page 구현

---

### ⑤ Skymeric Technologies Pvt Ltd (인도) — ME-115041

| 항목 | 내용 |
|---|---|
| 케이스 | ME-115041 |
| 담당자 | Ankit, Amol Bhore |
| 컨설팅 날짜 | 2026.03.04, 2026.03.09, 2026.03.25 |
| 특이사항 | AgenticAI + RPA 전문 기업, HPE OEM ISV, NVIDIA Inception Partner |

**주요 논의**
- Agent-Based Copilot 아키텍처 (EDD Ops용, eval-driven-agents 패턴)
- Azure OpenAI Function Calling (Microsoft Foundry 기반)
- Prompt Engineering for Agent Control (System Message, Few-shot)
- Landing Page 구현 (Marketplace Entry Point, Entra ID SSO)
- Subscription Lifecycle (Resolve / Activate), SaaS Accelerator Reference Implementation
- Webhook + Partner Center 설정
- Multi-Tenant RDBMS: Azure SQL Database (Elastic Pool) 권장

---

### ⑥ Techgyan (인도) — ME-100381 / ME-100382

| 항목 | 내용 |
|---|---|
| 케이스 | ME-100381 / ME-100382 |
| 담당자 | Dipak Karkhanis, Smridi, Varsha, Kkalani, Krisha |
| 컨설팅 날짜 | 2025.12.05, 2025.12.19 |

**주요 논의**
- Power Apps Managed Solution 생성 및 내보내기 (step-by-step 가이드)
- AppSource Package Project 구성 (CLI + Visual Studio)
- Dataverse 뷰 생성 (Open Tickets 필터 뷰 등)
- AppSource 등록 필수 파일: `[Content_Types].xml`, `Input.xml`, 아이콘, `TermsOfUse.html`
- Customization Services (Managed Properties, DLP, 보안 정책)

---

### ⑦ Promptora AI Solutions Pvt Ltd (인도) — ME-096287

| 항목 | 내용 |
|---|---|
| 케이스 | ME-096287 |
| 담당자 | Subhankar, Rohit |
| 컨설팅 날짜 | 2025.10.31 |

**주요 논의**
- SaaS Chatbot 플랫폼 아키텍처 (다중 AI 챗봇 생성·배포·관리)
- Azure Blob Storage (문서 업로드·훈련 데이터 저장)
- PostgreSQL (테넌트별 스키마 분리, 데이터 격리)
- Multi-Tenancy 모델: SMB (공유 리소스) vs Enterprise (전용 격리)
- Azure Backup, 수평 확장, 로드 밸런싱, 감성 분석, 리드 관리

---

### ⑧ Atom Data NZ Limited (뉴질랜드) — ME-101254

| 항목 | 내용 |
|---|---|
| 케이스 | ME-101254 |
| 담당자 | Paul Li, Johnny Wang |
| 컨설팅 날짜 | 2025.12.03 → 2025.12.10 → 2025.12.16 재조정 |
| 내용 | Architecture Review Session |

---

### ⑨ Spirit Technology Solutions Ltd (호주) — ME-095788

| 항목 | 내용 |
|---|---|
| 케이스 | ME-095788 |
| 담당자 | Caleb Bateman, Vineet Nair |
| 컨설팅 날짜 | 2025.11.19 → 2025.11.24 재조정 |
| 내용 | Architecture Review Session |

---

### ⑩ SeeDigitalAI / Seeo.ai (미국·뉴질랜드) — ME-109184

| 항목 | 내용 |
|---|---|
| 케이스 | ME-109184 |
| 담당자 | Dean Marris (Co-Founder), Craig Marris, Paul Lee, Bede Cammock-Elliott |
| 컨설팅 날짜 | 2026.01.23 → 2026.02.07~10 (아키텍처 다이어그램 수신) |
| 내용 | AI Inference 아키텍처 검토, 기술 개선 사항 정리 |

---

### ⑪ AiRTS Pte. Ltd. (싱가포르) — ME-110346

| 항목 | 내용 |
|---|---|
| 케이스 | ME-110346 |
| 담당자 | Quyen, Jaz |
| 컨설팅 날짜 | 2026.01.27 (후속 자료 발송) |

**주요 논의**
- AKS + Azure Managed Application 배포 구조
- ACR + AKS 통합 (Kubelet Managed Identity, AcrPull Role)
- Publisher → Managed Resource Group → Customer Subscription 구조
- Cross-tenant Managed Identity 제한사항

---

### ⑫ Medial Pty Ltd (호주) — ME-108955

| 항목 | 내용 |
|---|---|
| 케이스 | ME-108955 |
| 담당자 | Justin O'Donnell 외 |
| 컨설팅 날짜 | 2026.01.21 |

**주요 논의**
- SaaS 아키텍처 검토 (Xero 통합, Business Central 통합)
- Azure Well-Architected Review (5 Pillars)
- AI Prompt Optimization (Azure OpenAI, Few-shot, JSON Schema 출력)
- Private Endpoints (App Service + Database VNet 격리)
- Multi-tenant 인증, 데이터 주권 및 컴플라이언스

---

### ⑬ Harman Connected Services, Inc. (미국) — ME-111327

| 항목 | 내용 |
|---|---|
| 케이스 | ME-111327 |
| 담당자 | Cherish Dickey, Manisha Choudhary, Gopakumar G, Artem Smirnov |
| 컨설팅 날짜 | 2026.01.28 |
| 내용 | Architecture Review Session |

---

### ⑭ 주식회사 소금광산 / SALTMiNE (한국) — ME-108085

| 항목 | 내용 |
|---|---|
| 케이스 | ME-108085 |
| 담당자 | Wake Ahn (empathy@saltmine.io) |

**주요 논의**
- Microsoft Commercial Marketplace SaaS 등록 절차 전반
- Transactable Offer 설정, Preview Audience 정의
- SaaS Fulfillment API 기술 요구사항
- Payout 계정 및 세금 서류 제출

---

### ⑮ Bespin Global (한국) — 한국어 대응

| 항목 | 내용 |
|---|---|
| 담당자 | 형재혁 (jaehyuk.hyung@bespinglobal.com) |
| 컨설팅 날짜 | 2025.12.15~16 |

**주요 논의**
- Azure VM NVMe 변환 스크립트 기술 지원
- TPD 구조 상세 설명 (한국어 대응)
  - 파트너 등급별 Advisory Hours: Core 5h / Expanded 10h / Solutions Partner 50h+ 
  - 계약 구조: 별도 금전 거래 없음, 파트너 프로그램 혜택 내 포함

---

### ⑯ Roxonn (인도) — ME-101967

| 항목 | 내용 |
|---|---|
| 케이스 | ME-101967 |
| 담당자 | dinesh R (dineshr@roxonn.com) |
| 컨설팅 날짜 | 2025.12.12 |

**주요 논의**
- AWS → Azure 마이그레이션 매핑
  - EC2 → Azure VM / App Service
  - RDS(PostgreSQL) → Azure Database for PostgreSQL
  - S3 → Azure Blob Storage
  - Parameter Store + KMS → Azure Key Vault
  - Auto Scaling → VM Scale Sets
- Web3/블록체인 배포 패턴, GitHub App 통합
- Marketplace SaaS Transactable Offer 게시 준비

---

### ⑰ Findler Technologies Private Limited (인도) — ME-106820

| 항목 | 내용 |
|---|---|
| 케이스 | ME-106820 |
| 담당자 | Abhinav |
| 컨설팅 날짜 | 2025.12.31 |

**주요 논의**
- Voice AI / 통화 자동화 아키텍처
  - Azure Speech-to-Text (실시간 전사, 다국어)
  - Azure OpenAI GPT-4 (의도 감지, 컨텍스트 관리)
  - Azure Text-to-Speech (Neural Voice, 저지연)
  - Barge-in 실시간 인터럽션 처리 (GPU 기반)
  - Azure VNet + 서브넷 네트워크 격리

---

### ⑱ Translab Technologies Pvt Limited (인도) — ME-101494

| 항목 | 내용 |
|---|---|
| 케이스 | ME-101494 |
| 담당자 | Amit.P, Shirshendu Bikash Mandal (SVP), Vipluv Jain |
| 컨설팅 날짜 | 2026.01.16 |
| 내용 | Architecture Review Session |

---

### ⑲ Edge Semantics Pty Ltd (호주) — ME-090905

| 항목 | 내용 |
|---|---|
| 케이스 | ME-090905 |
| 담당자 | Jeremy C, Graeme |
| 컨설팅 날짜 | 2025.10.31 → 2025.11.20 (후속) |

**주요 논의**
- Azure Container Apps → AKS 마이그레이션 계획
- GitOps (Argo CD), Private Endpoints, Azure Front Door Premium
- InfluxDB, TimescaleDB (컨테이너 내 운영, ADLS Gen2)
- PostgreSQL 스키마 분리 (테넌트별 데이터 격리)
- Marketplace Offer 유형 결정 (SaaS vs Managed Application)

---

### ⑳ DevOps Enabler & Co. (인도) — ME-097468

| 항목 | 내용 |
|---|---|
| 케이스 | ME-097468 |
| 담당자 | Suresh, Santhosh |
| 컨설팅 날짜 | 2025.11.20 |

**주요 논의**
- Azure API Management (API 게이트웨이)
- Azure Container Apps (완전 관리형 컨테이너 플랫폼)
- Multi-tenant SaaS 테넌시 모델 설계
- PostgreSQL 스키마 분리, Role-based Access Control
- GPU AKS 노드풀 (AI 워크로드)
- Marketplace Managed Application 게시

---

### ㉑ Exonpro Innovations LLP (인도) — ME-113431

| 항목 | 내용 |
|---|---|
| 케이스 | ME-113431 |
| 담당자 | Kusaldip Das |
| 컨설팅 날짜 | 2026.02.10 → 2026.02.19 재조정 |

---

### ㉒ Seers Group Australia Pty Ltd (호주) — ME-123038

| 항목 | 내용 |
|---|---|
| 케이스 | ME-123038 |
| 담당자 | Stephen Maclean (CEO, Seers Digital) |
| 컨설팅 날짜 | 2026.04.16 (NZST) 재조정 |

---

### ㉓ Maven Cloud Service (한국) — ASfP | 2602090010000553

| 항목 | 내용 |
|---|---|
| 케이스 | 2602090010000553 |
| 담당자 | Andrew Baek (백민호), Aiden (이용덕), Chloe (임연주) |
| 내용 | Azure Tenant Consolidation + 도메인 분리 관리 (ASfP 채널) |
| 배정 이유 | 한국어 구사 가능 컨설턴트 요청 |

---

## 기술 커버리지 요약

| 도메인 | 주요 기술 |
|---|---|
| Azure AI / LLM | Azure OpenAI, Azure AI Foundry, Azure AI Search, RAG, Agent 아키텍처 |
| Azure Infrastructure | AKS, Azure Container Apps, App Service, Azure VNet, Private Endpoints |
| Data | ADLS Gen2 Medallion, Cosmos DB, PostgreSQL, Azure SQL Elastic Pool |
| Security | Managed Identity, Entra ID SSO, WAF, Private Endpoints |
| Marketplace | SaaS Transactable Offer, Managed Application, AppSource, SaaS Fulfillment API |
| DevOps | Azure DevOps, GitOps (Argo CD), GitHub App |

> 총 23건 이상의 글로벌 ISV 파트너 기술 자문 수행 (APAC·인도·한국·미국 대상)