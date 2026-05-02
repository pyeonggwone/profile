[Customer_Statement]
- 개발 가이드 자료: Agent, MCP, API, SDK, 커넥터, 플러그인 및 앱 연동 구현 자료
- 고객은 Azure OpenAI, Copilot Studio, Microsoft Fabric 등의 개발 및 구현 가이드와 API, SDK, 커넥터, 플러그인, 에이전트 구성 자료를 요청했다.
- 이 자료 범위는 RAG, Agent, 업무 자동화, 데이터 연동 등 개발 참고 자료다.

[pre_scoping]
in_scope
- Development guide materials for agents, MCP, APIs, SDKs, connectors, plugins, and app integration.
- Implementation references for Azure OpenAI, Copilot Studio, Microsoft Fabric, Microsoft 365 Copilot extensibility, and Microsoft Foundry.
- Materials for RAG, automation, data integration, and tool integration planning.

out_of_scope
- Writing production code, reviewing customer source code, or building the final solution.
- Local path or internal repository directory as reference evidence.

assumptions
- The customer needs development material for PoC and implementation planning.
- Official Microsoft documentation should be used for implementation facts.

dependencies
- Implementation path depends on platform choice, identity, data sources, permissions, and API availability.

risks_unknowns
- Agent and MCP-related capabilities can vary by product, preview status, region, and licensing.

[scoping]
customer_question
- What development guide materials support Agent, MCP, API, SDK, connector, plugin, and app integration implementation?

technical_scope
- Include Microsoft 365 Copilot extensibility, Copilot Studio, Azure OpenAI, Microsoft Fabric developer resources, and Foundry Agent Service.
- Include authentication, permissions, tool integration, testing, and publishing as follow-up dimensions.

process_scope
- Prioritize official implementation documentation first.
- Add approved decks only when customer-sharing is confirmed.

decision_points
- Which platform should be prioritized: Copilot Studio, Microsoft 365 Copilot extensibility, Foundry Agent Service, Azure OpenAI, or Fabric?
- Is the target PoC implementation or production implementation?

deliverables
- Development guide material entry.
- Follow-up questions for platform, data source, and authentication.

[research]
summary
- This topic covers development guide materials for agents, MCP, APIs, SDKs, connectors, plugins, app integration, RAG, and automation.

facts
- Microsoft 365 Copilot extensibility covers agents, plugins, connectors, developer tools, and APIs.
- Copilot Studio supports low-code agents and agent flows.
- Azure OpenAI, Microsoft Fabric, and Microsoft Foundry have official developer documentation.

follow_up_questions
- Which platform should be used for the first development track?
- Which APIs, data sources, and authentication methods are required?

references
https://learn.microsoft.com/en-us/microsoft-365-copilot/extensibility/
https://learn.microsoft.com/en-us/microsoft-copilot-studio/fundamentals-what-is-copilot-studio
https://learn.microsoft.com/en-us/azure/ai-services/openai/
https://learn.microsoft.com/en-us/fabric/developer/
https://learn.microsoft.com/en-us/azure/foundry/agents/overview
