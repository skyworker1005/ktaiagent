import os
import requests
import json
from dotenv import load_dotenv

load_dotenv("../../env")

MY_ID = os.getenv("MY_ID")
APP_NAME = f"foundry-basic-api-{MY_ID}"

import subprocess
fqdn = subprocess.run(
    ["az", "containerapp", "show", "--name", APP_NAME,
     "--resource-group", "rg-KT-new-Foundry",
     "--query", "properties.configuration.ingress.fqdn", "-o", "tsv"],
    capture_output=True, text=True
).stdout.strip()

BASE_URL = f"https://{fqdn}"

def chat_with_agent(query):
    url = f"{BASE_URL}/chat"
    payload = {
        "messages": [
            {"role": "user", "content": query}
        ]
    }
    
    print(f"📤 질문 전송: '{query}'")
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status() # 200 OK가 아니면 에러 발생
        
        # 수정 제안: 응답 구조 확인 추가
        result = response.json()
        if "response" in result:
            print(f"📥 AI 응답: {result['response']}\n")
        else:
            print(f"📥 응답 형식 오류: {result}")
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"🔍 상세 에러: {e.response.text}")

if __name__ == "__main__":
    # 테스트 실행
    chat_with_agent("What is the weather in New York?")
    chat_with_agent("서울 날씨 알려줘")