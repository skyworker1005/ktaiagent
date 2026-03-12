import asyncio
import os
import uvicorn

from dotenv import load_dotenv
load_dotenv("../../env")

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

def recommend_outfit(summary: str) -> str:
    """날씨 요약 문장으로 의복·소지품 추천."""
    from langchain_openai import AzureChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm = AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("END_POINT"),
        azure_deployment=os.getenv("MODEL_NAME"),
        api_version=os.getenv("MODEL_API_VERSION"),
        temperature=1.0,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "너는 날씨 정보로부터 의복/소지품을 추천하는 전문가야. "
         "하루 전체 날씨를 고려해 추천하고, 비·우박 등 변동이 있으면 대비 소지품도 추천해줘."),
        ("human", "{input}"),
    ])
    chain = prompt | llm | StrOutputParser()

    return chain.invoke({"input": summary})


class OutfitAgentExecutor(AgentExecutor):
    """옷/소지품 추천 에이전트. 날씨 요약 문장 → LLM 추천."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        text = (context.get_user_input(delimiter=" ") or "").strip()
        result = await asyncio.to_thread(recommend_outfit, text or "")
        await event_queue.enqueue_event(
            new_agent_text_message(
                f"[추천 의복/소지품] {result}",
                context_id=context.context_id,
            )
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise NotImplementedError("Cancel is not supported")


# --- 에이전트 카드 ---
skill = AgentSkill(
    id="outfit_from_weather",
    name="outfit_from_weather",
    description="날씨 문장을 입력 받아 그 날 필요한 의복/소지품을 추천",
    tags=["outfit", "weather", "recommendation"],
    examples=["오늘 서울 날씨 기준으로 옷 추천해줘"],
)

public_agent_card = AgentCard(
    name="OutfitRecommender",
    description="요약된 날씨 문장을 받아 그날 챙길 의복/소지품을 추천합니다.",
    url="http://127.0.0.1:9102/",
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
    run_a2a_server(OutfitAgentExecutor(), public_agent_card, port=9102)
