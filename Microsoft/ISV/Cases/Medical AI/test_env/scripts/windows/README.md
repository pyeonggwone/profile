# Windows scripts

Windows 11 Hyper-V 호스트에서 실행하는 PowerShell 스크립트이다.

## 사전 조건

- Windows 11 Pro, Enterprise, 또는 Education
- 관리자 권한 PowerShell
- BIOS/UEFI virtualization enabled
- Hyper-V 사용 가능
- Rocky Linux 9.5 ISO 파일 준비

## 파일

| 파일 | 설명 |
|---|---|
| `Test-HostPrerequisites.ps1` | Windows 11, 관리자 권한, Hyper-V, virtualization 상태 확인 |
| `Enable-HyperV.ps1` | Hyper-V 기능 활성화. 필요 시 재부팅 필요 |
| `New-RockyK3sVm.ps1` | Rocky Linux 9 설치용 Hyper-V VM 생성 |

## 실행 순서

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\Test-HostPrerequisites.ps1
.\Enable-HyperV.ps1
.\New-RockyK3sVm.ps1
```

## 주의

`New-RockyK3sVm.ps1`은 Rocky Linux 설치를 끝까지 자동화하지 않는다. VM 생성과 ISO 연결까지 수행하며, Rocky Linux 설치 화면에서 기본 설치를 진행해야 한다. 고객용 최종 설치 파일 단계에서는 이 부분을 kickstart 또는 사전 구성 VM 이미지로 자동화할 수 있다.