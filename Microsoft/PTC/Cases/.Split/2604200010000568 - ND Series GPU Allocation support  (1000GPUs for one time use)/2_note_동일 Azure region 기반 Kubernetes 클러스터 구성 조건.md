[Customer_Statement]
- 고객은 모든 CPU/GPU VM을 동일 Azure region에 배치하고, Acryl의 custom Kubernetes cluster에 편입하려 한다.
- 고스펙 GPU는 RDMA/InfiniBand가 필요한 분산학습 node group으로 분리하는 것이 핵심이다.
- 저스펙 GPU와 CPU VM은 같은 cluster에 포함하되 보조 workload에 배치할 수 있다.

[pre_scoping]
in_scope
- Define same-region placement and Kubernetes cluster participation requirements.
- Distinguish RDMA high-end GPU node pools from low-end GPU and CPU node pools.
- Include node scheduling assumptions for distributed training jobs.

out_of_scope
- Kubernetes installation, CNI selection, storage class design, and application deployment are not covered.
- AKS-specific implementation is not assumed because the customer uses a custom Kubernetes environment.

assumptions
- All selected VMs must be reachable within the same region and customer network boundary.
- RDMA-sensitive jobs must be scheduled only onto RDMA-capable GPU nodes.

dependencies
- The selected region must have compatible high-end GPU, low-end GPU, and CPU capacity.
- The customer's Kubernetes configuration must support node labels, selectors, taints, and tolerations.

risks_unknowns
- Same-region SKU availability does not guarantee stock or approved capacity for the requested dates.

[scoping]
customer_question
- What Kubernetes and regional placement conditions should be confirmed before submitting the capacity request?

technical_scope
- Treat same-region allocation as a hard requirement for the cluster design.
- Place high-end RDMA GPU VMs in a dedicated node pool for distributed training.
- Place CPU and non-RDMA GPU VMs in separate pools for support workloads and preparation tasks.

process_scope
- Ask capacity reviewers to validate combined availability in a single region.
- Avoid presenting split-region allocation as equivalent unless the customer accepts application-level distributed design changes.

decision_points
- Confirm whether all GPU nodes need RDMA or only high-end GPU nodes need RDMA.
- Confirm whether customer will accept a region outside Korea if capacity is stronger.

deliverables
- Same-region Kubernetes placement requirement statement.
- RDMA node pool boundary and scheduling assumptions.

[research]
summary
- The design requires same-region VM placement and Kubernetes node separation by workload and RDMA capability.

facts
- All VM instances must be able to join the customer's custom Kubernetes cluster.
- High-end GPU jobs that require RDMA should be scheduled onto RDMA-capable GPU nodes.
- CPU and non-RDMA GPU nodes can support preprocessing, inference, bug fixing, monitoring, and test preparation.

follow_up_questions
- Confirm whether the customer requires RDMA for all GPU nodes or only for high-end GPU nodes.
- Confirm network, storage, and Kubernetes scheduling constraints for the custom cluster.

references
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ndh100v5-series
- https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/nd-h200-v5-series
