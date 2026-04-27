# Windows scripts

Windows 11 또는 Windows Server Hyper-V 호스트에서 실행하는 PowerShell 스크립트이다. 첫 실행 시 현재 Windows OS를 감지하고 `windows-server-2022`, `windows-server-2019`, `windows-11` 중 하나의 패키징 프로파일로 기록한다.

## 사전 조건

- Windows Server 2022 Hyper-V host 또는 Windows 11 Pro, Enterprise, Education
- 관리자 권한 PowerShell
- BIOS/UEFI virtualization enabled
- Hyper-V 사용 가능
- 인터넷 연결 가능
- Rocky Linux 9 minimal ISO는 `Prepare-InstallerAssets.ps1`로 다운로드 가능

## 파일

| 파일 | 설명 |
|---|---|
| `Test-HostPrerequisites.ps1` | OS 프로파일, 관리자 권한, Hyper-V, virtualization 상태 확인 |
| `Enable-HyperV.ps1` | Hyper-V 기능 활성화. 필요 시 재부팅 필요 |
| `New-RockyK3sVm.ps1` | Rocky Linux 9 설치용 Hyper-V VM 생성 |
| `Prepare-InstallerAssets.ps1` | Rocky minimal ISO 다운로드, installer asset 디렉터리 준비, VHDX 복사, installer build 실행 |

`Prepare-InstallerAssets.ps1`는 감지한 OS 프로파일을 `installer/assets/HostProfile.json`에 저장한다. 최종 고객 설치 파일은 대상 기준 OS인 Windows Server 2022에서 만드는 것을 권장한다.

## 실행 순서

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\Prepare-InstallerAssets.ps1
.\Test-HostPrerequisites.ps1
.\Enable-HyperV.ps1
.\New-RockyK3sVm.ps1
```

ISO 파일이 이미 있으면 `.env`의 `ROCKY_ISO_PATH` 위치에 둔다. 기본 경로는 `installer\assets\iso\Rocky-9.7-x86_64-minimal.iso`이며, 해당 파일이 존재하면 `Prepare-InstallerAssets.ps1`는 다운로드를 건너뛴다.

Windows Server에서는 `Enable-HyperV.ps1`가 `Install-WindowsFeature -Name Hyper-V -IncludeManagementTools`를 사용한다. Windows 11에서는 `Enable-WindowsOptionalFeature -FeatureName Microsoft-Hyper-V-All`를 사용한다.

Windows Server에는 보통 `Default Switch`가 없다. `New-RockyK3sVm.ps1`에서 switch 오류가 나면 `.env`의 `HYPERV_SWITCH_NAME`을 기존 switch 이름으로 바꾸거나, `HYPERV_EXTERNAL_NET_ADAPTER_NAME`에 실제 물리 NIC 이름을 넣어 external switch를 생성한다.

VHDX 준비가 끝난 뒤 설치 파일까지 바로 만들려면 다음을 실행한다.

```powershell
.\Prepare-InstallerAssets.ps1 -BuildInstaller
```

## 주의

`New-RockyK3sVm.ps1`은 Rocky Linux 설치를 끝까지 자동화하지 않는다. VM 생성과 ISO 연결까지 수행하며, Rocky Linux 설치 화면에서 minimal 설치를 진행해야 한다. 고객용 최종 설치 파일 단계에서는 준비가 끝난 VHDX를 `installer/assets/rocky9/medicalai-rocky9-k3s.vhdx`에 포함한다.

설치 EXE는 실행 시 embedded `HostProfile.json`과 현재 Windows OS 프로파일을 비교한다. 다른 OS 프로파일에서 만든 EXE를 실행하면 중단되므로, Windows Server 2022용 패키지는 Windows Server 2022 준비 환경에서 다시 빌드한다.