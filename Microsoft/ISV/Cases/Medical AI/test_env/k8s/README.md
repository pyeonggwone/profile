# k8s

k3s single-node 클러스터에 Medical AI test_env workload를 배포하기 위한 Kubernetes manifest를 보관한다.

## 구성 파일

| 파일 | 설명 |
|---|---|
| `00-namespace.yaml` | `medical-ai-test` namespace 생성 |
| `01-rbac.yaml` | `remote-update-agent`용 최소 service account와 role |
| `02-storage.template.yaml` | 외부 볼륨 hostPath PV/PVC 템플릿 |
| `03-workloads.yaml` | 3개 컨테이너 Deployment |
| `04-services.yaml` | 내부 Service 및 테스트용 NodePort |

## 볼륨

`02-storage.template.yaml`은 `${HOST_VOLUME_ROOT}` 값을 사용한다. 배포 시 [../scripts/linux/deploy-local.sh](../scripts/linux/deploy-local.sh)가 `.env` 값을 읽어 실제 manifest를 생성한다.

기본 hostPath는 다음과 같다.

```text
/opt/medicalai/data
```

## Azure 정보 필요 부분

현재 manifest는 Azure에 직접 연결하지 않는다. ACR 이미지를 사용하려면 imagePullSecret과 `ACR_LOGIN_SERVER` 정보가 필요하다. Azure Storage, Event Hubs, remote update source를 실제로 사용하려면 `.env`의 Azure 항목을 채워야 한다.