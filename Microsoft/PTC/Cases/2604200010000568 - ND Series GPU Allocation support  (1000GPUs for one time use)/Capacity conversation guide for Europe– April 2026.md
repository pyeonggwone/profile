Capacity conversation guide for Europe– April 2026
Last updated April 14th , 2026
The following example conversation script has been developed to help field sellers discuss the capacity situation 
in Europe with their customers. This document is Microsoft Confidential. You may customize it to address your customers 
specific resource asks. As a reminder, please DO NOT engage the press directly – leverage corporate communications to 
respond to press inquiries.
Please check aka.ms/azurecapacity for answers to common questions, the latest mitigation timelines and guidance to 
escalate urgent customer requests
Due to sustained high demand, Microsoft has implemented capacity preservation measures in a few Europe regions. 
These measures prioritize existing customers and include:
• Quota restrictions for new customers and additional scrutiny for quota increases.
• Deployment prioritization to prevent capacity exhaustion and reduce failure rates.
• Disaster recovery unaffected: Microsoft has reserved headroom for DR workloads.
Europe regions impacted (in order of resolution timeline):
• North Europe has restrictions across 3 Availability Zones (AZ). AZ01,AZ02 and AZ03 have Long Term Constraints 
until FY29 H1
• Note: Recent updates to the constraints in North Europe are largely due to Ireland’s energy policy. 
Capacity restrictions are in place to prioritize growth of existing workloads in the region.
• Germany West Central has internal-only restrictions on 3 AZs. AZ01 and AZ02 has a long-term constraint till end 
of FY27 H1. AZ03 have short term constraints until June 2026.
• UK South has restrictions across all AZs. AZ01 and AZ03 have long term constraints until September 2026 and 
February 2027 respectively. AZ02 has short term restrictions until June 2026. Learn more.
• Spain Central has restrictions on 1 AZ. AZ02 has Long Term Constraints until FY27 H1.
• West Europe AZ01 has short term constraints until April 2026, AZ02 and AZ03 have Long Term Constraints, 
resolution timeline is TBD.
• Note: Recent media articles about a new datacenter in Amsterdam, connected to Microsoft, are creating 
confusion with customers about the need to shape growth out of the West Europe region. Any
expansion of our West Europe region would be several years into the future and be prioritized for 
organic growth of existing workloads. Existing Offer Restrictions are not being removed.
• France Central AZ01 has long term constraints with all new subscriptions being restricted and resolution time 
FY30 H1. AZ03 has long term constraints with free and internal subscriptions being restricted until FY28 H1.
AZ02 has a short term constraint with free and internal subscriptions being restricted until May 2026.
• Italy North has internal-only restrictions on 3 AZs until FY28 H1.
• Switzerland North has internal-only restrictions on AZ03 until FY28 H1.
• Norway East has restrictions across 3 AZ’s, with the resolution time TBD. Learn more.
Recommended Actions: 
• Capacity- Capacity fluctuates daily and varies by SKU, please check aka.ms/azurecapacity for the latest 
status. Microsoft recommends new workloads should target the following regions:
o Sweden Central
o Italy North 
o Other options for edge cases, the following regions can also be leveraged: Germany West Central, 
Austria East, Denmark East, Poland Central, and Switzerland North.
• Zone requirementso 3-zone deployments: For customers requiring 3 healthy zones, Sweden Central and Italy North are the 
best viable alternative for customers. You can also leverage other options for edge cases: Germany West 
Central, Austria East, Denmark East, Poland Central, and Switzerland North. Learn more about Azure 
services that provide support for Availability Zones, and may be impacted.
o 2-zone deployments: For customers requiring 2 healthy zones, the best viable alternatives for customers 
includes: Sweden Central, Italy North, Spain Central. You can also leverage other options for edge cases:
Germany West Central, Austria East, Denmark East, Poland Central, and Switzerland North
o Non-zonal deployments: For customers without any zonal requirements (1 zone only), the best viable 
alternatives for customers includes: Sweden Central, Italy North, Spain Central, France Central. You can 
also leverage other options for edge cases: Germany West Central, Austria East, Denmark East, Poland 
Central, and Switzerland North
• Multi-region strategy- To ensure quota approval, deployment success and scalability, customers are encouraged 
to:
o Consider leveraging a multi-region strategy A multi-region approach achieves high availability, ensures 
resiliency, and enables advanced scalability. Customers can also consider alternate regions for their zonal 
deployment.
• Data Sovereignty- Capex so high now that the markets didn’t like it, but it is the right thing for us to do 
o For customers citing in-country data sovereignty requirements in their existing regions, evaluate whether a 
digital data sovereignty approach including Customer Managed Keys, Azure Key Vault Managed HSM, and/or 
Azure Confidential Compute can be used together with an alternate EU-based growth region can address the 
customer's sovereignty requirements. For customer scenarios where in-country physical data residency is 
still required, leverage the UAT process. 
o UAT process is open to all customers and will be triaged by a joint MCAPS-Engineering triage team to 
determine if supportability is possible. Important questions we assess with each UAT:
▪ Why does the workload have to be in that region, or are other regions possible (e.g. Sweden)
▪ Does the workload zonal (AZ’s) requirements, or is non-zonal an option?
▪ What is the minimum # cores needed now and do you have a ramp plan of the customer's needs
▪ Is there SKU flexibility (e.g. AMD vs Intel, older generation SKUs, etc…)
▪ When is the capacity needed? When does the actual milestone start?
▪ Are we able to reclaim the capacity after a certain event (holiday retail season) or period of time? 
Additional Communication
You can also consider alternate SKU’s that might suffice your workload needs. If none of these alternates work for the 
customer, please follow the escalation process.
We are continuing to closely monitor the situation and working to increase available capacity in line with customer 
demand signals. 
In the meantime, several Microsoft teams are working around the clock to identify solutions to help meet 
your additional capacity requests to ensure continued growth. Representatives from our product team and DC Leads 
from each time zone join frequent status calls with our teams to ensure clear transparency and prioritization until these 
preventative restrictions are lifted.  
We will work with you on a regular update cadence, and share more information about your specific quota requests, and 
the ongoing efforts to expand our cloud infrastructure in the region. We apologize for the inconvenience and extra work 
that these preventative measures represent and stand ready to assist you in successfully running and growing your 
business in our Europe datacenters and beyond.
If you have any questions or feedback, please email us at Capcomms@microsoft.com 
The Big Picture
The Microsoft Cloud spans over 80 datacenter regions, more than any cloud provider. Our cloud footprint continues to grow as we 
add more regions and datacenters all over the world to meet our growing customer and partner needs; including general availability 
of our newest regions in Europe: Austria East, Belgium Central and Denmark East, with our intent to build a second datacenter 
region in Denmark. We will continue to expand and strengthen our infrastructure across Europe through investments to drive 
economic growth and technological advancement in the AI era. Our most recent investment announcements in Switzerland and the 
United Kingdom, help pave the way for this expansion, while partnerships with Nscale help drive additional AI infrastructure in 
Norway and Portugal. Looking ahead, Azure will continue to drive innovation in cloud infrastructure and AI-powered services, 
providing the choice and flexibility businesses need to meet evolving requirements.