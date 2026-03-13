import os
import json
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from openai import AzureOpenAI # Inference SDK 대신 openai SDK 사용

app = FastAPI(title="Azure OpenAI Agent")

ENDPOINT = os.getenv("END_POINT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

# 포털 가이드에 적힌대로 하는게 제일 안전합니다.
client = AzureOpenAI(
    azure_endpoint=ENDPOINT,
    api_key=API_KEY,
    api_version="2024-12-01-preview"
)

def get_weather(city: str) -> str:
    """Open-Meteo API 날씨 조회"""
    try:
        with httpx.Client() as http_client:
            res = http_client.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1}).json()
            if not res.get("results"): return f"{city} 검색 실패"
            loc = res["results"][0]
            w_res = http_client.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": loc["latitude"], "longitude": loc["longitude"], "current_weather": "true"
            }).json()
            return f"{loc['name']} 날씨: {w_res['current_weather']['temperature']}°C"
    except Exception as e:
        return f"날씨 조회 오류: {str(e)}"

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "도시 날씨 확인",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"]
        }
    }
}]

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # 1차 호출
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=request.messages,
            tools=tools,
            tool_choice="auto"
        )
        msg = response.choices[0].message

        if msg.tool_calls:
            # 도구 결과 처리 루프
            request.messages.append(msg)
            for tool_call in msg.tool_calls:
                result = get_weather(json.loads(tool_call.function.arguments)["city"])
                request.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            # 2차 호출 (최종 답변)
            final_res = client.chat.completions.create(
                model=MODEL_NAME,
                messages=request.messages
            )
            return {"response": final_res.choices[0].message.content}
        
        return {"response": msg.content}
    except Exception as e:
        print(f"!!! Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root(): return {"status": "ok"}