[Customer_Statement]
- 고객의 우선 요청은 총 256 GPUs이며, capacity 확보가 어려울 경우 128 GPUs로 축소 가능하다.
- 256 GPUs는 고스펙 GPU 128장과 저스펙 GPU 128장으로 나누어 검토한다.
- fallback 128 GPUs는 고스펙 64장과 저스펙 64장 기준으로 정리한다.

[pre_scoping]
in_scope
- Compare the primary 256 GPU request with the 128 GPU fallback request.
- Include VM count implications for 8-GPU and lower-end GPU SKUs.
- Preserve the same-region and Kubernetes cluster requirements.

out_of_scope
- Pricing commitment, purchase order terms, and final scheduling approval are handled separately.
- Multi-region fallback is not treated as equivalent to a single-region cluster.

assumptions
- The 256 GPU request is split into 128 high-end GPUs and 128 low-end GPUs.
- The 128 GPU fallback is split into 64 high-end GPUs and 64 low-end GPUs.

dependencies
- Capacity team validation is required for the selected region and SKU mix.
- Quota approval must match the chosen VM families and vCPU totals.

risks_unknowns
- A smaller 128 GPU test may reduce benchmark representativeness for full GPUBASE validation.

[scoping]
customer_question
- How should the primary 256 GPU request and the 128 GPU fallback be framed for capacity review?

technical_scope
- For high-end 8-GPU NDsr H100/H200 SKUs, 128 GPUs requires 16 VMs and 64 GPUs requires 8 VMs.
- For low-end RDMA 8-GPU A100/V100 SKUs, 128 GPUs requires 16 VMs and 64 GPUs requires 8 VMs.
- For low-end 4-GPU NCads A100 or NCas T4 SKUs, 128 GPUs requires 32 VMs and 64 GPUs requires 16 VMs.

process_scope
- Submit both primary and fallback sizes in the same capacity request.
- State that fallback is acceptable only if the validation goal remains viable.

decision_points
- Decide whether fallback capacity should preserve the 50:50 high-end/low-end split.
- Decide whether low-end GPUs can be non-RDMA nodes.

deliverables
- Primary and fallback capacity request wording.
- VM count and vCPU implication table for selected SKU families.

[research]
summary
- The 256 GPU request should be submitted as the primary ask, with 128 GPUs as an explicit fallback.

facts
- Primary scenario: 128 high-end GPUs and 128 low-end GPUs.
- Fallback scenario: 64 high-end GPUs and 64 low-end GPUs.
- H100 and H200 8-GPU VM options are `Standard_ND96isr_H100_v5` and `Standard_ND96isr_H200_v5`.
- A100 8-GPU alternatives include `Standard_ND96asr_v4` and `Standard_ND96amsr_A100_v4`.

follow_up_questions
- Confirm whether the 50:50 split must be preserved in the fallback scenario.
- Confirm whether A100 can be used as a fallback for high-end RDMA capacity.

references
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ndh100v5-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/nd-h200-v5-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ndasra100v4-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ndma100v4-series
