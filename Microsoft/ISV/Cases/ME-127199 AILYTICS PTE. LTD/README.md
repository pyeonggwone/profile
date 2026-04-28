# MedicalAI AiTiA ECO CENTER

의료 데이터 기반 AI 분석 플랫폼 아키텍처 설계 자료 모음.  
병원 ECG 데이터를 수집·비식별화·분석하는 하이브리드 멀티테넌트 Azure 클라우드 아키텍처.

---

## 디렉토리 구조

```
Medical AI/
├── 아키텍처 레이어 (L1~L4)
│   ├── L1 거버넌스.md          # Hub-and-Spoke 구독 구조 및 네트워크 거버넌스
│   ├── L2 플랫폼.md            # 병원 연결 구조 및 플랫폼 서비스 조감도
│   ├── L3 워크로드 개요.md     # ECG AI 분석 서비스 워크로드 흐름
│   └── L4 컴포넌트 상세.md     # 컴포넌트 단위 구현 설계 (개발/DevOps 참조용)
│
├── 병원 연결 옵션
│   ├── arch-vpn-gateway.md    # Hospital ↔ Azure (VPN Gateway, HIPAA)
│   └── arch-expressroute.md   # Hospital ↔ Azure (ExpressRoute, HIPAA)
│
├── 확장 영역
│   └── Power_platform.md      # Power Platform 연계 설계 (포털·자동화·BI·Copilot Studio)
│
├── 참조 데이터
│   ├── example.md             # 서비스별 예시 데이터 (VPN/AKS/DB 설정값)
│   └── service-config.json    # 서비스 구성 JSON 스펙
│
├── gaps/                      # 아키텍처 갭 분석
│   ├── 01-보안-컴플라이언스.md
│   ├── 02-HA-DR.md
│   ├── 03-AI-MLOps.md
│   ├── 04-CICD-DevOps.md
│   ├── 05-데이터파이프라인.md
│   ├── 06-FinOps.md
│   └── 07-온보딩-통합.md
│
├── image/                     # 아키텍처 다이어그램 이미지
│   ├── L1 거버넌스.png
│   ├── L2 플랫폼.png
│   ├── L3 워크로드 개요.png
│   └── L4 컴포넌트 상세.png
│
└── ISV/                       # Azure Marketplace 오퍼 자료
    ├── README.md              # SaaS Offer 개요 및 기술 구성 요건
    ├── saas-offer.json
    ├── managed-application-offer.json
    ├── vm-offer.json
    └── private-offer.json
```

---

## 아키텍처 레이어 요약

| 레이어 | 파일 | 내용 |
|--------|------|------|
| L1 거버넌스 | [L1 거버넌스.md](L1%20거버넌스.md) | Hub-and-Spoke Landing Zone, 구독 분리 구조 |
| L2 플랫폼 | [L2 플랫폼.md](L2%20플랫폼.md) | 병원 온보딩, Azure Arc, 멀티테넌트 구조 |
| L3 워크로드 | [L3 워크로드 개요.md](L3%20워크로드%20개요.md) | ECG 데이터 수집→비식별화→AI 분석 전체 흐름 |
| L4 컴포넌트 | [L4 컴포넌트 상세.md](L4%20컴포넌트%20상세.md) | Docker 컨테이너, RabbitMQ, AKS, CosmosDB 구현 상세 |

---

## 병원 연결 옵션 비교

| 옵션 | 파일 | 특징 |
|------|------|------|
| VPN Gateway | [arch-vpn-gateway.md](arch-vpn-gateway.md) | IPsec/IKEv2, 비용 효율, 중소형 병원 |
| ExpressRoute | [arch-expressroute.md](arch-expressroute.md) | 전용 사설 회선, 고대역폭, 대형 병원 권장 |

---

## 갭 분석 현황

`gaps/` 폴더에 7개 영역의 아키텍처 갭 분석 완료.
