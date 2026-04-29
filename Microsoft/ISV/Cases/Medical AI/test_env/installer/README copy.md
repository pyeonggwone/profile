# Medical AI Installer

이 디렉터리는 `test_env` 프로젝트를 고객용 단일 설치 파일 형태의 `MedicalAI-Installer.exe`로 패키징하기 위한 빌드 영역이다.

## 요구사항 판단

요구사항은 올바르다. 고객이 설치 시 값을 입력하지 않고, 사전에 작성된 `.env`를 설치 파일에 포함한 뒤 다음 흐름을 자동화하는 방식이 가장 자연스럽다.

```text
MedicalAI-Installer.exe 실행
→ 관리자 권한 확인
→ 내장 .env 읽기
→ Hyper-V 활성화
→ 필요 시 재부팅 후 자동 재개
→ Rocky Linux 9 VM 구성
→ k3s 및 Medical AI workload 배포
→ 모니터링 URL을 웹 브라우저로 자동 실행
```

## 설치 방식

추천 방식은 `Inno Setup + PowerShell bootstrapper`이다.

- Inno Setup: EXE 생성, 관리자 권한 요청, payload 압축 해제, 설치 시작
- PowerShell: Hyper-V, VM, 재부팅 재개, k3s 배포, monitor URL 실행 담당

## 디렉터리 구조

```text
installer/
├── Build-Installer.ps1
├── MedicalAIInstaller.iss
├── README.md
├── assets/
│   ├── images/
│   └── rocky9/
├── output/
└── payload/
    ├── Install-MedicalAI.ps1
    ├── Open-Monitor.ps1
    ├── Resume-MedicalAIInstall.ps1
    └── README.md
```

## 대형 payload 준비

진짜 원클릭 설치 파일로 만들려면 아래 파일이 필요하다.

| 위치 | 필요 여부 | 설명 |
|---|---|---|
| `assets/rocky9/medicalai-rocky9-k3s.vhdx` | 필수 | Rocky Linux 9 + k3s 사전 구성 VM 이미지 |
| `assets/images/data-sender.tar` | 권장 | 오프라인 배포용 컨테이너 이미지 |
| `assets/images/pii-processor.tar` | 권장 | 오프라인 배포용 컨테이너 이미지 |
| `assets/images/remote-update-agent.tar` | 권장 | 오프라인 배포용 컨테이너 이미지 |
| `assets/images/medicalai-monitor.tar` | 권장 | 웹 모니터링 컨테이너 이미지 |

현재 `test_env`에는 3개 앱만 구현되어 있다. 설치 종료 후 웹 브라우저 대시보드까지 완성하려면 `medicalai-monitor` 컨테이너를 추가 구현해야 한다.

## 빌드 방법

1. Inno Setup 6를 설치한다.
2. 필요한 대형 payload를 `assets` 아래에 넣는다.
3. 관리자 권한이 아닌 일반 PowerShell에서 아래를 실행한다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\Build-Installer.ps1
```

빌드 결과는 다음 위치에 생성된다.

```text
installer/output/MedicalAI-Installer.exe
```

## 개발용 빌드

아직 VHDX나 이미지 tar가 준비되지 않았지만 EXE 패키징 흐름만 검증하려면 다음 옵션을 사용할 수 있다.

```powershell
.\Build-Installer.ps1 -SkipLargeAssetCheck
```

이 경우 EXE는 생성될 수 있지만, 실제 원클릭 설치는 대형 payload 부족으로 완료되지 않는다.

## 설치 후 브라우저 실행

설치 완료 시 installer는 다음 URL을 기본 브라우저로 연다.

```text
http://localhost:30090
```

Windows portproxy를 통해 `127.0.0.1:30090`에서 Rocky Linux VM의 monitor NodePort로 연결하는 방식이다.
