[Customer_Statement]
- Acryl AI는 Jonathan GPUBASE의 multi-GPU orchestration 검증을 위해 대규모 GPU 환경을 요청하고 있다.
- 검증 대상은 open-source LLM과 의료특화 foundation model `A-LLM.H`의 distributed training/inference이다.
- 핵심 목적은 GPUBASE 적용 전후 성능, 안정성, 비용 효율을 확인하는 것이다.

[pre_scoping]
in_scope
- Define the workload scope for Jonathan GPUBASE validation.
- Cover distributed training and distributed inference scenarios.
- Include open-source LLM and `A-LLM.H` medical foundation model workloads.

out_of_scope
- Model architecture redesign, dataset preparation, and application code tuning are not covered.
- Benchmark result interpretation beyond capacity planning is not included.

assumptions
- The customer will operate its own custom Kubernetes environment.
- GPU capacity is the primary blocker for the planned validation.

dependencies
- Final workload sizing depends on selected GPU SKU, region, and approved capacity window.
- RDMA/InfiniBand is required for high-end GPU distributed training jobs.

risks_unknowns
- Exact model size, framework version, storage throughput, and benchmark success criteria are not yet fixed.

[scoping]
customer_question
- What workload scope should be used to justify GPU capacity for Jonathan GPUBASE validation?

technical_scope
- Scope validation around distributed training and distributed inference for LLM workloads.
- Separate high-end RDMA GPU node pools from low-end GPU or CPU node pools.
- Capture the GPUBASE before/after comparison as the technical objective.

process_scope
- Use the workload description in Azure Support or internal capacity escalation requests.
- Include preferred and fallback test windows when capacity is reviewed.

decision_points
- Confirm whether the test requires 256 GPUs or can start with 128 GPUs.
- Confirm whether low-end GPU nodes need RDMA or only high-end GPU nodes need RDMA.

deliverables
- Workload scope statement for capacity request.
- Validation boundary covering model types, execution mode, and target cluster design.

[research]
summary
- The capacity request should be framed as Jonathan GPUBASE validation for distributed LLM training and inference.

facts
- Customer-provided facts identify Jonathan GPUBASE performance validation as the main purpose.
- The target workloads include open-source LLMs and Acryl's medical foundation model `A-LLM.H`.
- High-end GPU nodes should use RDMA/InfiniBand-capable VM families when distributed training is in scope.

follow_up_questions
- Confirm exact model sizes, framework stack, dataset size, and benchmark pass criteria.
- Confirm whether low-end GPUs participate in distributed training or only support auxiliary workloads.

references
- https://www.acryl.ai/
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ndh100v5-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/nd-h200-v5-series
