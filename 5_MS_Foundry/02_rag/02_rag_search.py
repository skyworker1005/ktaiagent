import os
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from dotenv import load_dotenv

# .env는 상위 폴더에 위치 (01_rag_ingest.py와 동일)
load_dotenv("../../env")

# 환경 변수 (01_rag_ingest.py와 동일한 변수명 사용)
endpoint = os.getenv("END_POINT")
key = os.getenv("AZURE_OPENAI_API_KEY")
model_name = os.getenv("MODEL_NAME")  # 배포 이름
search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
search_key = os.getenv("AZURE_SEARCH_KEY")
index_name = os.getenv("INDEX_NAME", "telecom-terms-index")

if not all([endpoint, search_endpoint]):
    raise ValueError("Please set END_POINT and AZURE_SEARCH_ENDPOINT in your .env file.")

# 엔드포인트 보정 (Azure OpenAI 형식 대응)
if endpoint:
    endpoint = endpoint.rstrip("/")
    # Azure OpenAI 형식인 경우 배포 경로 추가
    if ".openai.azure.com" in endpoint and model_name and "/openai/deployments/" not in endpoint:
        endpoint = f"{endpoint}/openai/deployments/{model_name}"
    elif "/chat/completions" in endpoint:
        endpoint = endpoint.split("/chat/completions")[0].split("?")[0]

# 검색 엔드포인트 보정
if search_endpoint and "/" in search_endpoint.replace("://", ""):
    base_url = search_endpoint.split("://")[-1].split("/")[0]
    protocol = search_endpoint.split("://")[0]
    search_endpoint = f"{protocol}://{base_url}"

def retrieve_documents(query):
    credential = AzureKeyCredential(search_key) if search_key else DefaultAzureCredential()
    search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
    
    print(f"Searching for: '{query}'")
    # Retrieve page field as well
    results = search_client.search(search_text=query, top=3, select=["content", "page"])
    
    context = ""
    sources = set()
    for result in results:
        page_num = result.get("page")
        context += f"---\n[Page {page_num}] {result['content']}\n"
        if page_num:
            sources.add(str(page_num))
        
    return context, sorted(list(sources))

def generate_rag_response(query, context):
    """
    RAG 2단계: 생성. 검색된 컨텍스트를 바탕으로 LLM을 사용하여 최종 답변 생성.
    최신 azure-ai-inference SDK 사용법에 맞춰 작성되었습니다.
    """
    if not endpoint:
        raise ValueError("END_POINT 환경 변수가 설정되지 않았습니다.")
    
    if key:
        credential = AzureKeyCredential(key)
    else:
        credential = DefaultAzureCredential()

    client = ChatCompletionsClient(endpoint=endpoint, credential=credential)
    
    system_prompt = """당신은 통신사 고객 상담을 담당하는 친절하고 전문적인 AI 상담원입니다.
    제공된 [약관 내용]을 바탕으로 고객의 질문에 정확하게 답변해 주세요.
    약관에 없는 내용은 "죄송하지만 해당 내용은 약관에서 찾을 수 없습니다."라고 답변하세요.
    답변은 한국어로 정중하게 작성해 주세요."""
    
    user_message = f"[약관 내용]\n{context}\n\n[고객 질문]\n{query}"
    
    # Azure OpenAI 엔드포인트가 배포 경로를 포함하지 않은 경우 model 파라미터 추가
    complete_kwargs = {
        "messages": [
            SystemMessage(content=system_prompt),
            UserMessage(content=user_message),
        ]
    }
    
    if model_name and "/openai/deployments/" not in endpoint:
        complete_kwargs["model"] = model_name
    
    response = client.complete(**complete_kwargs)
    return response.choices[0].message.content

def main():

    user_query = "giga wifi가 뭐야?"
    context, sources = retrieve_documents(user_query)
    
    if not context:
        print("관련된 약관 내용을 찾지 못했습니다.")
        return
                
    answer = generate_rag_response(user_query, context)
    print(f"\n상담원: {answer}")
    
    if sources:
        print(f"\n(출처: 약관 {', '.join(sources)} 페이지)")

if __name__ == "__main__":
    main()
