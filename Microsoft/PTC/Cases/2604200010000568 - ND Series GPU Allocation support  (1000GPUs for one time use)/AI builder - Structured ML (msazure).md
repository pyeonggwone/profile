GPU capacity management overview
Managing GPU capacity for Azure OpenAI models in BIC involves three main phases, each owned by a different team. This page provides a high-level view of the end-to-end process; dedicated pages cover the operational details relevant to CAPI.

The CAPI team maintains a GPU tracking page with a global view on expected new capacity reception, to drive clarity across the team.

Process overview









Phase 1 — Forecasting and demand planning
Owner: COO office and Antoine Cellerier

GPU capacity needs are forecasted and the demand model is updated on a regular cadence. This phase takes into account model usage and growth projections, room for experimental models, turn-space, and other factors. The forecast is reviewed with Finance to determine cost impact and secure GPU approvals.

Note
This phase is the responsibility of the COO office and is not covered in detail in this documentation.

Phase 2 — GPU allocation to BIC
Owner: 1P Capacity team (led by Nica Tierney)

Once GPUs have been approved by Finance and physically exist, the 1P Capacity team handles the GPU allocation to BIC through a process commonly called a GPU shuffle. In the most common case, this transfers GPU quota to the Azure subscriptions used by Azure OpenAI on BIC's behalf (Manifold quota type). However, GPUs can also be allocated to other subscriptions or quota types depending on the scenario (e.g., MEF).

During this phase, the CAPI team does not yet have access to the GPUs. CAPI's responsibility is to track the progress of the 1P Capacity team and ensure the shuffle completes as expected. The GPU tracking page reflects the GPU allocation as known by the CAPI team during this phase. Once the shuffle is complete, the new GPUs become visible in the MPCM tool within the BIC allotment.

For details, see Getting GPU Capacity from 1P Capacity team.

Phase 3 — CAPI GPU allocation
Owner: CAPI team

Once GPU capacity is visible in MPCM, the CAPI team decides how to allocate GPUs across models and regions, deploys models, configures throttling, and monitors usage.

GPU allocation decisions are not limited to receiving new capacity — they also happen when usage patterns shift, when models are deprecated, or when new models need to be onboarded.

For details, see CAPI GPU Allocation.

Team responsibilities
CAPI
Works with AOAI to provision GPUs and models for use by BIC.
Handles onboarding of BIC teams to provided models (GPT-4o, GPT-4o mini, etc.).
Approves incoming GPU capacity requests based on current allocation. Smaller requests are fulfilled directly by CAPI from existing quota; larger requests are reviewed jointly with the COO office.
Ensures the health of the infrastructure via monitoring, throttling, and responding to unexpected GPU shortages.
Provides APIs that allow BIC teams to access models, submit prompts, and benefit from optimizations (caching, model upgrades) without application changes.
Works with BIC teams to upgrade to newer model versions as they become available (accelerated migration efforts). Newer versions typically improve throughput as well as accuracy.
Works with M365 for provisioning agreed-upon scenarios, such as embedded App Builder. M365 pays the GPU costs for these scenarios as they receive the revenue.
COO office
Works with CAPI to facilitate overall capacity forecasting.
Provides tools and reports to determine capacity requirements and current allocation (TPS Manager, BIC AI GPU Allocation and Usage).
Works with Finance to determine overall cost impact, reviewing allocation and requests to evaluate spend and identify reduction opportunities (e.g., cross-region queries rather than expansion in all regions).
Works with IAP, M365, Finance, and CAPI to ensure GPU allocation and accurate long-term signal. IAP provides capacity for non-M365 scenarios.
Reviews large incoming GPU requests jointly with CAPI (those requiring additional quota).
Drives fiscal responsibility and accountability: targeting 80% gross margin, ensuring monetization, and promoting efficiency best practices.
Joint CAPI & COO office
Identify gaps in current capacity management and work to close them (e.g., checklist for rollout).

Getting GPU capacity from 1P Capacity team
This page describes the process by which GPU capacity is allocated to BIC by the 1P Capacity team. This corresponds to Phase 2 of the GPU capacity management overview.

GPU champions
Each organization has designated contacts authorized to request GPU shuffles. The 1P Capacity team limits each organization to exactly two GPU champions (one primary, one backup) and one finance contact. For BIC:

Role	Contact
GPU Champion	Antoine Cellerier
GPU Champion Backup	Arnaud Fabre
GPU Finance Contact	Tory Estes
Only GPU champions (or their backup) are authorized to request a GPU shuffle for GPUs owned by the BIC organization. More details on the GPU champion role are available in the 1P Capacity team documentation (accessible to GPU champions only).

GPU shuffle process
A GPU shuffle is a transfer of GPU quota between subscriptions or teams. It is initiated by sending a standardized email to the 1P Capacity team with a table summarizing the requested changes.

Shuffle request format
The email contains a table with the following columns:

Column	Description
Team Name	The team impacted by the quota change (e.g., BIC).
Quota Type	How the GPU quota should be granted. Most often Manifold, the system used by Azure OpenAI to leverage GPUs.
Public or OOR	Most often set to OOR (Out of Rotation).
Training or Inferencing	Set to Inferencing for our use cases.
Sub ID	The Azure subscription receiving the GPU quota.
Region	The Azure region where the GPUs are located.
GPU SKU	The GPU hardware SKU (e.g., NDm A100 v4).
Current Quota (GPUs)	The current GPU count for this subscription/region/SKU combination.
Requested new quota (GPUs)	The target GPU count after the shuffle.
Notes	Additional context (e.g., existing GPUs in the target subscription).
The most common target subscriptions are:

