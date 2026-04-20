# 구현 가이드: Entra ID 테넌트 간 동기화

> 적용 시나리오: MedicalAI 한국 마스터 테넌트 ↔ 미국 테넌트 간 운영자 계정 자동 동기화  
> 옵션 A (Cross-Tenant Synchronization) 기준 — GA 공식 기능

---

## 전제조건

- 소스 테넌트 (한국 마스터): Global Administrator 또는 Application Administrator 권한
- 대상 테넌트 (미국): Global Administrator 또는 Application Administrator 권한
- 두 테넌트 모두 Microsoft Entra ID P1 이상 라이선스 필요

---

## Step 1. 대상 테넌트에서 Cross-Tenant 접근 허용

대상 테넌트(미국) 관리자가 실행:

```powershell
# Microsoft Graph PowerShell 모듈 설치
Install-Module Microsoft.Graph -Scope CurrentUser

# 대상 테넌트로 로그인
Connect-MgGraph -TenantId "<TARGET_TENANT_ID>" `
  -Scopes "Policy.ReadWrite.CrossTenantAccess"

# Cross-Tenant Access Policy — 소스 테넌트의 사용자 동기화 허용
$params = @{
    tenantId = "<SOURCE_TENANT_ID>"   # 한국 마스터 테넌트 ID
    b2bCollaborationInbound = @{
        usersAndGroups = @{
            accessType = "allowed"
            targets = @(@{
                target = "AllUsers"
                targetType = "user"
            })
        }
        applications = @{
            accessType = "allowed"
            targets = @(@{
                target = "AllApplications"
                targetType = "application"
            })
        }
    }
    inboundTrust = @{
        isMfaAccepted = $true         # 소스 테넌트 MFA 신뢰
        isCompliantDeviceAccepted = $false
        isHybridAzureADJoinedDeviceAccepted = $false
    }
}

New-MgPolicyCrossTenantAccessPolicyPartner -BodyParameter $params
```

---

## Step 2. 소스 테넌트에서 Cross-Tenant Sync 설정

소스 테넌트(한국) 관리자가 실행:

```powershell
# 소스 테넌트로 로그인
Connect-MgGraph -TenantId "<SOURCE_TENANT_ID>" `
  -Scopes "Policy.ReadWrite.CrossTenantAccess","Synchronization.ReadWrite.All","Application.ReadWrite.All"

# Cross-Tenant Sync 활성화 (소스 → 대상 방향)
$params = @{
    tenantId = "<TARGET_TENANT_ID>"
    b2bCollaborationOutbound = @{
        usersAndGroups = @{
            accessType = "allowed"
            targets = @(@{
                target = "AllUsers"
                targetType = "user"
            })
        }
    }
    automaticUserConsentSettings = @{
        inboundAllowed = $true
        outboundAllowed = $true       # 동의 없이 자동 프로비저닝
    }
}

Update-MgPolicyCrossTenantAccessPolicyPartner -CrossTenantAccessPolicyConfigurationPartnerTenantId "<TARGET_TENANT_ID>" `
  -BodyParameter $params
```

---

## Step 3. 동기화 앱(Service Principal) 생성

```powershell
# Entra Admin Center 방식 (포털): 
# Entra ID > External Identities > Cross-tenant synchronization > Configurations > New configuration

# CLI/Graph API 방식:
$appParams = @{
    displayName = "MedicalAI-CrossTenantSync-KR-to-US"
    description = "한국 마스터 → 미국 테넌트 운영자 계정 동기화"
}

$app = New-MgApplication -BodyParameter $appParams
$sp = New-MgServicePrincipal -AppId $app.AppId

Write-Host "Service Principal ID: $($sp.Id)"
Write-Host "App ID: $($app.AppId)"
```

---

## Step 4. 동기화 범위(Scope) 필터 설정

운영자 계정만 동기화, 병원 게스트 계정 제외:

```powershell
# 동기화 대상 그룹 생성 (소스 테넌트에서)
$groupParams = @{
    displayName = "SyncGroup-MedicalAI-Operators"
    description = "미국 테넌트로 동기화할 MedicalAI 운영자"
    mailEnabled = $false
    securityEnabled = $true
    mailNickname = "syncgroup-operators"
}
$syncGroup = New-MgGroup -BodyParameter $groupParams

# 동기화 대상 멤버 추가 예시
Add-MgGroupMember -GroupId $syncGroup.Id -DirectoryObjectId "<USER_OBJECT_ID>"
```

Entra Admin Center에서 범위 필터 설정:

```
경로: Cross-tenant synchronization > [설정명] > Provisioning > Mappings > 
      Provision Azure Active Directory Users > Source Object Scope

필터 조건:
  속성: department
  연산자: EQUALS
  값: MedicalAI-Operations

  또는

  속성: isMemberOf
  연산자: ISMEMBEROF
  값: SyncGroup-MedicalAI-Operators 그룹 ObjectID
