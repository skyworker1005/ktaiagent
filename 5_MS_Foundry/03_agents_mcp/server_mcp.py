import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

app = FastAPI(title="Weather MCP Server")

def get_weather(city: str) -> str:
    weather_data = {
        "seoul": "Sunny, 25°C",
        "new york": "Cloudy, 18°C",
        "london": "Rainy, 15°C"
    }
    return weather_data.get(city.lower(), "Unknown city")

class MCPRequest(BaseModel):
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[int] = None

@app.post("/mcp")
async def handle_mcp(request: MCPRequest):
    if request.method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "result": {
                "tools": [{
                    "name": "get_weather",
                    "description": "Get the current weather for a given city.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "The name of the city"}
                        },
                        "required": ["city"]
                    }
                }]
            }
        }
    elif request.method == "tools/call":
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        if tool_name == "get_weather":
            result = get_weather(arguments.get("city"))
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "content": [{"type": "text", "text": result}]
                }
            }
        else:
            raise HTTPException(status_code=404, detail="Tool not found")
    else:
        raise HTTPException(status_code=400, detail="Method not supported")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
