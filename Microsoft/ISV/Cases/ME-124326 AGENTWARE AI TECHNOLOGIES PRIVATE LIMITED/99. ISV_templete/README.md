SaaS Offer: 

Marketplace Overview 

Before selling offers in the commercial marketplace, you need to set up a payout account and fill out tax forms in Partner Center. 

Microsoft charges a 3% standard store service fee when customers purchase your transactable offer from the commercial marketplace. Microsoft commercial marketplace transact capabilities - Marketplace publisher | Microsoft Learn 

There is a general policy for publishing the application to Microsoft Commercial Marketplace. The policies apply to all offer types. The commercial marketplace certification policies can be found here: Commercial marketplace certification policies. 

  

Making your published application to transactable offer 

To sell through Microsoft (called transactable offer) and have Microsoft facilitate transactions for you, select Yes on the Offer setup tab, under Setup details. Create a SaaS offer in the commercial marketplace. - Marketplace publisher | Microsoft Learn 

Define preview audience who can review your offer listing before it goes live. Add a preview audience for a SaaS offer in Azure Marketplace - Marketplace publisher | Microsoft Learn 

The Supplemental Content page for SaaS offers gathers additional information about the functionality and structure of your SaaS offer. This information is used to enable the Microsoft Commercial Marketplace team to validate that your transactable SaaS offer is primarily platformed on Azure and following the marketplace policies for listing. These listing and certification policies can be found here: SaaS offer policies. 

  

Technical configuration 

Before can publish a SaaS offer, the SaaS application must meet technical requirements. Basically, technical details which the commercial marketplace will communicate to the SaaS application like landing page URL, connection webhook, Azure Active Directory tenant ID and Azure Active Directory application ID. 

Landing page URL: The SaaS site URL that users will be directed to after acquiring your offer from the commercial marketplace, triggering the configuration process from the newly created SaaS subscription. 

Your landing page should be up and running 24/7. This is the only way you will be notified about new purchases of your SaaS offers made in the commercial marketplace, or configuration requests of an active subscription of an offer. 

Building the landing page for your transactable SaaS offer in the commercial marketplace. Build the landing page for your transactable SaaS offer in the commercial marketplace - Marketplace publisher | Microsoft Learn  

The commercial marketplace manages the entire life cycle of a SaaS subscription after its purchase by the end user. It uses the landing page, Fulfillment APIs, Operations APIs, and the webhook as a mechanism to drive the actual SaaS subscription activation, usage, updates, and cancellation.  

Active (Subscribed) is the steady state of a provisioned SaaS subscription. After the Microsoft side has processed the Activate Subscription API call, the SaaS subscription is marked as Subscribed. The customer can now use the SaaS service on the publisher's side and is billed. 

How to find the application ID.  

The SaaS fulfilment APIs enable publishers to publish and sell their SaaS applications in the marketplace. Integrating with these APIs is a requirement for creating and publishing a transactable SaaS offer in Partner Center. 

Connection webhook: For all asynchronous events that Microsoft needs to send to you (for example, when SaaS subscription cancelled), we require you to provide a connection webhook URL. We will call this URL to notify you of the event. 

The webhook URL service must be up and running 24x7, and ready to receive new calls from Microsoft time at all times. Microsoft does have a retry policy for the webhook call (500 retries over 8 hours), but if the publisher doesn't accept the call and return a response, the operation that webhook notifies about will eventually fail on the Microsoft side.  

Pricing Model 

Offers sold through Microsoft marketplace must have at least one plan. Create plans for a SaaS offer in Azure Marketplace - Marketplace publisher | Microsoft Learn  

All plans in the same offer must use the same pricing model. For example, an offer can't have one plan that's flat rate and another plan that's per user. 

After your offer is published, you can't change the pricing model. In addition, all plans for the same offer must share the same pricing model. 

All prices input is in USD and converted into local currency of all selected markets using the exchange rate at the time of page save. Learn more about configuring price options. The amount that customers pay, and that ISVs are paid, depends on the Foreign Exchange rates at the time the customer transacts the offer. Learn more on "How we convert currency?". 

There are a few pricing models available: flat rate or per user. All plans in the same offer must use the same pricing model. There is another pricing model - custom meter dimension (consumption based). This option is available only if you select flat rate pricing. 

Flat rate – Enable access to your offer with a single monthly or annual flat rate price. This is sometimes referred to as site-based pricing. With this pricing model, you can optionally define metered plans that use the marketplace metering service API to charge customers for usage that isn't covered by the flat rate. 

