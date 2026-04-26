# Azure Setup

## 1. Resource Group

1. Azure Portal > Resource groups > Create
2. Subscription: `<AZURE_SUBSCRIPTION_ID>`
3. Resource group: `<AZURE_RESOURCE_GROUP>`
4. Region: `Korea Central`
5. Review + create > Create

## 2. Microsoft Entra ID / App Registration

1. Azure Portal > Microsoft Entra ID > App registrations > New registration
2. Name: `app-medicalai-local-runtime`
3. Supported account types: `Accounts in this organizational directory only`
4. Redirect URI: 입력 안 함
5. Register
6. Overview > Application (client) ID 복사 > `.env`의 `AZURE_CLIENT_ID`
7. Overview > Directory (tenant) ID 복사 > `.env`의 `AZURE_TENANT_ID`
8. Certificates & secrets > Client secrets > New client secret
9. Description: `medicalai-local-runtime-secret`
10. Expires: `12 months`
11. Add
12. Value 복사 > `.env`의 `AZURE_CLIENT_SECRET`

## 3. Azure Container Registry

1. Azure Portal > Container registries > Create
2. Subscription: `<AZURE_SUBSCRIPTION_ID>`
3. Resource group: `<AZURE_RESOURCE_GROUP>`
4. Registry name: `acrmedicalai<unique>`
5. Location: `Korea Central`
6. SKU: `Basic`
7. Review + create > Create
8. Container registry > Overview > Login server 복사 > `.env`의 `ACR_LOGIN_SERVER`
9. Container registry > Access control (IAM) > Add > Add role assignment
10. Role: `AcrPull`
11. Assign access to: `User, group, or service principal`
12. Members: `app-medicalai-local-runtime`
13. Review + assign
14. Container registry > Repositories > 확인 대상:
    - `data-sender`
    - `pii-processor`
    - `remote-update-agent`
    - `medicalai-monitor`

## 4. Azure Storage Account

1. Azure Portal > Storage accounts > Create
2. Subscription: `<AZURE_SUBSCRIPTION_ID>`
3. Resource group: `<AZURE_RESOURCE_GROUP>`
4. Storage account name: `stmedicalai<unique>`
5. Region: `Korea Central`
6. Performance: `Standard`
7. Redundancy: `Locally-redundant storage (LRS)`
8. Review + create > Create
9. Storage account > Overview > Storage account name 복사 > `.env`의 `AZURE_STORAGE_ACCOUNT`
10. Storage account > Data storage > Containers > + Container
11. Name: `medicalai-test`
12. Public access level: `Private`
13. Create
14. `.env`의 `AZURE_STORAGE_CONTAINER`: `medicalai-test`
15. Storage account > Access control (IAM) > Add > Add role assignment
16. Role: `Storage Blob Data Reader`
17. Assign access to: `User, group, or service principal`
18. Members: `app-medicalai-local-runtime`
19. Review + assign
20. Storage account > Access control (IAM) > Add > Add role assignment
21. Role: `Storage Blob Data Contributor`
22. Assign access to: `User, group, or service principal`
23. Members: `app-medicalai-local-runtime`
24. Review + assign
25. Storage account > Data storage > Containers > `medicalai-test` > Upload
26. Upload file: `release-manifest.json`
27. `.env`의 `UPDATE_SOURCE_URL`: `https://<AZURE_STORAGE_ACCOUNT>.blob.core.windows.net/medicalai-test/release-manifest.json`

## 5. Azure Event Hubs

1. Azure Portal > Event Hubs > Create
2. Subscription: `<AZURE_SUBSCRIPTION_ID>`
3. Resource group: `<AZURE_RESOURCE_GROUP>`
4. Namespace name: `evhns-medicalai-<unique>`
5. Location: `Korea Central`
6. Pricing tier: `Basic` 또는 `Standard`
7. Throughput units: `1`
8. Review + create > Create
9. Event Hubs Namespace > Overview > Name 복사 > `.env`의 `AZURE_EVENTHUB_NAMESPACE`
10. Event Hubs Namespace > Entities > Event Hubs > + Event Hub
11. Name: `evh-medicalai-pii-processed`
12. Partition count: `2`
13. Message retention: `1 day`
14. Create
15. `.env`의 `AZURE_EVENTHUB_NAME`: `evh-medicalai-pii-processed`
16. Event Hubs Namespace > Access control (IAM) > Add > Add role assignment
17. Role: `Azure Event Hubs Data Sender`
18. Assign access to: `User, group, or service principal`
19. Members: `app-medicalai-local-runtime`
20. Review + assign

## 6. Log Analytics Workspace

1. Azure Portal > Log Analytics workspaces > Create
2. Subscription: `<AZURE_SUBSCRIPTION_ID>`
3. Resource group: `<AZURE_RESOURCE_GROUP>`
4. Name: `log-medicalai-local-runtime`
5. Region: `Korea Central`
6. Review + create > Create
7. Log Analytics workspace > Agents > Log Analytics agent instructions > Workspace ID 복사
8. Log Analytics workspace > Agents > Log Analytics agent instructions > Primary key 복사
9. Log Analytics workspace > Access control (IAM) > Add > Add role assignment
10. Role: `Log Analytics Contributor`
11. Assign access to: `User, group, or service principal`
12. Members: `app-medicalai-local-runtime`
13. Review + assign

## 7. .env 입력값

```text
AZURE_TENANT_ID=<Directory tenant ID>
AZURE_SUBSCRIPTION_ID=<Subscription ID>
AZURE_RESOURCE_GROUP=<Resource group name>
AZURE_LOCATION=koreacentral
AZURE_CLIENT_ID=<Application client ID>
AZURE_CLIENT_SECRET=<Client secret value>
ACR_LOGIN_SERVER=<ACR login server>
AZURE_STORAGE_ACCOUNT=<Storage account name>
AZURE_STORAGE_CONTAINER=medicalai-test
AZURE_EVENTHUB_NAMESPACE=<Event Hubs namespace name>
AZURE_EVENTHUB_NAME=evh-medicalai-pii-processed
UPDATE_SOURCE_URL=https://<AZURE_STORAGE_ACCOUNT>.blob.core.windows.net/medicalai-test/release-manifest.json
```
