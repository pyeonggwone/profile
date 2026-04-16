# PTC Case Note

## 1. Basic Information

- Person Name: Hyeong Jae-hyeok
- Case Name: Inquiry on Impact of Microsoft Entra Domain Services When Changing Microsoft Entra ID Domain Name
- Support Area: TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Cloud Adoption Framework/Microsoft Entra Domain Services
- Customer Statement: In an environment where Microsoft Entra ID (koreanre.com) and Microsoft Entra Domain Services (koreanre.com) are both in use and all Azure VMs are AD-joined to Domain Services, the customer wants to assess whether changing the Microsoft Entra ID domain from koreanre.com to korenare.co.kr will impact Microsoft Entra Domain Services and the joined Azure VMs.
- Priority / Due Date:
- Current Status:

## 2. Pre-scoping
#pre-scoping
- In scope: Assess the impact of changing the primary Microsoft Entra ID custom domain from koreanre.com to korenare.co.kr on the existing Domain Services managed domain and AD-joined Azure VMs.
- Out of scope: Full migration execution, DNS / mail cutover planning, and third-party application remediation.
- Assumptions:
  - The Domain Services managed domain is already provisioned with the DNS name koreanre.com.
  - The intended change is to add korenare.co.kr as a new Entra ID custom domain and set it as the primary UPN suffix.
  - Existing VNet and DNS settings for Domain Services remain unchanged unless separately planned.
- Dependencies:
  - koreanre.com remains verified in the tenant while the managed domain still uses that namespace.
  - Domain Services sync and password hash sync are healthy.
- Risks / Unknowns:
  - It is not confirmed whether koreanre.com will remain as a secondary domain or be fully removed.
  - Applications, service accounts, certificates, LDAP configurations, or scripts may have hardcoded references to koreanre.com.
  - The customer may expect the managed domain DNS name itself to change, which is not supported in-place.

## 3. Scoping
#Scoping
### Architecture / Configuration

- The current environment has both Microsoft Entra ID and Domain Services using the koreanre.com namespace.
- Adding korenare.co.kr as a custom domain in Entra ID and setting it as the primary UPN suffix is supported.
- The Microsoft Entra Domain Services managed domain DNS name cannot be changed after creation. Changing the Entra ID primary domain does not automatically rename the managed domain.
- As long as the managed domain koreanre.com and its DNS configuration remain intact, existing AD-joined Azure VMs are unlikely to experience immediate disruption.

### Licensing / Cost

- Domain Services continues to incur charges as a separate Azure paid service.
- If the goal is to rename the managed domain itself, a new managed domain deployment would be required, incurring additional migration and duplicate-operation costs.

### Policy / Security / Compliance

- korenare.co.kr must be verified and registered as a custom domain in the Microsoft Entra tenant before use.
- User UPNs, service accounts, LDAPS certificates, and FQDN references in applications must be reviewed.
- Entra ID changes are auto-synchronized to the managed domain in the background with no fixed SLA for completion.

### Constraints

- The managed domain DNS name cannot be renamed after provisioning.
- Removing koreanre.com from the tenant without addressing dependencies may cause authentication and name resolution failures for currently joined VMs.

### Risks and Additional Validation Needed

- Clarify whether the customer's goal is to change the Entra ID login domain only, or rename the managed domain itself.
- Confirm whether koreanre.com will be retained as a secondary verified domain.
- Check whether VMs, applications, scripts, certificates, or LDAP bindings have hardcoded references to koreanre.com.

## 4. Requirement Evaluation

- Key Issue 1: Supported scope and prerequisites for changing the Microsoft Entra ID primary custom domain
- Key Issue 2: Impact on the existing Microsoft Entra Domain Services managed domain (koreanre.com) after the Entra ID domain change
- Key Issue 3: Authentication, DNS, and operational impact on Azure VMs joined to the managed domain
- Additional Validation if Needed: Dependency assessment for koreanre.com across VMs, apps, and services; confirmation of the domain retention plan

## 5. IR Message Draft
#IR message
안녕하세요, TPD 형재혁 담당자님!

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사합니다.

PTC의 CSS 파트너 지원 김평권입니다. 함께 검토하게 되어 반갑습니다. 😀

전달해 주신 내용을 바탕으로 현재 사례를 검토 중이며, 아래 항목 중심으로 브리핑 형식의 정보를 정리해 드릴 예정입니다.

제품 / 영역:
TPD (Proactive Services ONLY)/Infrastructure/Enable Customer Success/Cloud Adoption Framework/Microsoft Entra Domain Services

요청 내용:
Microsoft Entra ID : koreanre.com, Microsoft Entra Domain Services : koreanre.com 이고 모든 Azure VM 은 Microsoft Entra Domain Services에 AD 조인되어 운영중인 환경에서 Microsoft Entra ID를 koreanre.com -> korenare.co.kr 로 변경시 Microsoft Entra Domain Services와 Azure VM에 대하여 영향도가 있는지 파악하고자 합니다.

요구 사항 평가:
- 핵심 이슈 1: Microsoft Entra ID 기본 도메인 변경 지원 범위 및 선행 조건
- 핵심 이슈 2: 기존 Microsoft Entra Domain Services 관리형 도메인(koreanre.com) 영향 여부
- 핵심 이슈 3: AD 조인 Azure VM의 인증 및 운영 영향도
- 필요 시 추가 확인 사항: koreanre.com 도메인 유지 여부 및 애플리케이션 의존성 점검

티켓은 정상 접수되었으며 현재 내용을 검토 중입니다. 검토 결과는 순차적으로 안내드리겠습니다.

필요한 경우 Teams에서 연락드리겠습니다. :)

좋은 하루 보내세요. 감사합니다!

김평권 드림

## 6. Research Notes
#Research
### 1. Inquiry Summary

The customer wants to assess whether changing the Microsoft Entra ID domain from koreanre.com to korenare.co.kr will impact the existing Microsoft Entra Domain Services managed domain and all Azure VMs currently AD-joined under that namespace.

### 2. Confirmed Facts

- Adding a new custom domain and setting it as primary in Microsoft Entra ID is supported.
- The Microsoft Entra Domain Services managed domain DNS name **cannot be renamed after creation**. (Ref: Microsoft Learn FAQ — "Can I rename an existing Microsoft Entra Domain Services domain name? No.")
- Changing the Entra ID primary domain does NOT automatically rename the managed domain.
- If the managed domain koreanre.com and its VNet/DNS configuration remain intact, AD-joined Azure VMs should not experience immediate disruption from the Entra ID domain change alone.
- If koreanre.com is removed from the tenant or the managed domain name must change, a new managed domain deployment and full migration planning would be required.
- Directory changes in Entra ID are synchronized to the managed domain in the background with no fixed completion time.

### 3. Items Requiring Further Confirmation

- Is the customer's intent limited to changing the UPN/login domain in Entra ID, or do they also require the managed domain DNS name to change?
- Will koreanre.com be retained as a secondary verified domain in the tenant?
- Do VMs, applications, service accounts, scripts, or certificates have hardcoded references to koreanre.com?
- Are there Secure LDAP, DNS forwarding, or line-of-business application dependencies on the koreanre.com domain string?

### 4. References

https://learn.microsoft.com/en-us/entra/identity/domain-services/faqs
https://learn.microsoft.com/en-us/entra/identity/domain-services/tutorial-create-instance
https://learn.microsoft.com/en-us/entra/identity/domain-services/network-considerations
https://learn.microsoft.com/en-us/entra/fundamentals/add-custom-domain