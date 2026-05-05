[Customer_Statement]
- Azure 지원 범위는 Microsoft Azure 내 quota, capacity request, VM SKU/region 검토, Support SR 경로 안내에 집중된다.
- 고객이 여러 CSP를 병행해 capacity를 확보하려는 전략은 Microsoft 단일 지원 범위와 구분해야 한다.
- 멀티 CSP 또는 멀티 리전 전략은 고객의 조달 및 아키텍처 결정이며, 동일 Kubernetes/RDMA 요구와 충돌할 수 있다.

[pre_scoping]
in_scope
- Clarify Microsoft Azure support boundaries for quota, capacity, SKU, and region validation.
- Explain limits of multi-CSP parallel capacity sourcing in relation to same-region cluster design.
- Identify when split capacity becomes an architecture decision rather than a support action.

out_of_scope
- Negotiating with non-Microsoft cloud providers or other CSPs is not included.
- Designing cross-cloud or multi-CSP distributed training architecture is not included.

assumptions
- The requested solution is intended to run on Azure VMs.
- The customer may compare or parallelize procurement paths, but Azure support can validate only Azure subscription and capacity paths.

dependencies
- CSP partner ownership determines who can submit Azure quota and support requests.
- Same-region RDMA cluster requirements limit the usefulness of split capacity.

risks_unknowns
- Multi-CSP allocation can fragment capacity and reduce validity of GPUBASE performance comparison.

[scoping]
customer_question
- Where is the boundary between Azure capacity support and the customer's multi-CSP procurement strategy?

technical_scope
- Azure can support VM SKU selection, region validation, quota request guidance, and support ticket routing.
- Same-region RDMA Kubernetes requirements should be preserved unless the customer explicitly accepts a split architecture.
- Split-region or multi-CSP capacity may require application-level distributed design changes.

process_scope
- Keep Azure Support SR scoped to the Azure subscription, VM families, regions, and dates.
- Treat external CSP coordination as customer/partner procurement activity.

decision_points
- Confirm whether single-region Azure capacity is mandatory or whether split allocation is acceptable.
- Confirm which CSP controls the target Azure subscription and support entitlement.

deliverables
- Support boundary statement.
- Multi-CSP risk and decision note for customer discussion.

[research]
summary
- Microsoft Azure support can guide Azure quota and capacity routes, but multi-CSP procurement is outside the Azure support boundary.

facts
- Azure Support SR should stay scoped to Azure subscription, VM family, region, date, and use case.
- Partner Center can support CSP partner engagement for Microsoft partner support paths.
- Split-region or multi-CSP allocation may conflict with a same-region RDMA Kubernetes cluster requirement.

follow_up_questions
- Confirm whether single-region Azure capacity is mandatory.
- Confirm which CSP controls the Azure subscription and support route.

references
- https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade/newsupportrequest
- https://partner.microsoft.com/en-US/dashboard/
- https://partner.microsoft.com/en-US/support