Per user – Enable access to your offer with a price based on the number of users who can access the offer or occupy seats. With this user-based model, you can set the minimum and maximum number of users supported by the plan. You can create multiple plans to configure different price points based on the number of users. These fields are optional. If left unselected, the number of users will be interpreted as not having a limit (min of 1 and max of as many as your service can support). The min or max number of users cannot be edited as part of an update to your plan. 

You can create SaaS offers that are charged according to non-standard units with metering service. You can define the billing dimensions such as bandwidth, tickets, or email processed. Customers will pay according to their consumption of these dimensions, with your system informing Microsoft via the commercial marketplace metering service API of billable events as they occur. 

You can configure a free trial for each plan in your offer. Select the check box to allow a one-month free trial. This check box isn't available for plans that use the marketplace metering service. 

  

Landing Page and webhook: 

Option 1: SaaS accelerator 

SaaS accelerator (creates from scratch Landing Page and Admin Portal) : Mastering the SaaS Accelerator - Mastering the Marketplace (microsoft.github.io) 

 Repository with SaaS Accelerator (C#, ASP .NET MVC): Azure/Commercial-Marketplace-SaaS-Accelerator: A reference example with sample code for developers … 

 Commercial Marketplace SaaS API Emulator (locally mocks Marketplace APIS): microsoft/Commercial-Marketplace-SaaS-API-Emulator: An emulator for the Microsoft commercial market… 

 SaaS samples: commercial-marketplace-solutions/saas-samples/saas-with-metered-engine/src at main · microsoft/comm… 

 Sample Landing Page: neelavarshad/SaaS-Demo 

Postman collections to trigger Marketplace APIs:  commercial-marketplace-solutions/saas-samples/saas-with-metered-engine/Postman at main · microsoft/… 

SaaS accelerator will provide landing page, a webhook that listens for subscription changes, a private portal for the publisher to monitor customer subscription. 

The SaaS Accelerator provides a fully functional community-led SaaS reference implementation for those interested in publishing SaaS offers in Microsoft’s marketplace in hours instead of days. This series of video modules and hands-on labs is designed to help you understand, install, use, and customize the SaaS Accelerator project. 

   Attached is the SaaS offer publication checklist for preparing your publication. 

Additional resources 

Mastering SaaS offers. Mastering SaaS offers - Mastering the Marketplace (microsoft.github.io)  

Mastering SaaS offers for developers. Mastering SaaS offers for developers - Mastering the Marketplace (microsoft.github.io) 

  

Option 2: Custom Landing Page: 

Landing page URL  

Follow this guide to create the Landing page and App Registration for Entra ID - Build the landing page for your transactable SaaS offer in the commercial marketplace  

Hands-on lab example: Creating a Landing Page  

Video guide to build a simple landing page - Building a simple landing page in .NET  

Entra ID configuration guide - Microsoft Entra ID configuration for your SaaS offer  

SaaS fulfilment API guide - Using the SaaS offer fulfillment API  

  

Connection Webhook  
Follow this guide to create the Implementing a webhook on the SaaS service  

Watch this Webhook overview guide - SaaS webhook overview 

Watch this demo on implementing a Webhook in .NET - Implementing a simple SaaS webhook in .NET  

Follow this hands-on lab example - Deploying and Monitoring a Webhook  

Review the different webhook events - Implementing a webhook on the SaaS service  

 

 

 

 

 

 

 

 

AZURE MANAGED APPLICATION OFFER: 

Azure Managed Application offer 

Azure Managed Applications enable deploying your solution's resources via an ARM template into the customer's tenant. Further, they enable the publisher to restrict customer access to deployed resources. 

Azure Application Offers allows you to deploy and configure your solution using Azure Resource Manager templates, which can include various Azure resources such as VMs, containers, storage, and more. You can also choose to manage your solution for your customers, or let them manage it themselves. Azure Application offers can be configured as Solution Templates or Managed Applications. 

An Azure managed application plan is one way to publish an Azure application offer in the Commercial Marketplace. 

With Managed applications publishers can choose to:  

Enable or disable publisher management access to the resource group in the customer tenant.  

Give customers full or restricted access to the resource group. 

Plan an Azure Application offer. Plan an Azure Application offer for the commercial marketplace - Marketplace publisher | Microsoft Learn 

Plan an Azure managed application for an Azure application offer. Plan an Azure managed application for an Azure application offer - Marketplace publisher | Microsoft Learn 

Prepare the technical assets for Azure application. Prepare the technical assets for Azure application - Marketplace publisher | Microsoft Learn 

Create an Azure application offer. Create an Azure application offer in Azure Marketplace - Marketplace publisher | Microsoft Learn 

Configure Azure application offer properties. How to configure your Azure Application offer properties - Marketplace publisher | Microsoft Learn 

Configure your Azure application offer listing details. Configure your Azure application offer listing details - Marketplace publisher | Microsoft Learn 

Add a preview audience for an Azure Application offer. Add a preview audience for an Azure Application offer - Marketplace publisher | Microsoft Learn 

Technical details for an Azure application offer. Add technical details for an Azure application offer - Marketplace publisher | Microsoft Learn 

Configure a managed application plan. Configure a managed application plan - Marketplace publisher | Microsoft Learn 

The metered billing APIs should be used when the publisher creates custom metering dimensions for an offer to be published in Partner Center. Integration with the metered billing APIs is required for any purchased offer that has one or more plans with custom dimensions to emit usage events. 

The deployment package contains all the template files needed for this plan, as well as any additional resources, packaged as a .zip file. 

All Azure applications must include these two files in the root folder of a .zip archive: 

A Resource Manager template file named mainTemplate.json. This template defines the resources to deploy into customer’s Azure subscription. 

A user interface definition for the Azure application creation experience named createUiDefinition.json. In the user interface, you specify elements that enable customers to provide parameter values. 

After creating the createUiDefinition.json file for your managed application, you need to test the user experience. To simplify testing, use a sandbox environment that loads your file in the portal. The sandbox is the recommended way to preview the interface. 

There is a general policy for publishing the application to Microsoft Commercial Marketplace. The policies apply to all offer types. The commercial marketplace certification policies can be found here: Azure Managed Application offer policies. 

ARM Template 

To implement infrastructure as code for your Azure solutions, use Azure Resource Manager templates (ARM templates). The template is a JavaScript Object Notation (JSON) file that defines the infrastructure and configuration for your project. 

Structure and syntax of ARM templates. Template structure and syntax - Azure Resource Manager | Microsoft Learn 

ARM template best practices. Best practices for templates - Azure Resource Manager | Microsoft Learn 

ARM template test toolkit. ARM template test toolkit - Azure Resource Manager | Microsoft Learn 

Parameters in ARM templates. Parameters in templates - Azure Resource Manager | Microsoft Learn 

View createUIDefinition using createUIDefinition Sandbox. 

ARM template test toolkit. ARM template test toolkit - Azure Resource Manager | Microsoft Learn 

Similar to a role assignment, a deny assignment attaches a set of deny actions to a user, group, or service principal at a particular scope for the purpose of denying access. Deny assignments block users from performing specific Azure resource actions even if a role assignment grants them access. 

JIT (Just In Time) access enables you to request elevated access to a managed application's resources for troubleshooting or maintenance. You always have read-only access to the resources, but for a specific time period you can have greater access. 

You can optionally specify which actions customers can perform on the managed resources in addition to the */read actions that is available by default. For available action, see Azure Resource Manager resource provider operations 

ARM template sample for your reference. azure-quickstart-templates/quickstarts at master · Azure/azure-quickstart-templates · GitHub 

Azure ARM template - ARM template documentation | Microsoft Learn 

How Metered Billing Works for Managed Applications 

Supported Only for Managed Application Plans: Metered billing is available exclusively for managed application plans in Azure Marketplace (not for solution templates). [Metered bi...soft Learn] 

Marketplace Metering Service API: Your application must integrate with the Marketplace metering service API to report billable events (e.g., transactions, usage units) to Microsoft. [learn.microsoft.com] 

Pricing Model: 

A base monthly fee (can be $0 if you want to rely entirely on usage-based billing). 

Billing dimensions for usage beyond the base rate (e.g., per transaction, per user, per API call). [techcommun...rosoft.com] 

Custom Dimensions: You can define up to 30 billing dimensions per plan in Partner Center. Each dimension represents a measurable unit (e.g., “pages scanned,” “API calls”). [microsoft.github.io] 

Additional resources 

Mastering Managed Application Offers. Mastering Managed Application Offers - Mastering the Marketplace (microsoft.github.io) 

Azure Managed App Samples. commercial-marketplace-solutions/azure-application-samples at main · microsoft/commercial-marketplace-solutions · GitHub 

ARM template sample for your reference. azure-quickstart-templates/quickstarts at master · Azure/azure-quickstart-templates · GitHub 

 

 

 

 

 

 

 

 

 

 

 

 

 

The Azure Virtual Machine offer : 

 VM offer prerequisites (technical & org) 

Use Azure Compute Gallery and ensure VHD ➜ image definition ➜ image version are correctly created (Gen1/Gen2, OS family, ports, etc.). Start here: “Create a VM using your own image” (Learn) and “Create an image definition and image version” (Learn | Azure China site mirror). 

Same-tenant requirement: The Azure Compute Gallery must be in the same Microsoft Entra tenant that’s linked to your Partner Center account; the publisher must have Owner on the subscription hosting the gallery. (Learn) 

Partner Center access to your gallery (service principals): Microsoft has moved to a more secure acquisition process that requires you to register the Partner Center resource provider and provision service principals so Partner Center can read your gallery. Follow the steps in the “Provide Partner Center permission to your Azure Compute Gallery” section of the same article. (Learn) 

RBAC: fix the “cannot read image version” validation 

The error you saw is typically caused by RBAC applied at the wrong scope or missing Reader permissions. Apply RBAC at the GALLERY (not only the resource group / image version): 

Scope: go to your Compute Gallery ➜ Access control (IAM) ➜ Add role assignment. 

Role: Reader (minimum needed for Partner Center ingestion); in some org setups, you may temporarily grant Owner to the human publisher account to proceed, but Reader on the gallery for the Partner Center service principal is the key. (Learn | Azure China site mirror) 

Assign to: the service principal(s) provisioned when you registered the Partner Center RP (per step 2.1). (Learn) 

Checklist to re-run validation successfully: 

Gallery is in same Entra tenant as Partner Center (Learn) 

Partner Center RP registered, service principals provisioned (Learn) 

Reader role at gallery scope to the Partner Center SP (Learn) 

Image definition/version exist and are Active with regions replicated if required (Learn) 

Owner in the gallery subscription (Learn) 

Partner Center configuration (VM offer) 

Create offer & plan following “Create a VM offer” (Learn). 

Plan ➜ Technical configuration: set OS family, recommended sizes, open ports, select the image version from your gallery once RBAC is fixed. (Learn) 

Preview audience: add Azure subscription IDs to test end-to-end before full publish. (Learn | Add preview audience) 

Guidance & labs: Mastering the Marketplace – VM (walkthroughs, labs) (GitHub Pages | Lab: publish VM offer). 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

PRIVATE OFFER: 

To create a private offer in the Microsoft Commercial Marketplace, especially for SaaS solutions, here’s a comprehensive step-by-step guide : 

 Step-by-Step: Creating a Private Offer 

Step 1: Prepare Your Account 

Before you begin, ensure: 

Your billing account ID is correctly configured. 

You have the necessary roles and permissions (e.g., Marketplace developer, manager, or account owner). 

Your offer is already published and publicly transactable in Partner Center [1]. 

Use the Private Offer Management dashboard in the Azure portal to track and manage offers [2]. 

  

Step 2: Create the Private Offer 

Sign in to Partner Center and go to the Marketplace Offers Workspace. 

Select Private Offers from the left menu. 

Click + New Private Offer. 

Choose the customer and enter a descriptive name. 

Select the offer type: 

Customize pricing for existing public offers (SaaS, Azure VMs, etc.) 

Create new customized plans (for SaaS or professional services) 

VM software reservations (1-year or 3-year terms) [1]. 

Define: 

Pricing (absolute or percentage discounts) 

Metering dimensions 

User limits 

Start and end dates 

Legal terms (optional PDF attachment) 

  

Step 3: Accept the Private Offer 

Once the offer is created: 

The customer receives an email or accesses the Azure portal. 

They must accept the offer via the Private Offer Management dashboard. 

This step forms a binding contract between the publisher and customer [2]. 

  

Step 4: Purchase and Subscribe 

After acceptance: 

The customer must complete the purchase in Azure Marketplace. 

They assign the purchase to a subscription and resource group. 

For SaaS offers, they must activate the product to begin usage [3]. 

  

Additional Considerations 

Avoid Overlapping Offers 

Ensure no overlapping private offers exist for the same customer, plan, and billing account ID. Overlaps are blocked at submission [5]. 

Checklist for Readiness 

Refer to the ​Marketplace private offer checklist​ for: 

Billing setup 

Role verification 

Offer acceptance and purchase flow ​[6]​ 

  

References 

[1] Manage ISV-to-customer private offers - Marketplace publisher 

[2] Step 2 - Accept the private offer - Marketplace customer documentation ... 

[3] Step 3 - Purchase and Subscribe to the Private Offer - Marketplace ... 

[5] Frequently asked questions about ISV-to-customer private offers. - Marketplace publisher | Microsoft Learn 

[6] ​Marketplace private offer checklist​ 

[7] Private offers overview - Marketplace customer documentation 

 