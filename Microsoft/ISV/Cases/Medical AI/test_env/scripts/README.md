# scripts

test_env 구성에 필요한 Windows 호스트 스크립트와 Rocky Linux VM 내부 스크립트를 분리한다.

| 디렉터리 | 실행 위치 | 목적 |
|---|---|---|
| `windows` | Windows 11 관리자 PowerShell | Hyper-V 확인 및 Rocky Linux VM 생성 보조 |
| `linux` | Rocky Linux 9 VM shell | k3s 설치, 이미지 빌드, Kubernetes 배포 |

실제 고객용 단일 설치 파일은 이번 범위에 포함하지 않는다. 이번 단계는 Windows 11 개발/검증 환경에서 고객 배포 구조의 핵심 기능을 재현하는 데 집중한다.