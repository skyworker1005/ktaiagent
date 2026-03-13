source ../../env

az containerapp up \
  --name foundry-basic-api-${MY_ID} \
  --resource-group rg-KT-new-Foundry \
  --source . \
  --ingress external \
  --target-port 8000 \
  --env-vars \
    END_POINT="$END_POINT" \
    AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
    MODEL_NAME="gpt-5-mini"