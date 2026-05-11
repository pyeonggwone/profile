[Customer_Statement]
- 아키텍처 자료: Cloud 전환, 컨테이너 마이그레이션, 보안·데이터·AI 연계 설계 자료
- 고객은 권장 아키텍처, Reference Architecture, 보안·데이터·AI 서비스 연계 구조, 고객 환경 설계 검토 자료를 요청했다.
- 이 자료 범위는 Azure Cloud, Data, AI, Security를 함께 고려한 설계 참고 자료다.

[pre_scoping]
in_scope
- Architecture materials for cloud transition, container migration, security, data, and AI integrated design.
- Azure landing zone, reference architectures, migration patterns, and governance-aligned architecture references.
- Materials useful for customer design review discussions.

out_of_scope
- Customer-specific architecture approval, production design sign-off, and bill of materials.
- Internal repository folders or local document names as references.

assumptions
- The customer needs architecture references before a detailed design workshop.
- Official Azure Architecture Center and Cloud Adoption Framework resources can support this category.

dependencies
- Architecture relevance depends on workload type, compliance, network, identity, data platform, and target region.

risks_unknowns
- Generic reference architectures may require tailoring before customer adoption.

[scoping]
customer_question
- What architecture materials support cloud transition, container migration, and security-data-AI integrated design?

technical_scope
- Include Azure landing zones, Azure Architecture Center, container migration to AKS, AI workload foundations, and governance/security design areas.
- Separate reference architecture materials from developer guides and operational runbooks.

process_scope
- Build architecture material index from official Microsoft sources.
- Confirm whether customer wants generic references or scenario-specific architecture packs.

decision_points
- Which architecture scenario should be prioritized: AI, data platform, security, cloud migration, or container modernization?
- Is a workshop expected or only document sharing?

deliverables
- Architecture material entry.
- Follow-up questions for workload, compliance, and target architecture.

[research]
summary
- This topic covers architecture materials for cloud transition, container migration, and security-data-AI integrated design.

facts
- Azure Architecture Center provides reference architectures and design guidance.
- Azure landing zones provide a foundation for governance, security, network, identity, and management.
- Azure Migrate App Containerization supports migration architecture discussions for supported application types.

follow_up_questions
- Which architecture scenario should be addressed first?
- Does the customer need public reference architectures only or a tailored design review?

references
https://learn.microsoft.com/en-us/azure/architecture/
https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/
https://learn.microsoft.com/en-us/azure/migrate/tutorial-app-containerization-aspnet-kubernetes?view=migrate
https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/scenarios/ai/
