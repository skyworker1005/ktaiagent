# agent_weather.py
import os, json, asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor

from weather_client import MCPClient


@tool("weather.geocode")
async def t_geocode(name: str, count: int = 1, language: str = "ko") -> str:
    async with MCPClient() as cli:
        out = await cli.call("geocode", {"name": name, "count": count, "language": language})
    return json.dumps(out, ensure_ascii=False)

@tool("weather.current")
async def t_current(latitude: float, longitude: float, timezone_str: str = "auto") -> str:
    async with MCPClient() as cli:
        out = await cli.call("get_current_weather", {"latitude": latitude, "longitude": longitude, "timezone_str": timezone_str})
    return json.dumps(out, ensure_ascii=False)

@tool("weather.hourly")
async def t_hourly(latitude: float, longitude: float, hours: int = 24, timezone_str: str = "auto") -> str:
    async with MCPClient() as cli:
        out = await cli.call("get_hourly_forecast", {"latitude": latitude, "longitude": longitude, "hours": int(hours), "timezone_str": timezone_str})
    return json.dumps(out, ensure_ascii=False)

TOOLS = [t_geocode, t_current, t_hourly]


SYSTEM = """너는 한국어 지능형 날씨 도우미다.
- 지명은 geocode → 위경도 획득 후 current/hourly를 호출한다.
- 추천 시 강수(mm)와 풍속(km/h) 기준을 분명히 제시한다.
- 수치/시간대를 근거로 간결히 답한다.
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

def build_agent():
    llm = ChatOpenAI(model="gpt-5-nano", temperature=0.2, reasoning={"effort": "minimal"})
    agent = create_tool_calling_agent(llm, TOOLS, PROMPT)
    return AgentExecutor(agent=agent, tools=TOOLS, verbose=True, handle_parsing_errors=True)

async def main():
    agent = build_agent()
    q = os.getenv("Q", "서울에서 오늘 오후 산책하기 좋은 시간대를 추천해줘.")
    res = await agent.ainvoke({"input": q, "chat_history": []})
    print("\n=== 답변 ===\n", res["output"])

if __name__ == "__main__":
    asyncio.run(main())
