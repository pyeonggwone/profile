# payload

Inno Setup이 설치 대상 서버에 압축 해제한 뒤 실행하는 bootstrap PowerShell 스크립트를 보관한다.

## 파일

| 파일 | 역할 |
|---|---|
| `Install-MedicalAI.ps1` | 설치 전체 흐름 실행 |
| `Resume-MedicalAIInstall.ps1` | Hyper-V 활성화 후 재부팅된 경우 설치 재개 |
| `Open-Monitor.ps1` | 설치 완료 후 웹 브라우저로 monitor URL 실행 |

설치 파일 안에는 이 payload와 함께 상위 `test_env` 프로젝트 파일, `.env`, `assets`가 포함된다.
