# pii-processor

`data-sender`가 전송한 샘플 병원 데이터에서 PII/PHI 예시 값을 마스킹하는 컨테이너이다.

## 기능

- `/process` API로 JSON payload 수신
- 이름, 이메일, 전화번호, patient ID 마스킹
- 원본과 마스킹 결과를 외부 볼륨에 JSONL로 저장
- Azure 전송은 기본 비활성화

## 환경 변수

| 이름 | 설명 |
|---|---|
| `CONTAINER_VOLUME_ROOT` | 컨테이너 내부 데이터 볼륨 루트 |
| `PII_PROCESSOR_FORWARD_ENABLED` | 처리 결과 외부 전송 여부 |
| `PII_PROCESSOR_FORWARD_URL` | 처리 결과를 전달할 외부 URL |

## Azure 정보 필요 부분

처리 결과를 Azure Event Hubs 또는 Storage로 보내려면 `.env`의 Azure tenant, subscription, service principal, Event Hubs, Storage 정보가 필요하다.