```

---

## Step 5. 속성 매핑 설정

동기화 시 대상 테넌트로 전달할 속성 정의:

| 소스 속성 (한국 테넌트) | 대상 속성 (미국 테넌트) | 매핑 유형 |
|------------------------|------------------------|----------|
| `userPrincipalName` | `userPrincipalName` | Direct |
| `displayName` | `displayName` | Direct |
| `mail` | `mail` | Direct |
| `department` | `department` | Direct |
| `jobTitle` | `jobTitle` | Direct |
| `"true"` | `showInAddressList` | Constant |
| `"Member"` | `userType` | Constant — Guest 아닌 Member로 생성 |

Breakglass 계정 동기화 제외 (필수):

```powershell
# Breakglass 계정에 동기화 제외 속성 태그
Update-MgUser -UserId "<BREAKGLASS_USER_ID>" `
  -AdditionalProperties @{
    "extensionAttribute1" = "ExcludeFromSync"
  }

# 범위 필터에 제외 조건 추가
# extensionAttribute1 NOTEQUALS ExcludeFromSync
```

---

## Step 6. 동기화 실행 및 모니터링

```powershell
# 동기화 작업 ID 조회
$syncJobId = (Get-MgServicePrincipalSynchronizationJob -ServicePrincipalId $sp.Id).Id

# 온디맨드 동기화 (테스트)
Invoke-MgSynchronizationServicePrincipalJobOnDemand `
  -ServicePrincipalId $sp.Id `
  -SynchronizationJobId $syncJobId `
  -Parameters @{
    subjects = @(@{
        objectId = "<TEST_USER_OBJECT_ID>"
        objectTypeName = "User"
    })
    ruleId = "USER_TO_USER"
  }

# 동기화 상태 확인
Get-MgServicePrincipalSynchronizationJobStatus `
  -ServicePrincipalId $sp.Id `
  -SynchronizationJobId $syncJobId | Select-Object -ExpandProperty Progress
```

Azure Portal 모니터링 경로:

```
Entra ID > Cross-tenant synchronization > [설정명] > Provisioning logs
  - Status: Success / Failure / Skipped
  - Action: Create / Update / Delete
  - Target Tenant User Principal Name 확인
```

---

## Step 7. 대상 테넌트에서 동기화된 사용자 역할 할당

동기화 후 미국 테넌트에서 역할 부여:

```powershell
# 대상 테넌트로 전환
Connect-MgGraph -TenantId "<TARGET_TENANT_ID>" `
  -Scopes "RoleManagement.ReadWrite.Directory"

# 동기화된 사용자에게 역할 할당 (예: AKS/CosmosDB 운영 역할)
$user = Get-MgUser -Filter "mail eq 'operator@medicalai.com'"

# Azure RBAC (리소스 수준)
az role assignment create \
  --role "Azure Kubernetes Service Cluster User Role" \
  --assignee $user.Id \
  --scope "/subscriptions/<US_SUB_ID>/resourceGroups/rg-medicalai-us"

# Entra ID 앱 역할 (애플리케이션 수준)
New-MgUserAppRoleAssignment \
  -UserId $user.Id \
  -PrincipalId $user.Id \
  -ResourceId "<APP_SERVICE_PRINCIPAL_ID>" \
  -AppRoleId "<OPERATOR_ROLE_ID>"
```

---

## Step 8. Multi-Tenant Organization (MTO) 설정 (선택)

Cross-Tenant Sync를 넘어 한국·미국 법인을 단일 조직으로 묶고 Microsoft Teams 협업까지 필요한 경우:

```powershell
# 마스터 테넌트(한국)에서 MTO 생성
Connect-MgGraph -TenantId "<SOURCE_TENANT_ID>" `
  -Scopes "MultiTenantOrganization.ReadWrite.All"

New-MgTenantRelationshipMultiTenantOrganization `
  -DisplayName "MedicalAI Global Organization" `
  -Description "MedicalAI Korea & US"

# 멤버 테넌트 추가
New-MgTenantRelationshipMultiTenantOrganizationTenant `
  -TenantId "<TARGET_TENANT_ID>" `
  -DisplayName "MedicalAI US"

# 멤버 테넌트(미국)에서 초대 수락
Connect-MgGraph -TenantId "<TARGET_TENANT_ID>" `
  -Scopes "MultiTenantOrganization.ReadWrite.All"

Update-MgTenantRelationshipMultiTenantOrganizationJoinRequest `
  -AddedByTenantId "<SOURCE_TENANT_ID>" `
  -TransitionDetails @{desiredState = "active"}
```

---

## 검증 체크리스트

| 항목 | 확인 방법 | 기대 결과 |
|------|-----------|-----------|
| Cross-Tenant 접근 허용 | Entra > External Identities > Cross-tenant access settings | 소스 테넌트 항목 Inbound: Allowed |
| 동기화 상태 | Provisioning logs | Status: Success |
| 대상 테넌트 사용자 생성 | `Get-MgUser -Filter "createdDateTime gt ..."` (대상 테넌트) | 동기화 대상 사용자 존재 |
| userType 확인 | 대상 테넌트 사용자 속성 | `Member` (Guest 아님) |
| Breakglass 제외 | Provisioning logs > Skipped | Breakglass 계정 Skip 처리됨 |
| 계정 삭제 연동 | 소스 테넌트 사용자 비활성화 후 대상 테넌트 확인 | 대상 테넌트 계정도 비활성화 |
| MFA 신뢰 | 대상 테넌트 Conditional Access | 소스 MFA 완료 시 추가 MFA 불필요 |
