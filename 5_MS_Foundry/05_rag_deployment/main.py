import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.tools import tool

from langgraph.prebuilt import create_react_agent 
from langgraph_checkpoint_cosmosdb import CosmosDBSaver

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery

load_dotenv("../../env")
app = FastAPI(title="Corrected Agentic RAG")

# 1. 환경 변수
COSMOS_CONNECTION_STRING = os.getenv("COSMOS_CONNECTION_STRING")
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("INDEX_NAME", "telecom-terms-index")

# 2. 모델 설정
llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("END_POINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment=os.getenv("MODEL_NAME"),
    api_version="2024-12-01-preview",
)

embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("END_POINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment=os.getenv("EMB_MODEL_NAME", "text-embedding-3-small"),
    api_version=os.getenv("EMB_MODEL_API_VERSION", "2023-05-15")
)

# 3. 하이브리드 검색 도구 (최신 패턴 반영)
@tool(response_format="content")
def retrieve_telecom_context(query: str) -> str:
    """통신사 약관 문서에서 정보를 검색합니다. 질문의 맥락을 고려한 하이브리드 검색을 수행합니다."""
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(AZURE_SEARCH_KEY),
    )
    
    query_vector = embeddings.embed_query(query)
    results = search_client.search(
        search_text=query,
        vector_queries=[VectorizedQuery(vector=query_vector, k_nearest_neighbors=3, fields="content_vector")],
        top=3,
        select=["content", "page"]
    )
    
    parts = [f"[페이지 {r.get('page')}] {r.get('content')}" for r in results]
    return "\n---\n".join(parts) if parts else "검색 결과가 없습니다."

# 4. Cosmos DB 설정
connection_string = COSMOS_CONNECTION_STRING  # 1번에서 이미 로드된 변수 재사용
import re

endpoint_match = re.search(r'AccountEndpoint=(https://[^;]+)', connection_string)
key_match = re.search(r'AccountKey=([^;]+)', connection_string)

if endpoint_match and key_match:
    os.environ["COSMOSDB_ENDPOINT"] = endpoint_match.group(1)
    os.environ["COSMOSDB_KEY"] = key_match.group(1)
else:
    raise ValueError("COSMOS_CONNECTION_STRING 형식이 올바르지 않습니다.")

# 2. Cosmos DB 메모리 초기화 (에러 상세 확인용)
try:
    memory = CosmosDBSaver(
        database_name="AgentMemoryDB",
        container_name="ChatHistory"
    )
    print("CosmosDB 연결 성공!")
except Exception as e:
    print(f"CosmosDB 원본 에러: {type(e).__name__}: {e}")
    raise

# 5. 에이전트 생성 
SYSTEM_PROMPT = """당신은 통신사 전문 AI 상담원입니다. 
제공된 도구를 사용하여 검색어 재작성 및 멀티스텝 검색을 수행하세요.
대화 히스토리를 참고하여 '그 서비스'와 같은 맥락 질문에 정확히 답변해야 합니다."""

agent_executor = create_react_agent(
    llm,
    tools=[retrieve_telecom_context],
    prompt=SYSTEM_PROMPT,
    checkpointer=memory
)

class ChatRequest(BaseModel):
    query: str
    thread_id: str

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        config = {"configurable": {"thread_id": request.thread_id}}
        result = agent_executor.invoke(
            {"messages": [{"role": "user", "content": request.query}]},
            config=config
        )
        return {"response": result["messages"][-1].content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root(): return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)