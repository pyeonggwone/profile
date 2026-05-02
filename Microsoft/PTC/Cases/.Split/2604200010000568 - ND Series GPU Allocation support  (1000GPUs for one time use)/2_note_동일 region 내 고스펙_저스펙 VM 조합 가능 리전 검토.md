[Customer_Statement]
- 고객 요구의 핵심은 동일 Azure region에서 고스펙 RDMA GPU, 저스펙 GPU, CPU VM을 함께 확보하는 것이다.
- 저스펙 GPU까지 RDMA가 필요하면 후보 리전은 제한된다.
- 저스펙 GPU가 일반 GPU여도 되면 Korea Central, Japan East, Sweden Central 등으로 후보를 넓힐 수 있다.

[pre_scoping]
in_scope
- Review same-region combinations of high-end RDMA GPU and low-end GPU candidates.
- Separate RDMA low-end and general low-end GPU region scenarios.
- Highlight practical candidate regions for capacity validation.

out_of_scope
- Actual stock, quota approval, and deployment success are not guaranteed by product availability data.
- Multi-region architecture is not treated as the primary design.

assumptions
- Region selection must consider combined availability, not each SKU independently.
- Customer prefers a single Kubernetes cluster in one Azure region.

dependencies
- Region feasibility depends on the final high-end SKU choice and low-end RDMA requirement.
- Capacity team must validate requested dates and quantities.

risks_unknowns
- Public or local availability data can differ from subscription-specific availability and physical capacity.

[scoping]
customer_question
- Which Azure regions should be prioritized for same-region high-end and low-end VM combinations?

technical_scope
- RDMA low-end priority regions include West Europe, UK South, East US, East US 2, and North Central US.
- General low-end GPU expansion regions include Korea Central, Japan East, Australia East, Sweden Central, West US, France Central, Italy North, and West US 3.
- Korea Central is viable only for high-end RDMA plus general GPU combinations in the reviewed data.

process_scope
- Submit a ranked region list with acceptable alternatives.
- Ask Support/UAT to validate combined capacity for high-end, low-end, and CPU VM pools in the same region.

decision_points
- Decide whether proximity to Korea outweighs broader RDMA low-end options in US/Europe.
- Decide whether non-RDMA low-end GPU nodes are acceptable.

deliverables
- Candidate region list by technical scenario.
- Region validation wording for capacity escalation.

[research]
summary
- Region shortlisting depends on whether low-end GPUs also need RDMA.

facts
- If both high-end and low-end GPU pools need RDMA, priority regions include West Europe, UK South, East US, East US 2, and North Central US.
- If low-end GPUs can be general GPU nodes, Korea Central, Japan East, Australia East, Sweden Central, West US, France Central, Italy North, and West US 3 can be considered.
- Same-region SKU presence does not guarantee physical capacity or quota approval.

follow_up_questions
- Confirm whether Korea-adjacent regions are preferred over US/Europe capacity options.
- Confirm whether non-RDMA low-end GPU nodes are acceptable.

references
- https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade/newsupportrequest
- https://portal.azure.com/#view/Microsoft_Azure_Capacity/QuotaMenuBlade/~/myQuotas
