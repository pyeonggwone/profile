[person name]
윤홍욱

[case name]
Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청

[Support area path]
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

[Customer Statement]
1. 요청 목적 
   사내 사용자 플랫폼, 관리자 플랫폼, RAG 데이터 파이프라인, 데이터베이스, 스토리지로 구성된 전사 AI 플랫폼의 클라우드 도입을 검토 중입니다.

   특히 본 검토는 다음 사항을 포함합니다.
    · 싱글 테넌트 환경 기준 전체 구축 비용
    · 서비스별 확장 전략(Scale-up / Scale-out) 반영
    · 고가용성(Active-Active) 구조 반영
    · 각 Cloud사가 보유 또는 연계 가능한 외부 LLM 파트너 제안
    · 외부 LLM별 금액 / 보안 / 장점 / 비교

아래 서버 수량 중 2식으로 구성된 항목은 Active-Active 이중화 목적입니다.

2-1. 사용자 플랫폼
  - 사용자 플랫폼 Web
    · 4 vCPU / 16GB Memory / SSD 128GB × 2

  - 사용자 플랫폼 WAS
    · 8 vCPU / 64GB Memory / SSD 256GB × 2

2-2. 관리자 플랫폼
  - 관리자 플랫폼 Web
    · 4 vCPU / 16GB Memory / SSD 128GB × 2

  - 관리자 플랫폼 WAS
    · 8 vCPU / 32GB Memory / SSD 256GB × 2

2-3. AI 영역
  - RAG Data Pipeline WAS
    · 16 vCPU / 128GB Memory / SSD 500GB × 2

2-4. 데이터 영역
  - RDBMS (메타데이터, Index DB 등)
    · 8 vCPU / 32GB Memory / SSD 500GB × 2

  - Vector DB
    · 8 vCPU / 32GB Memory / SSD 500GB × 2

2-5. 스토리지
  - Data Storage
    · 3TB × 1 Auto Scaling 지원 조건

2-6. 네트워크
  - Load Balancer
    · L4 또는 L7 LB × 1


3. 견적 산정 기준

3-1. 전체 비용 기준
  아래 기준으로 견적을 요청드립니다.

    · 싱글 테넌트 전체 구성 기준 총액
    · 월 비용 / 연간 비용
    · 초기 구축비와 운영비 분리
    · 기본 구성안 / 권장 구성안 구분 제시

3-2. 확장 기준
  서비스별 확장 기준은 아래와 같이 요청드립니다.

    · Storage: Scale-out 기준
    · 그 외 모든 서비스(Web / WAS / RAG / RDBMS / VectorDB 등): Scale-up 기준

  즉, 견적 시 아래 내용을 함께 제시 부탁드립니다.

    · 초기 제안 스펙 기준 비용
    · Scale-up 가능한 최대 권장 사양
    · Scale-up 시 비용 증가 구조
    · Storage Scale-out 시 용량 증가에 따른 비용 구조
    · 향후 사용자 증가 및 처리량 증가 시 증설 방식

---

위 내용은 고객 인프라 요구사항입니다.











