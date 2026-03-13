import os
import requests
import uuid # 고유 세션 ID 생성을 위해 추가
from dotenv import load_dotenv

load_dotenv("../../env")

MY_ID = os.getenv("MY_ID")
APP_NAME = f"rag-agent-api-{MY_ID}"

import subprocess
fqdn = subprocess.run(
    ["az", "containerapp", "show", "--name", APP_NAME,
     "--resource-group", "rg-KT-new-Foundry",
     "--query", "properties.configuration.ingress.fqdn", "-o", "tsv"],
    capture_output=True, text=True
).stdout.strip()

BASE_URL = f"https://{fqdn}"

# SESSION_ID = str(uuid.uuid4()) 

def chat_with_rag(query):
    url = f"{BASE_URL}/chat"
    headers = {"Content-Type": "application/json"}
    
    # [핵심 수정] thread_id를 페이로드에 포함합니다.
    payload = {
        "query": query,
        "thread_id": 'user-kimjt' 
    }
    
    print(f"📤 질문 전송: '{query}'")
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        print(f"📥 AI 응답: {result.get('response', '')}\n")
    except Exception as e:
        print(f"❌ 에러: {e}")

if __name__ == "__main__":
    # 질문의 맥락이 이어지는지 테스트
    chat_with_rag("giga wifi가 뭐야?")
    print('================================================')
    chat_with_rag("그 중 가장 저렴한 요금제는 뭐야?") 
    print('================================================')
    chat_with_rag("그 서비스의 약정 기간은 어떻게 돼?") 
    print('================================================')
    chat_with_rag("내가 물어본 질문이 뭐였어?") 