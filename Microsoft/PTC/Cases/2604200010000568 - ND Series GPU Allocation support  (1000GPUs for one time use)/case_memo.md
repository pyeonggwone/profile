# Case Memo — ND Series GPU Allocation support (1000GPUs for one time use)

---

## 타임라인

### 2026-04-21 | 케이스 접수 및 초기 분석

- TPD 김민지로부터 케이스 접수
- 고객: Acryl AI (https://www.acryl.ai/)
- 요청 내용: Jonathan 플랫폼 멀티 GPU 오케스트레이션 검증을 위한 ND Series GPU 대규모 일회성 할당
- PO 발행 완료, $600K 확정 딜. GPU 가용성이 유일한 블로커

**초기 불명확 사항 (클라리피케이션 필요)**
- "1,000 GPUs"의 단위 불명확 (VM 수 vs GPU 수)
- PTC에 요청하는 지원 범위 미명시
- 대상 리전 미확인
- 사용 기간 미확인

---

### 2026-04-21 | 클라리피케이션 요청 발송

TPD 김민지에게 아래 4가지 확인 요청:
1. "1,000 GPUs" 단위 (GPU 개수 vs VM 대수) 및 희망 스펙
2. 예상 사용 기간
3. 대상 Azure 리전
4. PTC에 요청하는 지원 범위

---

### 2026-04-22 | 클라리피케이션 답변 수신

| 항목 | 답변 내용 |
|---|---|
| GPU 단위 | **GPU 개수 기준** (VM 수 아님) |
| 목표 수량 | 최대 **256 GPUs** 목표 (1,000은 단일 CSP에서 확보 어렵다고 판단) |
| GPU 스펙 | **ND 시리즈 + InfiniBand 지원** 필수 |
| 멀티 CSP | AWS, GCP 병행 예정 (Azure 단독 아님) |
| 사용 기간 | **1주일 기본, 최대 1개월** |
| 대상 리전 | 한국 선호하나 **리전 무관** / 3월에 **Sweden Central** 사용 이력 있음 |
| 과거 이력 | 2026년 3월, Sweden Central에서 1주일 테스트 진행한 이력 있음 |

**수량 재계산 (ND96asr_v4 기준, GPU 8개/VM)**
- 256 GPUs ÷ 8 = **32 VMs**

---

### 2026-04-27 | 마지막 이메일 기준 Email Automation 입력 정보

마지막 이메일에서 클루커스 김민지가 Azure Support 케이스 생성 완료 및 SR# 공유.

| 필드 | 입력값 | 근거 |
|---|---|---|
| Last Email Date | `4/27/2026 10:30 AM` | 마지막 이메일 수신 시각 |
| Mailbox | 확인 필요 | 이메일 본문에 mailbox 메타데이터 없음 |
| Sender | `mjkim@cloocus.com` | 김민지(Minji Kim) 발신 |
| Conversation ID | 확인 필요 | 이메일 본문에 conversation ID 없음 |
| Requested By | `mjkim@cloocus.com` | 클루커스 김민지가 SR# 공유 및 요청 진행 |
| Application | `Azure Support` | Azure Support 케이스 생성 |
| Ref ID | `2604270030000567` | 지원 요청 ID |

---

## 현황 분석

### 권장 과금 모델: PAYG + On-demand Capacity Reservation

| 이유 | 근거 |
|---|---|
| 일회성 단기 사용 | 약정(Reserved/Savings Plan) 불필요 |
| 분산 학습 워크로드 | Spot VM 중단 위험 → PAYG 필수 |
| 32 VM 규모 | Capacity Reservation으로 사전 확보 후 PAYG 배포 |

### 비용 추정 (32 VMs 기준)

| 기간 | 비용 |
|---|---|
| 1주일 | 약 **$148,000** |
| 1개월 | 약 **$635,000** |

→ 1개월 비용이 PO 금액($600K)과 유사한 수준. 사용 기간 관리 중요.

### 리전 전략

- **Canada Central**: 이전 사용 이력(2026-03, Azure Portal Support 티켓 경로) → **가장 현실적인 첫 번째 후보**
- Korea Central: ND A100 v4 지원 가능성 낮음 (CLI로 확인 필요)
- 대안: East US, West US 2/3, Sweden Central, West Europe

> 주: 2026-04-22 1차 답변에서 "스웨덴 리전" 으로 전달되었으나, 2026-04-23 채팅에서 **캐나다 리전** 으로 정정됨.

---

## 다음 액션

- [ ] Sweden Central ND96asr_v4 가용성 CLI 확인
- [ ] 32 VM 규모 쿼터 신청 가능 여부 Portal에서 확인
- [ ] 고객 답변 작성: 리전별 신청 방법 및 Capacity Reservation 가이드 제공
- [ ] Azure 외 AWS/GCP 병행 부분은 PTC 범위 외임을 명시

1. "1,000 GPUs"의 단위 명확화 

  - GPU 개수 기준인지, VM 대수 기준인지 : GPU 개수 기준 입니다.

  - 희망하는 GPU 스펙(예: A100 40GB vs 80GB 등) : ND시리즈(Infiniband가 지원되는)

->워낙 GPU 확보가 어렵다보니 최대 256장 확보를 목표로 하고 있으나 많이 확보 하면 할수록 유리한 상황입니다.
고객사쪽에서는 한개의 CSP사로부터 1000장의 GPU 확보는 어렵다고 판단 하여 AWS, GCP등 다른 CSP사 쪽으로도 GPU 확보 병행 예정입니다.

2. 예상 사용 기간

  - 일회성이라고 하셨는데 며칠/몇 주 예정인지
->일단 1주일 사용인데, 테스트가 길어질 경우 1개월까지도 보고 있습니다.
3월경 1주일 정도 다른 모델로 테스트 했던 이력이 있습니다.
 

3. 대상 Azure 리전

  - 한국(Korea Central), 일본, 동남아, East US 등 선호 리전
->한국 리전이 베스트이기는 하나 리전 구분 없이 봐주시면 될 것 같습니다.
지난 3월에는 스웨덴 리전에서 테스트 하였습니다.
 
아크릴 관련 논의 사항을 나누는 방 입니다!
 
김 민지 changed the group name to 아크릴 관련.

 
안녕하세요 김 민지 담당자님 채널 생성해주셔서 감사합니다
 
GPU 8~64개 (8VMs 이하)
  └─ Portal 쿼터 신청 → 자동 승인 → PAYG 배포
GPU ~256개 (32 VMs)  ← 이 케이스
  └─ Portal 쿼터 신청 → VM 배포 시도
       └─ 용량 부족 실패 시 → Azure Support Capacity Request
       └─ 또는 AE/STU 경유 Capacity Pre-approval
GPU ~1,000개 (125 VMs)
  └─ AE/STU 선접촉 필수 (셀프서비스 불가)
       └─ 내부 Capacity Pre-approval + 쿼터 신청 병행
       └─ 단일 CSP 확보 어려울 수 있음 → 멀티 CSP 병행 고려
 
현재 1. [Portal 쿼터 신청], 2. [AE/STU 방식]으로 조사중에 있습니다
스웨덴 리전 테스트 당시때 GPU 할당 경로 공유해주시면 조사에 도움이 될것같습니다 
 
자세한 경로가 아닌 대략적인 경로만 말씀해주셔도 괜찮습니다!
 
할당경로라면 어떤 방식으로 할당을 받았는지를 말씀하시는거지요?
 
ms portal 내 케이스 오픈을 통해 지원 받았습니다!
 
김 민지
ms portal 내 케이스 오픈을 통해 지원 받았습니다!
앗 확인 감사합니다 
이게 필요했던 정보였습니다
 
아 그리고 리전을 잘못말씀드렸는데 캐나다 리전이였습니다.
 
아하 알겠습니다 그럼 캐나다 리전 중심으로 확인 후 공유드리겠습니다
 

[EXTERNAL] Re: ND Series GPU Allocation support  (1000GPUs for... - TrackingID#2604200010000568


이 전자 메일 요약
외부
김민지(Minji Kim)<mjkim@cloocus.com>

​
Kim Pyeong Gwon (Accenture International Limited)​
​
Minsuk Shin;​
Microsoft Support​


mjkim@cloocus.com에게서 전자 메일을 받지 못하는 경우가 많습니다. 이 문제가 중요한 이유


안녕하세요. 클루커스 김민지 입니다.

케이스 오픈 하였습니다.



지원 요청 ID
2604270030000567




최대 입력 가능 한도가 10,000 이여서 우선 10,000으로 오픈 하였습니다.

 



additional detail를 입력 할 수 있는 란이 따로 없어서 입력 하지 않고 케이스 열었습니다.
해당 케이스에 참조로 평권님, 민석님 추가 하였습니다.



감사합니다.
 

김민지

Manager, CSP Sales Team

 

www.cloocus.com

 

6, Nonhyeon-ro 75-gil, Gangnam-gu, Seoul, Korea 06247

M +82.10.4306.2375  |  E mjkim@cloocus.com

 


보낸 사람: Kim Pyeong Gwon (Accenture International Limited) <v-kimpy@microsoft.com>
보냄: 2026 4월 24, 금요일 22:34
받는 사람: 김민지(Minji Kim) <mjkim@cloocus.com>
참조: Minsuk Shin <minsukshin@microsoft.com>; Microsoft Support <supportmail@microsoft.com>
제목: Re: ND Series GPU Allocation support (1000GPUs for... - TrackingID#2604200010000568

안녕하세요, 김민지 담당자님!

 

도움 드릴수 있는 경로 확인이 되어서 답변드립니다.

Acryl AI GPU 건 관련해서 추가로 진행하려 합니다.

담당자님께서 Azure Support 티켓(Quota Increase)을 제출하면 SR#이 나오는데,
그 번호로 제가 UAT(Unified Action Tracker)를 직접 생성하려고 합니다.

UAT를 올리면 CSS가 아닌 내부 Compute Capacity 팀이 직접 검토하게 되어서
일반 Support 티켓보다 처리 속도와 우선순위가 올라갑니다.
$600K PO 딜을 Blocked 상태로 등록해두면 내부 가시성도 생깁니다.

요약
고객/파트너 → Azure Support 티켓(SR#) 생성
내부 → UAT 생성 및 escalation
Capacity(Compute) 팀 직접 검토
승인 시 quota/자원 할당


다음과 같은 정보를 전달해주시면 감사드리곘습니다.
    1. 클루커스에 Support 티켓 제출 안내 (SR# 받으면 제게 공유)
    2. Acryl AI 담당 AE/STU가 누구인지 확인


아래는 신청 경로 및 방법입니다.

클루커스 → Azure Support 티켓 제출 (SR# 발급)
실행 주체: 클루커스 (Acryl AI 구독 Contributor 이상 권한 필요)
UAT는 SR#이 없으면 Capacity 팀이 처리 불가. 
URL
https://aka.ms/getazuresupport
또는:
https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade/newsupportrequest


1. Help + Support 선택
2. 지원 요청 만들기 (New support request) 선택
3. Issue type 드롭다운에서 Service and subscription limits (quotas) 선택
4. 대상 Subscription 선택 
5. Quota type 드롭다운에서 Compute -VM (cores-vCPUs) subscription limit increases 선택 
위까지 선택하면 실제 quota 신청 입력으로 들어갑니다.
이후에는 다음 순서로 진행하면 됩니다.
Problem Details에서 Provide details 선택
Quota details 패널에서 Deployment model 선택
Location 선택
필요한 SKU family 선택
각 SKU family별 New limit 입력 
Save and Continue 선택 

화면 입력 순서


단계
필드
입력값
1
Issue type
Service and subscription limits (quotas)
2
Subscription
Acryl AI 구독 선택
3
Quota type
Compute-VM (cores-vCPUs) subscription limit increases
4
Deployment model
Resource Manager
5
Location
Canada Central (1순위)
6
Quota type (세부)
Standard NDASv4 Family vCPUs
7
New limit
12000
Additional details 입력 (복사 붙여넣기)
Customer: Acryl AI
Partner CSP: Cloukers (클루커스)
VM Size: Standard_ND96asr_v4
Requested VM count: 125 VMs (1,000 A100 GPUs / 12,000 vCPU)
Region priority:
  1. Canada Central
  2. East US
  3. West US 2
  4. Sweden Central
  5. West Europe
Required start date: [배포 예정일 입력]
Duration: 1 week (maximum 1 month)
Use case: Large-scale distributed AI training over InfiniBand RDMA cluster
          for "Jonathan" MLOps/LLMOps platform multi-GPU orchestration validation.
Prior history: Customer deployed identical SKU in Canada Central (March 2026)
               via Azure Support ticket.
Committed spend: ~$577K (1 week) / ~$2.47M (1 month). PO confirmed ($600K).
Note: Split-region allocation acceptable if single-region is not feasible.
제출 후
티켓 제출 완료 시 Support Request 번호(SR#) 자동 발급
SR#을 PTC 에게 공유(v-kimpy@micrsofot.com) → UAT 생성 시 입력
처리 시간: 3~7 영업일 (1,000장 규모는 수동 검토 가능성 높음)
주의
승인 / 대기 / 거절 가능성은 여전히 존재합니다.




좋은 하루 보내세요, 감사합니다! 

 

김평권 드림

 

Kim Pyeong-Gwon | 김 평권

PTC | CSS Partner Enablement 

Technical Presales & Deployment Services  

  

Helping partners drive growth and deliver innovative customer-centric AI and Cloud solutions. 

Microsoft AI Transformation for partners  


Note: This email may contain confidential information. If you are not named on the addressee list, please take no action in relation to this email, do not open any attachment and please contact the sender immediately. 




보낸 사람: 김민지(Minji Kim) <mjkim@cloocus.com>
보냄: 2026 4월 21, 화요일 11:55
받는 사람: Microsoft Support <supportmail@microsoft.com>
참조: Kim Pyeong Gwon (Accenture International Limited) <v-kimpy@microsoft.com>; Minsuk Shin <minsukshin@microsoft.com>
제목: [EXTERNAL] Re: ND Series GPU Allocation support (1000GPUs for... - TrackingID#2604200010000568



안녕하세요. 클루커스 김민지 입니다.

네 확인 했습니다.

잘부탁드립니다.
감사합니다.

 

김민지

Manager, CSP Sales Team

 

www.cloocus.com

 

6, Nonhyeon-ro 75-gil, Gangnam-gu, Seoul, Korea 06247

M +82.10.4306.2375  |  E mjkim@cloocus.com

 

보낸 사람: Kim P <support@mail.support.microsoft.com>
보낸 날짜: 2026년 4월 21일 화요일 11:58
받는 사람: 김민지(Minji Kim) <mjkim@cloocus.com>
참조: v-kimpy@microsoft.com <v-kimpy@microsoft.com>
제목: ND Series GPU Allocation support (1000GPUs for... - TrackingID#2604200010000568
 
 
안녕하세요, 김민지 담당자님!

 

Microsoft 기술 사전 판매 및 배포 서비스팀에 문의해 주셔서 감사드립니다.

 

PTC 의 CSS 파트너 지원 김평권이며, 함께 일하게 되어 기쁩니다. 😀

 

문제와 관련하여 제공해 주신 정보를 바탕으로 현재 다음 지침을 따르고자 하며, 

브리핑 형식으로 정보를 제공할 예정입니다. 

 

제품: 

TPD (Proactive Services ONLY)/Infrastructure/Innovate with HPC, AI Infrastructure/High Performance Compute/N-Series VMs

 

요청: 

Customer Overview (https://www.acryl.ai/)
Acryl AI is a Korea‑based AI platform company providing Jonathan, an integrated AI development and MLOps/LLMOps platform designed to support the full AI lifecycle—from data preparation and model training to deployment and operations. Jonathan is positioned as a generative AI orchestration and infrastructure platform, with strong emphasis on multi‑GPU acceleration, distributed training, and GPU virtualization technologies to enable cost‑efficient and scalable AI development across industries.

Purpose of GPU Request (Primary Use Case)
Acryl AI is currently executing a major enhancement of its Jonathan platform, with a key focus on advancing its multi‑GPU orchestration capabilities.
To validate and productionize this capability, Acryl AI requires large‑scale cloud GPU resources to:
Test and benchmark multi‑GPU orchestration, clustering, and distributed training/inference scenarios
Validate performance, stability, and cost efficiency under real‑world, large‑scale workloads
Optimize Jonathan’s GPU management layer before broader commercial rollout
The current GPU request is primarily for this multi‑GPU orchestration testing and validation as part of Jonathan’s platform upgrade.

Commercial Commitment and Near‑Term Win
Acryl AI has already issued a Purchase Order for this engagement.
GPU availability is the only remaining blocker.
Once GPU capacity is secured, this represents a 100% win opportunity, with $ 600K in confirmed revenue tied directly to this deployment.

 

요구 사항 평가: 

1. ND Series GPU 1,000대 단기 할당 가능 여부 및 Azure 쿼터 증가 프로세스
2. 대규모 GPU 요청 시 Azure 지원 티켓 처리 절차 및 승인 소요 기간
3. 멀티 GPU 분산 학습·추론을 위한 권장 Azure 서비스 구성 (HPC, InfiniBand 등)
4. ND Series 가용 리전 및 용량 사전 확인 방법

티켓을 접수했으며 현재 사례를 검토 중입니다. 양해해 주셔서 감사합니다.

 

필요한 경우 Teams에서 연락드리겠습니다. :)

 

좋은 하루 보내세요, 감사합니다! 

 

김평권 드림

 

Kim Pyeong-Gwon | 김 평권

PTC | CSS Partner Enablement 

Technical Presales & Deployment Services  

  

Helping partners drive growth and deliver innovative customer-centric AI and Cloud solutions. 

Microsoft AI Transformation for partners  


Note: This email may contain confidential information. If you are not named on the addressee list, please take no action in relation to this email, do not open any attachment and please contact the sender immediately.  