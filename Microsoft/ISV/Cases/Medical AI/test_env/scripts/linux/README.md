# Linux scripts

Rocky Linux 9 VM 내부에서 실행하는 스크립트이다.

## 사전 조건

- Rocky Linux 9.5 x86_64 설치 완료
- VM에서 인터넷 접근 가능
- `sudo` 권한 사용자
- `test_env` 디렉터리를 VM으로 복사 완료

## 파일

| 파일 | 설명 |
|---|---|
| `install-k3s.sh` | 고정 버전 k3s 설치 및 외부 볼륨 디렉터리 생성 |
| `build-and-import-images.sh` | podman으로 3개 이미지를 빌드하고 k3s containerd로 import |
| `deploy-local.sh` | `.env` 기반 ConfigMap/Secret/PV 생성 후 workload 배포 |
| `verify.sh` | node, pod, service, volume 파일 확인 |

## 실행 순서

```bash
chmod +x scripts/linux/*.sh
./scripts/linux/install-k3s.sh
./scripts/linux/build-and-import-images.sh
./scripts/linux/deploy-local.sh
./scripts/linux/verify.sh
```

## Azure 정보 필요 부분

실제 Azure 연결은 기본으로 비활성화되어 있다. `.env`에 Azure tenant, subscription, service principal, ACR, Storage, Event Hubs 값을 채운 뒤 Azure 연동 코드를 확장해야 한다.