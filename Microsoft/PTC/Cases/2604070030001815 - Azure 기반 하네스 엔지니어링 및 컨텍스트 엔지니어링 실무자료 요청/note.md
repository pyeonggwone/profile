# Case Note: Azure 기반 하네스 엔지니어링 및 컨텍스트 엔지니어링 실무자료 요청

---

## 1. 기본 정보 (Basic Information)

| 항목 | 내용 |
|------|------|
| 담당자명 | 윤홍욱 |
| 케이스명 | Azure 기반 하네스 엔지니어링 및 컨텍스트 엔지니어링 실무자료 요청 |
| 지원 영역 | TPD (Proactive Services ONLY)/Data and AI/Build and Modernize AI Apps (Data and AI)/Build and modernize apps with containers, databases and AI/Azure AI Services |
| 고객 문의 원문 | Azure 기반 하네스 엔지니어링 및 컨텍스트 엔지니어링 실무자료 요청 |
| 우선순위 / Due Date | - |
| 현재 상태 | - |

---

## 2. Pre-Scoping

**In Scope**
- Azure-based AI evaluation harness engineering practices and reference materials
- Context engineering methodologies and patterns for Azure AI Services
- Prompt management, token optimization, and RAG-based context structuring on Azure OpenAI / Azure AI Foundry

**Out of Scope**
- Non-Azure AI/ML platforms (AWS SageMaker, GCP Vertex AI, etc.)
- Custom model training or fine-tuning infrastructure
- Production deployment architecture review or SLA-level design engagement

**Assumptions**
- Customer is working within the Azure AI Services ecosystem (Azure OpenAI, Azure AI Foundry)
- The request is for reference materials and practical examples, not a full design engagement
- "Harness engineering" refers to test/evaluation frameworks for LLM-based applications

**Dependencies**
- Active Azure subscription with Azure AI Services access
- Defined target use case or AI workload type

**Risks / Unknowns**
- Specific Azure AI service or SDK version not identified
- Intended audience, technical depth, and preferred material format not specified
- Unclear whether customer needs official Microsoft documentation, GitHub samples, or workshop content

---

## 3. Scoping

- **Evaluation Harness**: Identify Azure-native evaluation harness approaches for LLM and AI applications, including Azure AI Evaluation SDK, Prompt Flow testing patterns, and built-in quality metrics
- **Context Engineering**: Document context structuring best practices — system prompt design, few-shot example management, token budget control, and retrieval-augmented generation (RAG) patterns on Azure OpenAI
- **Reference Architecture**: Provide reference links to Microsoft Learn, Azure AI Foundry docs, and GitHub samples relevant to harness and context engineering
- **Practical Materials**: Curate hands-on labs, solution accelerators, and code samples accessible via official Microsoft resources
- **Scope Boundary**: Limited to Azure AI Services ecosystem; no general AI theory or non-Azure platform content

---

## 4. 요구 사항 평가 (Requirement Evaluation)

고객 문의 원문("Azure 기반 하네스 엔지니어링 및 컨텍스트 엔지니어링 실무자료 요청")을 핵심 답변 섹션 제목 형태로 재구성합니다.

1. Azure AI 평가 하네스(Evaluation Harness) 개념 및 구성 방법
2. Azure 기반 컨텍스트 엔지니어링(Context Engineering) 적용 방법 및 Best Practice
3. 하네스·컨텍스트 엔지니어링 관련 Microsoft 공식 참고 자료 및 실무 샘플 안내

---

## 5. IR 메시지 초안 (IR Message Draft)

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Data and AI/Build and Modernize AI Apps (Data and AI)/Build and modernize apps with containers, databases and AI/Azure AI Services

요청 내용:
Azure 기반 하네스 엔지니어링 및 컨텍스트 엔지니어링 실무자료 요청

요구 사항 평가:
- Azure AI 평가 하네스(Evaluation Harness) 개념 및 구성 방법
- Azure 기반 컨텍스트 엔지니어링(Context Engineering) 적용 방법 및 Best Practice
- 하네스·컨텍스트 엔지니어링 관련 Microsoft 공식 참고 자료 및 실무 샘플 안내

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

---

## 6. Research Notes

**Summary**
Customer requests practical reference materials for building AI evaluation harnesses and applying context engineering on Azure. Core focus is structured testing/evaluation pipelines for LLM-based applications and context optimization patterns using Azure OpenAI or Azure AI Foundry.

**Facts**
- **Harness Engineering (Evaluation)**: Azure AI Foundry provides the `azure-ai-evaluation` SDK supporting custom evaluators, built-in quality/safety metrics, and batch evaluation against test datasets for LLM pipelines
- **Context Engineering**: Involves structured management of system prompts, conversation history, retrieved documents (RAG), and few-shot examples to optimize model output within token limits
- **Azure AI Foundry**: Primary Azure-native platform for AI app development; includes Prompt Flow, evaluation tooling, and model deployment management
- **RAG Pattern**: Azure AI Search + Azure OpenAI is the canonical retrieval-augmented generation architecture for context engineering on Azure
- **Prompt Flow**: Visual LLM chain orchestration in Azure AI Foundry; supports harness-style testing, tracing, and evaluation workflows

**Follow-up Questions**
- Which Azure AI service is in scope? (Azure OpenAI, Azure AI Foundry, Azure AI Search, etc.)
- What is the target use case? (RAG, agents, summarization, classification, etc.)
- What is the preferred format for reference materials? (official docs, GitHub samples, architecture diagrams, workshop content)

**References**
- https://learn.microsoft.com/en-us/azure/ai-foundry/
- https://learn.microsoft.com/en-us/azure/ai-services/openai/
- https://learn.microsoft.com/en-us/azure/ai-studio/how-to/evaluate-generative-ai-app
- https://learn.microsoft.com/en-us/azure/ai-studio/concepts/evaluation-metrics-built-in
- https://learn.microsoft.com/en-us/azure/ai-studio/how-to/prompt-flow
- https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview
- https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/ai/azure-ai-evaluation
- https://azure.microsoft.com/en-us/blog/announcing-azure-copilot-agents-and-ai-infrastructure-innovations/
