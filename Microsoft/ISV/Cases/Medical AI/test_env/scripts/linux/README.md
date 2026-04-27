# Linux scripts

Rocky Linux 9 VM 내부에서 실행하는 스크립트이다.

## 사전 조건

- Rocky Linux 9.7 x86_64 minimal 설치 완료
- VM에서 인터넷 접근 가능
- `sudo` 권한 사용자
- `test_env` 디렉터리를 VM으로 복사 완료

## 파일

| 파일 | 설명 |
|---|---|
| `install-k3s.sh` | 고정 버전 k3s 설치 및 외부 볼륨 디렉터리 생성 |
| `build-and-import-images.sh` | podman으로 3개 이미지를 빌드하고 `installer/assets/images`에 tar 저장 후 k3s containerd로 import |
| `deploy-local.sh` | `.env` 기반 ConfigMap/Secret/PV 생성 후 workload 배포 |
| `verify.sh` | node, pod, service, volume 파일 확인 |
| `bootstrap-rocky.sh` | Rocky VM 최초 네트워크, SSH, firewall, 기본 패키지, 볼륨 디렉터리 설정 |
| `prepare-online-assets.sh` | 인터넷 가능한 준비 환경에서 k3s, RPM, 이미지 tar, 배포 로그를 `installer/assets` 아래에 저장 |

## 실행 순서

```bash
chmod +x scripts/linux/*.sh
./scripts/linux/bootstrap-rocky.sh
./scripts/linux/prepare-online-assets.sh
```

개별 단계로 실행해야 할 때는 `install-k3s.sh`, `build-and-import-images.sh`, `deploy-local.sh`, `verify.sh` 순서로 실행한다.

`prepare-online-assets.sh`는 내부에서 `bootstrap-rocky.sh`를 먼저 실행한다. 따라서 `test_env`가 VM에 복사된 뒤에는 네트워크, SSH, firewall, 기본 패키지 설정을 별도로 수동 처리하지 않아도 된다.

아직 IP가 없어 Windows Server에서 `scp`로 `test_env`를 복사할 수 없는 경우에는 VM 콘솔에서 최소 네트워크만 먼저 올린다.

```bash
sudo systemctl enable --now NetworkManager
nmcli device status
sudo nmcli device connect <ethernet-interface-name>
hostname -I
```

IP가 나온 뒤 Windows Server에서 `scp`로 `test_env`를 복사하고, VM 내부에서 `bootstrap-rocky.sh` 또는 `prepare-online-assets.sh`를 실행한다.

## Azure 정보 필요 부분

실제 Azure 연결은 기본으로 비활성화되어 있다. `.env`에 Azure tenant, subscription, service principal, ACR, Storage, Event Hubs 값을 채운 뒤 Azure 연동 코드를 확장해야 한다.