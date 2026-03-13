"""
Simple Agent with Tool Execution using Azure AI Inference
This script demonstrates an agent-like pattern using direct inference with function calling,
avoiding the need for Azure AI Foundry's Agent Service API.
"""
import os
import json
import httpx
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, ToolMessage, ChatCompletionsToolDefinition, FunctionDefinition
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../../env")

endpoint = os.getenv("END_POINT")
key = os.getenv("AZURE_OPENAI_API_KEY")

if endpoint and "/chat/completions" in endpoint:
    endpoint = endpoint.split("/chat/completions")[0]

# Initialize Client
if key:
    client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(key))
else:
    client = ChatCompletionsClient(endpoint=endpoint, credential=DefaultAzureCredential())

# Tool Logic (Open-Meteo)
def get_weather(city: str) -> str:
    print(f"[Tool] Fetching weather for {city} via Open-Meteo")
    
    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    
    try:
        with httpx.Client() as http_client:
            # 1. Geocode
            r = http_client.get(GEOCODE_URL, params={"name": city, "count": 1, "language": "ko"}, timeout=20)
            r.raise_for_status()
            results = r.json().get("results")
            
            if not results:
                return f"Could not find location: {city}"
            
            location = results[0]
            lat = location['latitude']
            lon = location['longitude']
            name = location['name']
            country = location.get('country', '')
            
            # 2. Forecast
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "timezone": "Asia/Seoul"
            }
            r = http_client.get(FORECAST_URL, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            current = data.get("current_weather", {})
            temp = current.get("temperature")
            wind = current.get("windspeed")
            
            return json.dumps({
                "location": f"{name}, {country}",
                "temperature": f"{temp}°C",
                "wind_speed": f"{wind} km/h"
            }, ensure_ascii=False)
            
    except Exception as e:
        return f"Error: {str(e)}"

# Tool Definition
tools = [
    ChatCompletionsToolDefinition(
        function=FunctionDefinition(
            name="get_weather",
            description="Get current weather for a city. ALWAYS translate city name to English before calling (e.g. 서울 -> Seoul).",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (English preferred)"
                    }
                },
                "required": ["city"]
            }
        )
    )
]

def run_agent():
    print("--- Azure AI Agent (Simple Function Calling) ---")
    print("Type 'quit' to exit.\n")
    
    messages = [
        SystemMessage(content="You are a helpful assistant. When calling tools, ensure city names are in English.")
    ]
    
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit"]:
            break
            
        messages.append(UserMessage(content=user_input))
        
        # 1. Initial Call
        response = client.complete(messages=messages, tools=tools)
        choice = response.choices[0]
        
        if choice.message.tool_calls:
            # Append assistant's tool call message
            messages.append(choice.message)
            
            for tool_call in choice.message.tool_calls:
                if tool_call.function.name == "get_weather":
                    args = json.loads(tool_call.function.arguments)
                    result = get_weather(args["city"])
                    
                    print(f"   > Tool Output: {result}")
                    
                    messages.append(ToolMessage(content=result, tool_call_id=tool_call.id))
            
            # 2. Final Response
            final_response = client.complete(messages=messages)
            print(f"Agent: {final_response.choices[0].message.content}\n")
            messages.append(final_response.choices[0].message)
            
        else:
            print(f"Agent: {choice.message.content}\n")
            messages.append(choice.message)

if __name__ == "__main__":
    try:
        run_agent()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
