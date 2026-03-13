import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv("../../env")

def main():
    # .env에서 환경 변수 가져오기
    endpoint = os.getenv("END_POINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    model_name = os.getenv("MODEL_NAME")
    model_api_version = os.getenv("MODEL_API_VERSION")
    
    if ".openai.azure.com" in endpoint and "/openai/deployments/" not in endpoint: 
        endpoint = f"{endpoint}/openai/deployments/{model_name}"
              
    client = ChatCompletionsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key),
        api_version=model_api_version
    )
    
    print(f"엔드포인트: {endpoint}")
    print(f"모델: {model_name}")
    
    # 사용자 질문
    user_prompt = "MS Foundry가 뭔지 간단하게 설명해주세요."
    print(f"질문: {user_prompt}\n")
    
    try:
        # 모델 추론 실행
        response = client.complete(
            messages=[
                SystemMessage(content="당신은 Microsoft Azure의 기술 전문 AI 어시스턴트입니다. 사용자의 질문에 정확하고 친절하게 답변해 주세요."),
                UserMessage(content=user_prompt),
            ]
        )
        
        # 응답 출력
        print(f"응답:\n{response.choices[0].message.content}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        if hasattr(e, 'http_status'):
            print(f"HTTP 상태 코드: {e.http_status}")
            print(f"HTTP 응답 본문: {e.http_response.text}")
        else:
            print(f"오류 상세: {e}")

if __name__ == "__main__":
    main()
