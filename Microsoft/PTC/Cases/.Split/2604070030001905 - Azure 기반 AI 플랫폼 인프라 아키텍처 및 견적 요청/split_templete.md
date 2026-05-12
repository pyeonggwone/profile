[reference]
오스템임플란트_AI플랫폼_견적_v0.2.xlsx
Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청 - 2604070030001905.docx

S.Pin Technology
f754124d-f841-4b68-aec4-092f484be5e1
6251876

Contact Details
* Phone
+82 010-3105-0341
* First Name
홍욱
* Last Name
윤
* Email
kyle.yoon@spintech.co.kr


* Case Title

2. 서비스 구성별 인프라 사양 및 역할 정의

4. 클라우드 기반 싱글 테넌트 구축 비용 산정 기준
5. 기본 구성안 vs 권장 구성안 비교
6. 서비스별 확장 전략(Scale-up / Scale-out) 정의
7. Scale-up 기준 최대 권장 사양 및 비용 증가 구조
8. Storage Scale-out 기준 용량 증설 비용 구조
9. 사용자·처리량 증가 시 증설 및 확장 시나리오
10. 클라우드 사업자별 외부 LLM 연계 가능성
11. 외부 LLM별 비교 분석

* Description
1. 전사 AI 플랫폼 전체 아키텍처 개요
사내 전사 AI 플랫폼(사용자 플랫폼, 관리자 플랫폼, RAG 데이터 파이프라인, RDBMS, Vector DB, 스토리지)의 클라우드 도입을 검토 중이며, 싱글 테넌트 환경 기준으로 전체 구성 아키텍처 방향에 대한 검토가 필요하다.

2. 서비스 구성별 인프라 사양 및 역할 정의
플랫폼을 구성하는 각 서비스의 요구 사양은 다음과 같으며, 이에 적합한 클라우드 인프라 구성이 필요하다.
- 사용자 플랫폼 Web: 4 vCPU / 16GB / SSD 128GB × 2
- 사용자 플랫폼 WAS: 8 vCPU / 64GB / SSD 256GB × 2
- 관리자 플랫폼 Web: 4 vCPU / 16GB / SSD 128GB × 2
- 관리자 플랫폼 WAS: 8 vCPU / 32GB / SSD 256GB × 2
- RAG Data Pipeline WAS: 16 vCPU / 128GB / SSD 500GB × 2
- RDBMS: 8 vCPU / 32GB / SSD 500GB × 2
- Vector DB: 8 vCPU / 32GB / SSD 500GB × 2
- Data Storage: 3TB × 1 (Auto Scaling 지원)
- Load Balancer: L4 또는 L7 × 1
2식으로 구성된 항목은 모두 Active-Active 이중화 목적이다.

3. 고가용성(HA) 및 이중화 구조 설계
2식으로 구성된 모든 서버는 Active-Active 이중화를 전제로 하며, 각 서비스 계층별 HA 구성 방안과 그에 따른 가용성 보장 수준(SLA)에 대한 검토가 필요하다.

4. 클라우드 기반 싱글 테넌트 구축 비용 산정 기준
싱글 테넌트 전체 구성 기준으로 월 비용 및 연간 비용을 산정해야 하며, 초기 구축비와 운영비를 분리하여 제시하는 기준이 필요하다.

5. 기본 구성안 vs 권장 구성안 비교
고객이 요청한 사양을 기준 구성안(기본)으로 하고, 안정성·보안을 강화한 권장 구성안을 별도 제시하여 두 구성안 간 사양, 비용(월/연간), 가용성 수준의 차이를 비교할 근거가 필요하다.

6. 서비스별 확장 전략(Scale-up / Scale-out) 정의
고객이 요청한 확장 기준은 다음과 같으며, 이에 따른 서비스별 확장 전략 정의가 필요하다.
- Storage: Scale-out 기준
- 그 외 모든 서비스(Web / WAS / RAG / RDBMS / Vector DB): Scale-up 기준

7. Scale-up 기준 최대 권장 사양 및 비용 증가 구조
각 서비스에 Scale-up을 적용할 경우 초기 제안 스펙 대비 최대 권장 사양이 어느 수준인지, 단계별 업그레이드에 따라 비용이 어떤 구조로 증가하는지 파악이 필요하다.

8. Storage Scale-out 기준 용량 증설 비용 구조
Data Storage(3TB 기본)의 용량이 증가할 경우 Auto Scaling 조건 하에서 용량 증가에 따른 비용 구조(단가, 구간별 차이 등)가 어떻게 되는지 파악이 필요하다.

9. 사용자·처리량 증가 시 증설 및 확장 시나리오
향후 사용자 수 및 처리량 증가 시 각 서비스 계층별로 어떤 순서와 방식으로 인프라를 증설·확장해야 하는지 구체적인 시나리오 파악이 필요하다.

10. 클라우드 사업자별 외부 LLM 연계 가능성
RAG 데이터 파이프라인에 외부 LLM을 연계할 경우, 각 클라우드 사업자가 보유하거나 연계 가능한 외부 LLM 파트너가 무엇인지 파악이 필요하다.

11. 외부 LLM별 비교 분석
연계 가능한 외부 LLM 파트너 간 비용(토큰 단가), 보안 수준, 주요 장점을 비교하여 RAG 활용 목적에 맞는 LLM 선택 근거가 필요하다.

* Language
Korean
* Country/Region
Korea
* TPD Program
Microsoft AI Cloud Partner Program
* TPD Service
TPD (Proactive Services ONLY) / Infrastructure / Enable Customer Success / Well Architected / Azure Architecture Center
* Product
Azure Architecture Center






description: 다음의 주제별로 reference 의  note_templete.jsonl을 참조하여 note.md를 완성한다.

# PTC Case Note Writer

reference 폴더의 `case_statement.md`, `note_templete.jsonl`, `reference_link.md`를 읽고, `note_templete.jsonl`의 섹션별 설정(`language`, `format`, `tone`, `token_limit`, `max_bullets`)을 적용하여 `note.md`를 완성하라.





