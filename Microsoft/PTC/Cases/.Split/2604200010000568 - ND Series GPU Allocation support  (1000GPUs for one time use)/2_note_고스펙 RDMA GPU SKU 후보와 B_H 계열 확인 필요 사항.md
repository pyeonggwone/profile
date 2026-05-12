[Customer_Statement]
- 고객은 고스펙 GPU로 B/H 계열을 우선 희망하며, 고스펙 GPU 간 RDMA 지원이 필수라고 제시했다.
- 현재 확인 가능한 H 계열 후보는 `NDsr H100 v5-Series`와 `NDsr H200 v5-Series`이다.
- B 계열 GPU는 현재 확인된 후보 목록에 별도 SKU가 없어 Microsoft capacity team 또는 Azure Support 확인이 필요하다.

[pre_scoping]
in_scope
- Identify high-end RDMA GPU SKU candidates for the capacity request.
- Treat H100 and H200 NDsr series as primary H-series candidates.
- Flag B-series GPU availability as an unresolved validation item.

out_of_scope
- Non-RDMA PCIe H100 SKUs are not treated as primary distributed-training candidates.
- GPU performance benchmarking between H100, H200, and A100 is not included.

assumptions
- High-end GPUs represent about half of the total GPU requirement.
- RDMA/InfiniBand is mandatory between high-end GPU instances.

dependencies
- Microsoft capacity team or Azure Support must confirm B-series SKU naming and regional availability.
- Customer must confirm whether H100/H200 is acceptable if B-series is unavailable.

risks_unknowns
- B-series terminology may refer to a non-public, restricted, or incorrectly named GPU family.

[scoping]
customer_question
- Which high-end RDMA GPU SKUs should be proposed, and what must be confirmed about B/H series?

technical_scope
- Use `Standard_ND96isr_H100_v5` as the primary H100 8-GPU RDMA candidate.
- Use `Standard_ND96isr_H200_v5` as the primary H200 8-GPU RDMA candidate.
- Keep `Standard_ND96asr_v4` as an A100 fallback if H-series capacity is constrained.

process_scope
- Submit B-series as a validation question, not as a confirmed SKU.
- Request region and date capacity validation for H100/H200 with RDMA requirement.

decision_points
- Confirm whether B-series is mandatory or only preferred.
- Confirm whether A100 can be accepted as fallback for high-end RDMA workloads.

deliverables
- High-end SKU candidate list.
- B-series validation question for Support/UAT/internal capacity team.

[research]
summary
- H100 and H200 NDsr series are confirmed H-series candidates; B-series must be validated separately.

facts
- `Standard_ND96isr_H100_v5` provides 8 NVIDIA H100 GPUs per VM.
- `Standard_ND96isr_H200_v5` provides 8 NVIDIA H200 GPUs per VM.
- `Standard_ND96asr_v4` provides 8 NVIDIA A100 GPUs per VM and can be discussed as a fallback.
- B-series GPU availability is not confirmed and should be raised as a Microsoft validation item.

follow_up_questions
- Confirm whether B-series is a hard requirement or a preference.
- Confirm whether H100/H200 or A100 can satisfy the high-end RDMA requirement.

references
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ndh100v5-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/nd-h200-v5-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ndasra100v4-series
