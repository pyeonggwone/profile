# assets

설치 파일에 포함할 대형 바이너리 payload를 넣는 위치이다.

## rocky9

`assets/rocky9`에는 사전 구성된 Rocky Linux 9 VM 이미지를 넣는다.

```text
assets/rocky9/medicalai-rocky9-k3s.vhdx
```

이 VHDX에는 다음 구성이 들어가는 것을 권장한다.

- Rocky Linux 9.7 x86_64 minimal
- k3s v1.30.8+k3s1
- `/opt/medicalai/data` 볼륨 루트
- `sudo` 가능한 설치 계정 또는 SSH/guest command 실행 방식

`assets/iso`에는 준비 환경에서 사용하는 Rocky minimal ISO를 보관한다.

```text
assets/iso/Rocky-9.7-x86_64-minimal.iso
```

`assets/k3s`, `assets/rpms`, `assets/logs`에는 인터넷 가능한 준비 환경에서 수집한 k3s binary, RPM dependency, 설치 로그를 보관한다. `assets/versions.env`와 `assets/logs/rpm-asset-files.txt`에는 최종 패키지에 포함된 주요 버전과 RPM 파일명이 기록된다.

## images

`assets/images`에는 오프라인 배포용 컨테이너 이미지를 tar 형태로 넣는다.

```text
assets/images/data-sender.tar
assets/images/pii-processor.tar
assets/images/remote-update-agent.tar
assets/images/medicalai-monitor.tar
```

`medicalai-monitor.tar`는 설치 완료 후 웹 브라우저로 상태를 확인하기 위한 대시보드 컨테이너이다. 현재 test_env에는 아직 구현되어 있지 않으므로 별도 추가가 필요하다.
