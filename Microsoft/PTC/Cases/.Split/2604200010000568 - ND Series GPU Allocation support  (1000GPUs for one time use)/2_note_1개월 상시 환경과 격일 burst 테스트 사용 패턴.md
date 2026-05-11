[Customer_Statement]
- 고객은 1개월 동안 CPU 및 일부 저사양 GPU 환경을 유지하고, 대규모 GPU는 2주 동안 격일로 burst 테스트에 사용하려 한다.
- 대규모 GPU 테스트 총 사용일은 최소 6일 이상으로 정리된다.
- 8월 1일부터 8월 30일까지가 우선 일정이며, 9월도 fallback 일정으로 가능하다.

[pre_scoping]
in_scope
- Define steady-state and burst capacity windows for the capacity request.
- Separate always-on CPU/low-end GPU nodes from intermittent high-scale GPU nodes.
- Include preferred August schedule and September flexibility.

out_of_scope
- Daily job orchestration details and benchmark runbooks are not included.
- Billing optimization beyond usage-pattern explanation is not included.

assumptions
- Approximately 16 low-end GPUs plus CPU instances are needed continuously for one month.
- Large-scale GPU capacity is needed every other day during weeks 3 and 4.

dependencies
- Capacity approval must account for both allocation window and actual burst use dates.
- The customer's Kubernetes operations must support scale-up and scale-down around test days.

risks_unknowns
- Azure capacity may be allocated by availability window rather than exact test-day consumption.

[scoping]
customer_question
- How should the one-month baseline environment and intermittent large GPU burst pattern be described?

technical_scope
- Weeks 1-2 cover CPU and small low-end GPU environment setup.
- Weeks 3-4 cover large-scale distributed training/inference tests every other day.
- Non-test days are used for bug fixing, environment tuning, and preparation.

process_scope
- Include both preferred and flexible dates in Azure Support or internal capacity escalation.
- Clarify that not all 256 GPUs are required continuously for the entire month.

decision_points
- Confirm exact burst test dates if capacity team needs date-level allocation.
- Confirm whether the baseline 16 GPUs are part of the low-end GPU pool.

deliverables
- Usage schedule summary for capacity request.
- Baseline versus burst capacity statement.

[research]
summary
- The request should distinguish one-month baseline capacity from short burst GPU capacity.

facts
- Preferred period is August 1 to August 30.
- September is acceptable if August capacity is not feasible.
- CPU instances and approximately 16 low-end GPUs are planned for continuous one-month use.
- Large GPU capacity is planned for every-other-day testing during weeks 3 and 4, with at least 6 total test days.

follow_up_questions
- Confirm exact burst dates and expected runtime per test day.
- Confirm whether Azure capacity must be held for the full burst window or only specific dates.

references
- https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade/newsupportrequest
- https://portal.azure.com/#view/Microsoft_Azure_Capacity/QuotaMenuBlade/~/myQuotas
