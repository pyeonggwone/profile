[Customer_Statement]
- 고객은 전체 GPU 중 약 절반을 저스펙 GPU로 구성하고, CPU VM도 같은 Kubernetes cluster에 포함하려 한다.
- 저스펙 GPU 16장 규모와 CPU VM은 1개월 동안 지속 사용된다.
- 저스펙 GPU는 preprocessing, inference, bug fix, 테스트 준비, 보조 workload에 적합하다.

[pre_scoping]
in_scope
- Identify low-end GPU candidates and CPU auxiliary node role boundaries.
- Include RDMA and non-RDMA low-end GPU options.
- Estimate VM counts for 128, 64, and 16 GPU low-end scenarios.

out_of_scope
- Exact CPU VM family sizing is not defined in the provided materials.
- Storage, monitoring, and network appliance sizing are not included.

assumptions
- Low-end GPU nodes do not necessarily require RDMA unless the customer states otherwise.
- CPU nodes support control, preprocessing, storage, monitoring, and preparation workloads.

dependencies
- Low-end GPU choice depends on the same region as the high-end RDMA GPU nodes.
- CPU sizing depends on the customer's Kubernetes architecture and workload operations plan.

risks_unknowns
- If low-end GPU nodes also need RDMA, the feasible region list becomes narrower.

[scoping]
customer_question
- Which low-end GPU and CPU auxiliary node options should be included in the request?

technical_scope
- RDMA low-end candidates include `NDamsr A100 v4-Series`, `NDasr A100 v4-Series`, and `NDv2-Series`.
- General low-end GPU candidates include `NCads A100 v4-Series`, `NCas T4 v3-Series`, `NGads_V620_v1-series`, `NVads_V710_v5-series`, and `NVadsA10_v5-series`.
- CPU nodes should be scoped as auxiliary Kubernetes nodes, not as GPU performance nodes.

process_scope
- Present low-end GPU options as region-dependent alternatives.
- Ask the customer to confirm whether low-end GPU nodes need RDMA.

decision_points
- Choose RDMA-only low-end candidates or allow general GPU candidates.
- Confirm the approximate number and role of CPU instances.

deliverables
- Low-end GPU candidate list.
- CPU auxiliary node scope statement for capacity request.

[research]
summary
- Low-end GPU options should be separated into RDMA-capable and general GPU node choices.

facts
- 16 low-end GPUs can require 2 VMs for 8-GPU SKUs, 4 VMs for 4-GPU SKUs, 8 VMs for A10 2-GPU SKUs, or 16 VMs for 1-GPU SKUs.
- RDMA-capable low-end candidates include A100 and V100 ND-series options.
- General low-end candidates include A100 PCIe, T4, A10, and AMD V620/V710 options.
- CPU nodes should be sized separately for control, preprocessing, monitoring, storage, and support workloads.

follow_up_questions
- Confirm whether low-end GPU nodes must support RDMA.
- Confirm CPU VM count, vCPU, memory, storage, and network requirements.

references
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ndma100v4-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ndv2-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/nca100v4-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ncast4v3-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/nvadsa10v5-series