Subscription	ID	Description
AOAI	78a413a1-488d-4cfe-b055-4ae5ed4595c3	Standard Azure OpenAI stamp
AOAI IB	08c4e780-f415-4316-92c7-469f08deef5c	Azure OpenAI InfiniBand stamp
Important
Unless GPUs have just been plugged in the datacenter, the shuffle table should represent a move: for each GPU SKU and region, quota increases must match quota decreases.

Below is an example of a GPU shuffle request moving NDm A100 v4 GPUs from the AOAI IB stamp to the AOAI stamp across multiple regions:

Team	Quota Type	OOR	Ticket Type	Inferencing	Sub ID	Region	GPU SKU	Current	Requested	Notes
BIC	Manifold	OOR	Quota Decrease	Inferencing	08c4e780-...deef5c	Australia East	NDm A100 v4	48	0	-48 GPUs
BIC	Manifold	OOR	Quota Increase	Inferencing	78a413a1-...4595c3	Australia East	NDm A100 v4	0	48	+48 GPUs
BIC	Manifold	OOR	Quota Decrease	Inferencing	08c4e780-...deef5c	Central US	NDm A100 v4	16	0	-16 GPUs
BIC	Manifold	OOR	Quota Increase	Inferencing	78a413a1-...4595c3	Central US	NDm A100 v4	160	176	+16 GPUs
BIC	Manifold	OOR	Quota Decrease	Inferencing	08c4e780-...deef5c	Japan East	NDm A100 v4	40	0	-40 GPUs
BIC	Manifold	OOR	Quota Increase	Inferencing	78a413a1-...4595c3	Japan East	NDm A100 v4	0	40	+40 GPUs
Tracking
After the email is sent and acknowledged by the 1P Capacity team, the shuffle should be trackable through an incident in the ICM system. If no ICM incident is provided, the 1P Capacity team can be pinged for a tracking reference.

Verifying GPU allocation in MPCM
GPU quotas in this process are not granted directly to CAPI subscriptions — they are granted to Azure OpenAI subscriptions, since that is where direct GPU access is needed. To reflect these grants, Azure OpenAI maintains allotments in the MPCM tool. GPU champions can also check quota status through aka.ms/gpuquota.

Allotments represent quotas granted to teams, scoped by region and GPU or CPU SKU. Once a GPU shuffle is complete, the new capacity should be visible in MPCM under the BIC allotment group.

To verify, navigate to the Capacity Slicer view in MPCM, filter by the BIC allotment group, and confirm the expected quota appears:

MPCM Capacity Slicer showing BIC allotments

Common issues
Buildout delays: GPU buildout can take several days or more, especially when internal capacity issues or mismatches are detected by the 1P Capacity team.

CAPI GPU allocation
This page describes how the CAPI team allocates GPU capacity across models and regions once GPUs are available in MPCM. This corresponds to Phase 3 of the GPU capacity management overview.

When does GPU allocation change?
GPU allocation is not limited to receiving new capacity. It can be triggered by:

New GPU capacity received — After a GPU shuffle completes, new GPUs are available and need to be assigned to models.
Usage pattern changes — Lower or higher usage of some models may warrant reallocating GPUs to better match demand.
New model onboarding — Hosting a new model requires freeing up GPU capacity from existing allocations.
Model end of support — When a model is deprecated, its GPUs can be repurposed for other models.
Model upgrades — Configuring model upgrades shifts traffic from one model to another, which may require adjusting GPU allocation between the two.
Expected traffic changes — Anticipated demand changes, such as large customers with traffic expected to increase in specific regions.
Allocation planning
When an allocation decision needs to be made, the people driving GPU planning review the current state of capacity using two main tools:

MPCM — Provides visibility into which models are deployed, how many GPUs are in use or free, and the overall allocation across regions and stamps.
BIC GPT Dashboard — Shows current model usage, throughput, and consumption trends that help inform reallocation decisions.
Reallocation decisions are the result of various signals:

Current model usage and throughput
Available (unassigned) GPUs
Expected traffic changes (e.g., large customers ramping up in specific regions)
New models coming up or existing models being deprecated
Model upgrade configurations that shift traffic from one model to another
Based on this analysis, the team decides what scale-up or scale-down operations are needed.

Execution
Tracking
All ongoing, planned, and recently completed capacity shuffle tasks are tracked in the PAES Capacity Shuffles ADO query. Each work item describes exactly what changes need to happen: which models, which regions, and how many GPUs to scale up or down. See work item #36682439 for an example.

Working on a task
When picking up a capacity shuffle task:

Assign the task to yourself so that others know who is working on it.
Add a comment for each step completed — for example, creating the PR, provisioning the model, updating CAPI's model deployment registration, applying throttling, etc. If errors are encountered, add them as comments as well. This makes it easier for team members across time zones to follow progress and pick up where someone left off.
Mark the task as done once the capacity shuffle is fully complete — i.e., the model deployment is done and actively serving traffic, or the deployment has been deleted if the shuffle was for a removal.
Cross-timezone handoffs
If a task cannot be completed in a single shift and needs to be continued by someone in another time zone, the current owner should sync with the person taking over to ensure the handoff is acknowledged and context is transferred.

Related pages
MPCM role assignments (Vienna repo) — Where MPCM manages permissions to the tool. Members of the AP-PowerAiMl-RW-aca4 security group have write access to BIC's allotment. For any MPCM-related questions, contact Yunjie Zhang (yunzhan).
Getting GPU Capacity from 1P Capacity team — How GPUs are allocated to BIC by the 1P Capacity team (Phase 2).
LLM Capacity per model — Understanding capacity types (PTU-C, PTU-M, PayAsYouGo) and throughput per model.
Manually Deploying a new Azure OpenAI model — Step-by-step deployment procedures.
Kusto logs for capacity and consumption — Monitoring GPU usage and throughput.