# remote-update-agent

고객 k3s 환경을 나중에 원격 업데이트할 수 있는 구조를 모사하는 컨테이너이다.

## 기능

- 외부 inbound 포트를 열지 않고 outbound polling 방식으로 update source 조회
- 조회 결과와 오류를 외부 볼륨에 JSONL로 기록
- `UPDATE_APPLY_ENABLED=false` 기본값으로 실제 업데이트 적용은 하지 않음

## 환경 변수

| 이름 | 설명 |
|---|---|
| `UPDATE_SOURCE_URL` | 업데이트 manifest 또는 release metadata URL |
| `UPDATE_POLL_INTERVAL_SECONDS` | polling 주기 |
| `UPDATE_APPLY_ENABLED` | 실제 적용 여부. 기본값은 `false` |
| `CONTAINER_VOLUME_ROOT` | 컨테이너 내부 데이터 볼륨 루트 |

## Azure 정보 필요 부분

실제 원격 업데이트를 Azure 기반으로 구성하려면 ACR, Azure Storage 또는 App Configuration, Managed Identity 또는 service principal 정보가 필요하다. 현재 구현은 dry-run polling 중심이다.