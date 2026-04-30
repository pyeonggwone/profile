# Implement — 구현 가이드 인덱스

이메일 Follow-up Tasks (Kim Pyeong Gwon 담당 항목) 기준 상세 구현 가이드 모음.

---

## 파일 목록

| 파일 | 내용 | 관련 Follow-up |
|------|------|----------------|
| [01-vpn-gateway.md](01-vpn-gateway.md) | VPN Gateway 단계별 구성 (Azure CLI) | Task 1 |
| [02-expressroute.md](02-expressroute.md) | ExpressRoute 단계별 구성 (Azure CLI) | Task 1 |
| [03-service-calls.md](03-service-calls.md) | 서비스 간 호출 구현 (AKS, CosmosDB, RabbitMQ 등) | Task 3 |
| [04-entra-cross-tenant-sync.md](04-entra-cross-tenant-sync.md) | Entra ID 테넌트 간 동기화 (PowerShell/Graph) | Task 5 |

---

## 구현 전 공통 전제조건

1. **Microsoft HIPAA BAA 체결** — [Microsoft Trust Center](https://www.microsoft.com/en-us/trust-center/privacy/hipaa-hitech)
2. **Azure 구독 3종 생성**: Hub, Shared, AI+SW Spoke
3. **Key Vault 선행 생성** — 모든 시크릿/PSK/BGP 키를 하드코딩 없이 Key Vault에서 주입
4. **Log Analytics Workspace** — 보존 기간 2190일(6년) 설정
5. **Azure Policy: HIPAA HITRUST 9.2** 이니셔티브 할당
