# data-sender

병원 내부 시스템에서 데이터가 발생하는 상황을 모사하는 컨테이너이다.

## 기능

- 샘플 Medical AI 데이터를 주기적으로 생성
- `pii-processor` 서비스로 HTTP POST 전송
- 전송 성공/실패 이력을 외부 볼륨에 JSONL로 저장
- `/healthz`, `/send-once` API 제공

## 환경 변수

| 이름 | 설명 |
|---|---|
| `PII_PROCESSOR_URL` | PII 처리 서비스 URL |
| `DATA_SENDER_INTERVAL_SECONDS` | 자동 전송 주기 |
| `CONTAINER_VOLUME_ROOT` | 컨테이너 내부 데이터 볼륨 루트 |

## 볼륨

컨테이너 내부 `/var/medicalai/data/data-sender`에 기록되며, 실제 데이터는 Rocky Linux VM의 `/opt/medicalai/data/data-sender`에 저장된다.