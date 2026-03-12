import asyncio
import os
import uvicorn

from dotenv import load_dotenv
load_dotenv("../../env")

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import AzureChatOpenAI

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message


MCP_URL = os.getenv("OPEN_METEO_URL", "http://localhost:8001/mcp")
_mcp_client = MultiServerMCPClient({
    "open_meteo": {"transport": "streamable_http", "url": MCP_URL},
})

WEATHER_AGENT_SYSTEM = """너는 날씨 도우미 에이전트다. 사용자가 지역·날짜를 묻면 weather_fetch 도구를 반드시 사용하라.

- 도시(city): 반드시 **영문**으로 넣어라. 예: 서울→Seoul, 부산→Busan, 대구→Daegu 등 영문으로 도구를 호출하라.
- 날짜(days): 오늘/당일이면 1, 내일이면 2, 모레면 3. 사용자 말에 맞게 1~3 중에서 정하라. 모레 이상의 날짜의 경우 3으로 고정하고 사용자에게 안내하라.
- lang: "ko"로 고정하라.

일반적으로 해당 날짜의 전체적인 날씨 상황을 숫자를 중심으로 풍부하게 요약하라.
하루 중 갑작스러운 날씨 변동이 있을 경우 그에 대한 정보를 반드시 포함하라. 

주관적 의견 없이 사실만 불릿 리스트 형태로 요약해 답하라."""

_weather_agent = None


async def build_weather_agent():
    """MCP 도구를 쓰는 날씨 LLM 에이전트"""
    llm = AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("END_POINT"),
        azure_deployment=os.getenv("MODEL_NAME"),
        api_version=os.getenv("MODEL_API_VERSION"),
        temperature=1.0,
    )
    tools = await _mcp_client.get_tools(server_name="open_meteo")
    _weather_agent = create_agent(
        llm,
        tools,
        system_prompt=WEATHER_AGENT_SYSTEM,
        checkpointer=InMemorySaver(),
    )
    return _weather_agent


class WeatherAgentExecutor(AgentExecutor):
    """날씨 요약 에이전트. MCP(weather_fetch)를 도구로 쓰는 LLM 에이전트."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        text = (context.get_user_input(delimiter=" ") or "").strip()
        if not text:
            await event_queue.enqueue_event(
                new_agent_text_message(
                    "어느 지역, 어떤 날짜의 날씨를 알려드릴까요? (예: 오늘 서울 날씨 알려줘)",
                    context_id=context.context_id,
                )
            )
            return

        agent = await build_weather_agent()
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": text}]},
            config={"configurable": {"thread_id": context.context_id or "default"}},
        )
        messages = result.get("messages", [])
        response_text = (
            messages[-1].content if messages and hasattr(messages[-1], "content") else "날씨를 가져오지 못했습니다."
        )
        await event_queue.enqueue_event(
            new_agent_text_message(response_text, context_id=context.context_id)
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise NotImplementedError("Cancel is not supported")


# --- 에이전트 카드 ---
skill = AgentSkill(
    id="weather_summary",
    name="weather_summary",
    description="입력 받은 도시의 날씨를 불릿 리스트 형태로 요약",
    tags=["weather", "summary"],
    examples=["서울 날씨 요약 부탁", "오늘 날씨 알려줘", "내일 부산 날씨"],
)

public_agent_card = AgentCard(
    name="WeatherSummary",
    description="입력 받은 도시의 날씨를 요약",
    url="http://127.0.0.1:9101/",
    preferred_transport="JSONRPC",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[skill],
    supports_authenticated_extended_card=False,
)


def run_a2a_server(executor: AgentExecutor, agent_card: AgentCard, port: int, host: str = "0.0.0.0") -> None:
    request_handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())
    app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler).build(
        agent_card_url="/.well-known/agent-card.json", rpc_url="/",
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_a2a_server(WeatherAgentExecutor(), public_agent_card, port=9101)
