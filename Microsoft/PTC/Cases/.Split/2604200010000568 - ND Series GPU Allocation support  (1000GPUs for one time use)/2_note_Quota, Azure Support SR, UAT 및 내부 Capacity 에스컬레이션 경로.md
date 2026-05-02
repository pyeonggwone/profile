[Customer_Statement]
- 이 규모의 GPU 확보는 단순 VM 배포가 아니라 quota, Azure Support SR, UAT, 내부 capacity 검토가 함께 필요하다.
- 쿼터가 승인되어도 실제 물리 capacity가 없으면 배포는 실패할 수 있다.
- CSP 구조에서는 클루커스와 Microsoft PDM/Support 경로를 함께 활용해야 한다.

[pre_scoping]
in_scope
- Define the quota request, Azure Support SR, UAT, and internal capacity escalation paths.
- Include the minimum information needed for capacity review.
- Clarify that quota and physical capacity are separate requirements.

out_of_scope
- Direct ownership of Microsoft internal capacity systems is not available to the customer.
- Final approval timeline is not guaranteed.

assumptions
- The deployment uses an Azure subscription where the customer or CSP has sufficient permissions.
- CSP partner can submit quota or support requests if it owns the subscription relationship.

dependencies
- Subscription ID, region, VM size, VM count, required dates, duration, and use case are required.
- Internal escalation depends on account ownership and partner channel alignment.

risks_unknowns
- Large GPU capacity may require days to weeks depending on region and scale.

[scoping]
customer_question
- What escalation path should be used to secure quota and physical GPU capacity?

technical_scope
- Calculate vCPU quota per VM family and region based on selected GPU SKUs.
- Confirm that quota approval alone does not reserve physical capacity.
- Include RDMA/InfiniBand and same-region cluster requirements in the request.

process_scope
- Start with Azure Portal quota request for the chosen VM family and region.
- Open Azure Support SR if deployment fails or capacity pre-validation is required.
- Use CSP-to-PDM or AE/STU/internal capacity path for large or time-sensitive GPU capacity.

decision_points
- Determine whether Cloukus or Acryl AI submits the support request.
- Determine whether PDM, AE, or PTC internal escalation is the primary path.

deliverables
- Support/UAT request payload.
- Escalation route summary for quota and capacity validation.

[research]
summary
- Quota approval and physical GPU capacity validation must be handled as separate workstreams.

facts
- Azure Portal quota request is required for the selected VM family, region, and vCPU limit.
- Azure Support SR can be used for quota and capacity-related escalation.
- Partner Center or AE/PDM routes can be used when the CSP or account team must escalate capacity.
- Required payload includes subscription ID, VM size, VM count, region priority, start date, duration, and use case.

follow_up_questions
- Confirm the target subscription ID and support entitlement owner.
- Confirm whether Cloukus, Acryl AI, PDM, AE, or PTC owns the primary escalation motion.

references
- https://portal.azure.com/#view/Microsoft_Azure_Capacity/QuotaMenuBlade/~/myQuotas
- https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade/newsupportrequest
- https://partner.microsoft.com/en-US/dashboard/
- https://partner.microsoft.com/en-US/support
- https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/properties
