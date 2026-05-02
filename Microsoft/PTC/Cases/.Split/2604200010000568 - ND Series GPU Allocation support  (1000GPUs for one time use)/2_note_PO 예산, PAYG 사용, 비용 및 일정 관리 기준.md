[Customer_Statement]
- Acryl AI는 본 건에 대해 PO를 발행했고, GPU capacity 확보가 남은 blocker로 정리되어 있다.
- 고객은 PAYG 사용을 전제로 capacity 확보 후 배포를 진행하는 흐름을 검토한다.
- 비용과 일정 관리는 1개월 baseline과 격일 burst 테스트 패턴을 구분해 설명해야 한다.

[pre_scoping]
in_scope
- Frame commercial readiness, PAYG deployment flow, cost exposure, and schedule controls.
- Tie cost planning to baseline versus burst usage.
- Include August preferred window and September fallback.

out_of_scope
- Exact Azure pricing calculation and discount negotiation are not included.
- Contract, PO processing, invoicing, and procurement approval are not modified.

assumptions
- PAYG deployment starts only after capacity and quota approval.
- The issued PO supports the engagement but does not itself reserve GPU capacity.

dependencies
- Final cost depends on SKU, VM count, region, runtime, and allocation window.
- Schedule depends on capacity approval timing and available region options.

risks_unknowns
- Capacity may need to be held for a wider window than actual test-day usage, affecting cost expectations.

[scoping]
customer_question
- How should PO readiness, PAYG use, cost exposure, and schedule flexibility be managed in the response?

technical_scope
- Separate one-month always-on CPU/low-end GPU capacity from intermittent large GPU burst capacity.
- Use VM count and runtime assumptions to support later cost estimation.
- Avoid treating a capacity request as a pricing commitment.

process_scope
- Confirm billing subscription and purchase path before deployment.
- Share September flexibility with capacity reviewers to widen allocation options.

decision_points
- Confirm who controls the deployment subscription and PAYG billing.
- Confirm whether the customer can accept shifted dates or reduced GPU count to manage cost and availability.

deliverables
- Cost and schedule management assumptions.
- PAYG deployment readiness checklist items.

[research]
summary
- PO readiness supports the opportunity, but GPU capacity and quota remain separate prerequisites for PAYG deployment.

facts
- Customer-provided facts identify the PO as issued and GPU availability as the remaining blocker.
- PAYG deployment should proceed only after quota and capacity are confirmed.
- Cost exposure depends on SKU, VM count, region, runtime, and allocation period.
- August is preferred, and September flexibility can help capacity planning.

follow_up_questions
- Confirm the billing subscription and purchasing route.
- Confirm target budget guardrails and acceptable schedule shifts.

references
- https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/properties
- https://portal.azure.com/#view/Microsoft_Azure_Capacity/QuotaMenuBlade/~/myQuotas
