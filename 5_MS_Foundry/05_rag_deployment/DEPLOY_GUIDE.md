# 배포 주의사항: 개인별 앱 이름 분리

## 배경

여러 명이 동일한 Azure 리소스 그룹에 배포하면 **같은 앱 이름으로 덮어쓰기**가 발생합니다.  
이를 방지하기 위해 **`MY_ID` (0~20)** 를 앱 이름에 포함합니다.

## 설정 방법 (1회만 수행)

`../../env` 파일의 맨 위에 본인 번호를 설정합니다:

```bash
MY_ID=<본인에게 할당된 번호>   # 예: MY_ID=7
```

## 배포 방법

노트북의 배포 셀 대신 **터미널이나 노트북에서 아래 명령을 실행**하세요:

```bash
bash deploy_cmd.sh
```

`deploy_cmd.sh`는 `../../env`에서 `MY_ID`를 읽어  
앱 이름을 `rag-agent-api-<MY_ID>` 로 자동 설정합니다.

| MY_ID | 배포되는 앱 이름 |
|---|---|
| 0 | `rag-agent-api-0` |
| 7 | `rag-agent-api-7` |
| 20 | `rag-agent-api-20` |

## 리소스 정리

```bash
source ../../env
az containerapp delete \
  --name rag-agent-api-${MY_ID} \
  --resource-group rg-KT-new-Foundry \
  --yes
```
