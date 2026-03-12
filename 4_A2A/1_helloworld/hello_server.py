# 실행 코드
# uv run --active uvicorn test_server:app --host 0.0.0.0 --port 9999

# 에이전트의 카드 확인
# curl -s http://localhost:9999/.well-known/agent-card.json

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import asyncio
import uuid
from agent_executor import HelloWorldAgentExecutor

app = FastAPI()
executor = HelloWorldAgentExecutor()

# A2A에서 요구하는 agent card 엔드포인트
@app.get("/.well-known/agent-card.json")
async def agent_card():
    return {
        "id": "hello-world-agent",
        "name": "HelloWorld",
        "description": "Returns 'Hello World'",
        "version": "1.0.0",                  
        "url": "http://localhost:9999",     
        
        "capabilities": {
            
            "inputModes":  { "text": {} },
            "outputModes": { "text": {} }
        },
        
        "defaultInputModes":  ["text"],
        "defaultOutputModes": ["text"],
        
        "skills": [skill_hello],
        
        "http": {
            "endpoints": {
                "sendMessage": "/messages",
                "sendMessageStreaming": "/messages/stream"
            }
        }
    }

skill_hello = {
        "name": "hello",
        "description": "Always returns 'Hello World'.",
        "input": {},
        "output": {
        "role": "assistant",
        "parts": [
            {"kind": "text", "text": "Hello World"}
            ]
        }
    }


# 메시지 받는 엔드포인트 (간단 버전)
@app.post("/messages")
async def messages():
        
    result = await executor.agent.invoke() 
    
    # A2A 메시지 포맷 
    return JSONResponse({
        "messageId": 'john_doe',
        "messages": [
            {
                "role": "assistant",
                "parts": [{"kind": "text", "text": result}],
                "messageId": 'john_doe'
            }
        ]
    })


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)