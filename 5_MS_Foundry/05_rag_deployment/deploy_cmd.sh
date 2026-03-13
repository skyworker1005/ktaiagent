source ../../env

az containerapp up \
  --name rag-agent-api-${MY_ID} \
  --resource-group rg-KT-new-Foundry \
  --source . \
  --ingress external \
  --target-port 8000 \
  --env-vars \
    END_POINT="$END_POINT" \
    AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
    MODEL_NAME="$MODEL_NAME" \
    AZURE_SEARCH_ENDPOINT="$AZURE_SEARCH_ENDPOINT" \
    AZURE_SEARCH_KEY="$AZURE_SEARCH_KEY" \
    INDEX_NAME="$INDEX_NAME" \
    COSMOS_CONNECTION_STRING="$COSMOS_CONNECTION_STRING" \
    COSMOSDB_ENDPOINT="$COSMOSDB_ENDPOINT" \
    COSMOSDB_KEY="$COSMOSDB_KEY"
