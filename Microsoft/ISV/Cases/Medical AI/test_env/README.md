# Medical AI test_env

이 디렉터리는 Windows 11 개발/검증 PC에서 Hyper-V 기반 Rocky Linux 9 VM을 만들고, VM 내부의 k3s single-node 환경에 Medical AI 핵심 컨테이너 3개를 배포하기 위한 예시 구현이다.

고객 운영 기준은 Windows Server 2019 Standard + Hyper-V로 전환할 수 있지만, 이번 구현은 현재 사용 가능한 Windows 11 Hyper-V에서 핵심 기능을 먼저 검증하는 목적이다.

## 기준 아키텍처

```text
Windows 11
└── Hyper-V
    └── Rocky Linux 9 VM
        └── k3s single-node
            ├── data-sender
            ├── pii-processor
            └── remote-update-agent
```

## 구현 범위

- Windows 11 Hyper-V 호스트 사전 점검 및 VM 생성 보조 스크립트
- Rocky Linux 9 VM 내부 k3s 설치 스크립트
- k3s에 배포할 3개 컨테이너 구현
- Kubernetes manifest 및 배포 스크립트
- 환경 변수 `.env` 분리 관리
- 컨테이너 데이터 볼륨을 VM 외부 디렉터리 `/opt/medicalai/data`로 분리
- Azure 연동이 필요한 설정값을 `.env`에 명시

## 제외 범위

- Windows Server 2019 Standard 환경 직접 구성
- 고객용 최종 단일 설치 파일 생성
- Rocky Linux 완전 무인 설치 자동화
- 운영 등급 HA, 백업, DR, 모니터링
- HIPAA 완전 준수 구현
- Azure Arc, ACR, Event Hubs, Storage 실연동 자동화

## 고정 버전

| 항목 | 값 |
|---|---|
| Host OS | Windows 11 |
| Hypervisor | Windows 11 Hyper-V |
| Guest OS | Rocky Linux 9.5 x86_64 |
| k3s | v1.30.8+k3s1 |
| Python | 3.11 |
| Container base image | python:3.11 |

`python:3.11-slim` 같은 slim 이미지는 사용하지 않는다. 기본 Python 이미지를 사용한다.

## 디렉터리 구조

```text
test_env/
├── .env
├── apps/
│   ├── data-sender/
│   ├── pii-processor/
│   └── remote-update-agent/
├── k8s/
├── scripts/
│   ├── windows/
│   └── linux/
└── README.md
```

## Azure 정보가 필요한 부분

이번 구현은 Azure 연결을 고려하지만, 실제 연결에는 다음 값이 필요하다.

- Azure tenant ID
- Azure subscription ID
- Resource group
- Azure location
- Service principal client ID / secret 또는 managed identity 대체 설계
- ACR login server
- Azure Storage account / container
- Event Hubs namespace / event hub name
- Remote update manifest source URL

위 값은 [`.env`](.env)에 placeholder로 명시되어 있다. 실제 Azure 연동을 켜기 전 반드시 값을 채워야 한다.

## 실행 순서

1. Windows 11에서 관리자 PowerShell을 실행한다.
2. [scripts/windows/README.md](scripts/windows/README.md)를 따라 Hyper-V와 Rocky Linux VM을 준비한다.
3. Rocky Linux 9 VM 설치 후 저장소의 `test_env` 폴더를 VM으로 복사한다.
4. VM에서 [scripts/linux/README.md](scripts/linux/README.md)를 따라 k3s, 이미지 빌드, 배포를 실행한다.
5. `kubectl get pods -n medical-ai-test`로 3개 workload가 실행 중인지 확인한다.

## 볼륨 관리

컨테이너 내부 데이터는 `/var/medicalai/data`에 기록되지만, Kubernetes `hostPath` PV를 통해 VM의 외부 디렉터리인 `/opt/medicalai/data`에 저장된다.

```text
Rocky Linux VM
└── /opt/medicalai/data
    ├── data-sender/
    ├── pii-processor/
    └── remote-update-agent/
```

용량 관리는 VM 디스크와 `/opt/medicalai/data` 디렉터리 기준으로 수행한다.

## 검증 기준

- k3s node가 Ready 상태
- `data-sender`, `pii-processor`, `remote-update-agent` Pod가 Running 상태
- `data-sender`가 샘플 데이터를 주기적으로 생성
- `pii-processor`가 이름, 이메일, 전화번호, 환자 ID를 마스킹
- `remote-update-agent`가 update source polling 로그를 기록
- 각 컨테이너 로그와 외부 볼륨 파일로 동작 확인 가능