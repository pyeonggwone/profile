# PTC Case Note

## 1. Basic Information

- 담당자명: 윤홍욱
- 케이스명: Azure 기반 AI 플랫폼 인프라 아키텍처 및 견적 요청
- 지원 영역: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center
- 고객 문의 원문: 연계 가능한 외부 LLM 파트너 간 비용(토큰 단가), 보안 수준, 주요 장점을 비교하여 RAG 활용 목적에 맞는 LLM 선택 근거가 필요하다.
- 우선순위 / Due Date:
- 현재 상태:

## 2. Pre-scoping

- In scope:
  - Comparison of Azure AI Foundry-available LLM models (GPT-4o, Llama 3.3 70B, Mistral Large 2, Command R+) on cost, security, and RAG suitability
  - Per-model token pricing (input / output) and total cost sensitivity for RAG workloads
  - Security and compliance posture per model provider
- Out of scope:
  - LLM fine-tuning or custom model training
  - Benchmark evaluation (latency, accuracy) — requires customer-specific test data
  - Models not available via Azure AI Foundry (requires cross-cloud, see Note 10)
- Assumptions:
  - All models accessed via Azure AI Foundry managed endpoints within Azure boundary
  - RAG workload: primarily retrieval-augmented Q&A; moderate token volume per query
  - Security baseline: data must not leave Azure Korea Central region
- Dependencies:
  - Data residency and compliance requirements from customer
  - Expected token consumption volume (queries/day, avg. tokens/query)
- Risks / Unknowns:
  - Token pricing subject to change; estimates based on April 2026 public pricing
  - Actual RAG cost highly dependent on context window size per query

## 3. Scoping

1. GPT-4o (Azure OpenAI): $2.50/1M input tokens, $10.00/1M output tokens; highest security (Azure-native, SOC2/ISO27001/HIPAA, data stays in Azure, no training use); best overall RAG accuracy
2. Meta Llama 3.3 70B (Azure AI Foundry): ~$0.23/1M input, ~$0.77/1M output; lowest cost option; open-source; self-hostable for full data control; good multilingual and RAG capability
3. Mistral Large 2 (Azure AI Foundry): ~$2.00/1M input, ~$6.00/1M output; European provider, GDPR-first, EU data residency option; strong multilingual (French, Korean, Japanese) capability
4. Cohere Command R+ (Azure AI Foundry): ~$0.50/1M input, ~$1.50/1M output; purpose-built for RAG; native grounding and citation features; enterprise-grade Azure managed endpoint
5. Decision matrix: cost-first → Llama 3.3 70B; security/compliance-first → GPT-4o; RAG performance-first → Command R+ or GPT-4o; multilingual (Korean)-first → GPT-4o or Mistral Large 2

## 4. Requirement Evaluation

고객 문의를 분석하여 다음 핵심 답변 항목을 도출하였습니다.

1. 각 LLM 모델의 입력/출력 토큰 단가는 얼마이며, 동일 질의 량 기준 비용 차이는?
2. 보안·컴플라이언스 측면에서 가장 안전한 모델은 무엇이며, 그 이유는?
3. RAG 응용에 가장 적합한 모델과 그 근거는?
4. 한국어 더빠쾰 RAG 응용에 적합한 모델은?

## 5. IR Message Draft

안녕하세요, TPD 윤홍욱 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Well Architected/Azure Architecture Center

요청 내용:
연계 가능한 외부 LLM 파트너(Azure OpenAI, Meta Llama, Mistral, Cohere) 간 비용, 보안, RAG 적합성 비교 및 LLM 선택 근거 안내를 요청하셨습니다.

요구 사항 평가:
- 각 LLM 모델의 입력/출력 토큰 단가는 얼마이며, 동일 질의 량 기준 비용 차이는?
- 보안·컴플라이언스 측면에서 가장 안전한 모델은 무엇이며, 그 이유는?
- RAG 응용에 가장 적합한 모델과 그 근거는?
- 한국어 더빠쾰 RAG 응용에 적합한 모델은?

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes

### 1. Inquiry Summary

Customer needs a comparative analysis of available LLM models on Azure AI Foundry, covering per-token pricing, security/compliance posture, and RAG-specific suitability to support LLM selection decision.

### 2. Confirmed Facts

| Model | Provider | Input | Output | Security / Compliance | RAG Suitability |
|---|---|---|---|---|---|
| GPT-4o | Azure OpenAI | $2.50 / 1M tokens | $10.00 / 1M tokens | Highest — Azure-native, SOC2/ISO27001/HIPAA, no training use | Excellent |
| Llama 3.3 70B | Meta (AI Foundry) | ~$0.23 / 1M tokens | ~$0.77 / 1M tokens | Open-source; self-hostable for full data control | Good |
| Mistral Large 2 | Mistral (AI Foundry) | ~$2.00 / 1M tokens | ~$6.00 / 1M tokens | European provider, GDPR-first, EU data residency option | Good — strong multilingual (Korean supported) |
| Command R+ | Cohere (AI Foundry) | ~$0.50 / 1M tokens | ~$1.50 / 1M tokens | Enterprise-grade; Azure managed endpoint | Excellent — purpose-built for RAG, native grounding |

- Cost-first: Llama 3.3 70B (~10× cheaper than GPT-4o for same token volume)
- Security/compliance-first: GPT-4o (Azure OpenAI) — data never leaves Azure, strictest compliance
- RAG performance-first: Command R+ (RAG-optimized with grounding) or GPT-4o (highest accuracy)
- Korean-language RAG: GPT-4o or Mistral Large 2 (both show strong Korean multilingual performance)

### 3. Items Requiring Further Confirmation

- Expected daily query volume and average tokens per RAG query (to project monthly LLM cost)
- Compliance tier required (ISO 27001, ISMS, HIPAA) — determines if Llama or Mistral are viable
- Whether customer has existing Azure OpenAI PTU commitment that could reduce GPT-4o cost

### 4. References

https://learn.microsoft.com/en-us/azure/ai-services/openai/overview
https://learn.microsoft.com/en-us/azure/ai-foundry/
https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/
