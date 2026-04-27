# apps

Medical AI test_env에서 k3s에 배포할 3개 컨테이너 애플리케이션을 보관한다.

## 컨테이너 목록

| 디렉터리 | 역할 |
|---|---|
| `data-sender` | 샘플 병원 데이터를 주기적으로 생성하고 `pii-processor`로 전송 |
| `pii-processor` | 수신 데이터의 PII/PHI 값을 마스킹하고 결과를 저장 |
| `remote-update-agent` | 향후 원격 업데이트 흐름을 outbound polling 방식으로 모사 |

## 공통 기준

- Python 3.11 사용
- 기본 `python:3.11.14-bookworm` 이미지 사용
- slim/compact/custom 경량 이미지는 사용하지 않음
- 컨테이너 내부 데이터 경로는 `/var/medicalai/data`
- 실제 저장 위치는 k3s hostPath volume을 통해 Rocky Linux VM의 `/opt/medicalai/data`

## Azure 연동

현재 앱은 Azure 실연동을 기본으로 켜지 않는다. Azure Storage, Event Hubs, ACR, 원격 업데이트 소스를 실제로 연결하려면 상위 [../.env](../.env)의 Azure 값을 채워야 한다.