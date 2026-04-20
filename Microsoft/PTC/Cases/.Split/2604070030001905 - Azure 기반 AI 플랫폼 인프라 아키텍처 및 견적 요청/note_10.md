# PTC Case Note

## 1. Basic Information

- 담당자명: 윤홍욱
- 케이스명: Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청
- 지원 영역: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center
- 고객 문의 원문: RAG 데이터 파이프라인에 외부 LLM을 연계할 경우, 각 클라우드 사업자(Azure, AWS, GCP)가 보유하거나 연계 가능한 외부 LLM 파트너가 무엇인지 파악이 필요하다.
- 우선순위 / Due Date:
- 현재 상태:

## 2. Pre-scoping

- In scope:
  - Azure-native LLM integration via Azure AI Foundry and Azure OpenAI Service
  - Cross-cloud LLM access options (AWS Bedrock, GCP Vertex AI) via public API from Azure workload
  - Data residency, network security, and compliance considerations per integration path
- Out of scope:
  - On-premises or private LLM hosting (self-hosted open-source models on IaaS)
  - LLM model fine-tuning or training infrastructure
  - Detailed per-model cost analysis (covered in Note 11)
- Assumptions:
  - Customer's RAG pipeline runs on Azure; LLM calls originate from Azure VNet
  - Azure AI Foundry is the primary recommended integration path for Azure-hosted workloads
  - Cross-cloud LLM calls use HTTPS/REST API; data leaves Azure network boundary
- Dependencies:
  - Customer data residency or compliance requirements (ISMS, ISO 27001, GDPR)
  - LLM technology preference or existing vendor relationships
- Risks / Unknowns:
  - Cross-cloud LLM API calls may require outbound firewall exception and increase latency
  - Private Endpoint not available for AWS Bedrock or GCP Vertex AI from Azure

## 3. Scoping

1. Azure AI Foundry (native): catalog of models from Microsoft (GPT-4o via Azure OpenAI), Meta (Llama), Mistral, Cohere, etc.; deployed within Azure boundary; supports Private Endpoint and VNet integration; data stays in Azure region
2. Azure OpenAI Service: dedicated capacity option (Provisioned Throughput Unit) for high-volume RAG workloads; SOC2/ISO27001/HIPAA compliant; data not used for model training
3. AWS Amazon Bedrock: accessible via HTTPS from Azure; data crosses cloud boundary; no Private Endpoint from Azure VNet; latency ~5–20ms additional vs. in-region Azure call
4. GCP Vertex AI: same cross-cloud pattern as AWS Bedrock; subject to GCP data processing terms; GDPR compliance depends on region selection
5. Recommendation: prefer Azure AI Foundry for data residency, security posture, and latency; cross-cloud options viable only if specific model unavailable on Azure AI Foundry

## 4. Requirement Evaluation

고객 문의를 분석하여 다음 핵심 답변 항목을 도출하였습니다.

1. Azure 환경에서 LLM을 연계할 때 Azure AI Foundry를 통한 연계와 외부 클라우드 API 호출의 차이점은?
2. Azure AI Foundry에서 연계 가능한 외부 LLM 파트너 목록은?
3. AWS Bedrock / GCP Vertex AI 호출 시 Azure 보안 정책(아웃바운드 방화벽, Private Endpoint 미지원) 측면의 제약은?
4. 데이터 상주(Data Residency) 요건이 있는 경우 어떤 연계 방식을 선택해야 하는가?

## 5. IR Message Draft

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

요청 내용:
RAG 데이터 파이프라인에 외부 LLM을 연계할 때 각 클라우드 사업자별 연계 가능한 LLM 파트너 및 보안·제약 사항 안내를 요청하셨습니다.

요구 사항 평가:
- Azure 환경에서 LLM을 연계할 때 Azure AI Foundry를 통한 연계와 외부 클라우드 API 호출의 차이점은?
- Azure AI Foundry에서 연계 가능한 외부 LLM 파트너 목록은?
- AWS Bedrock / GCP Vertex AI 호출 시 Azure 보안 정책 측면의 제약은?
- 데이터 상주(Data Residency) 요건이 있는 경우 어떤 연계 방식을 선택해야 하는가?

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes

### 1. Inquiry Summary

Customer wants to understand which LLM providers are available or connectable per cloud vendor, and the constraints when calling LLMs outside the Azure boundary from their Azure-hosted RAG pipeline.

### 2. Confirmed Facts

- Azure AI Foundry: unified model catalog within Azure; supported models include GPT-4o (Azure OpenAI), Llama 3.3 70B (Meta), Mistral Large 2, Command R+ (Cohere), Phi-4, and others; all accessed via managed Azure endpoint; supports Private Endpoint and VNet integration
- Azure OpenAI Service: Microsoft-managed; data stays within Azure region; not sent to OpenAI; SOC2, ISO27001, HIPAA compliant; optional Provisioned Throughput Unit (PTU) for deterministic latency
- AWS Amazon Bedrock: offers Claude (Anthropic), Titan (Amazon), Llama, Mistral; accessible via HTTPS REST from Azure; data crosses Azure network boundary; no Private Endpoint from Azure; latency overhead ~5–20ms
- GCP Vertex AI: offers Gemini (Google), Claude (Anthropic), Llama, Mistral; same cross-cloud pattern; data subject to GCP data processing agreements
- Key constraint: data residency requirements (ISMS, government, financial sector) may prohibit data leaving Azure Korea Central region — eliminates cross-cloud options

### 3. Items Requiring Further Confirmation

- Customer data residency or regulatory requirements (determines whether cross-cloud LLM calls are permissible)
- Preferred LLM model (may already be available on Azure AI Foundry, making cross-cloud unnecessary)
- Outbound firewall policy in customer's Azure VNet (affects whether cross-cloud API calls are allowed)

### 4. References

https://learn.microsoft.com/en-us/azure/ai-foundry/
https://learn.microsoft.com/en-us/azure/ai-services/openai/overview
https://azure.microsoft.com/en-us/products/ai-foundry/
