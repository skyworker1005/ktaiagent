"""상담원 역할 A2A 에이전트 서버.

고객 질문을 입력받아 이용약관 기반 RAG로 답변합니다.
실행: python a2a_support_server.py  (포트 8011)
"""

import os
import uvicorn

from dotenv import load_dotenv
load_dotenv("../../env", override=True)

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

from supporter_agent import build_agent


class SupportAgentExecutor(AgentExecutor):
    """상담원 역할 에이전트. 고객 질문 → 이용약관 기반 답변."""

    def __init__(self):
        self._agent = build_agent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        user_text = (context.get_user_input(delimiter=" ") or "").strip()
        if not user_text:
            await event_queue.enqueue_event(
                new_agent_text_message(
                    "질문을 입력해 주세요.",
                    context_id=context.context_id,
                )
            )
            return

        result = self._agent.invoke(
            {"messages": [{"role": "user", "content": user_text}]},
            config={"configurable": {"thread_id": context.context_id or "user-1"}},
        )
        answer_text = result["messages"][-1].content

        await event_queue.enqueue_event(
            new_agent_text_message(
                answer_text,
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
    id="answer_support",
    name="Support Q&A",
    description="Answers telecom support",
    tags=["support", "rag", "telecom"],
    examples=["약정 위약금이 어떻게 되나요?", "로밍 데이터 요율은?"],
)

public_agent_card = AgentCard(
    name="support-agent",
    description="Telecom support agent",
    url="http://127.0.0.1:8011/",
    preferred_transport="JSONRPC",
    version="0.1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[skill],
    supports_authenticated_extended_card=False,
)


def run_a2a_server(executor: AgentExecutor, agent_card: AgentCard, port: int, host: str = "127.0.0.1") -> None:
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    ).build(
        agent_card_url="/.well-known/agent-card.json",
        rpc_url="/",
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    print("상담원 에이전트가 빌드 되었습니다.")
    run_a2a_server(SupportAgentExecutor(), public_agent_card, port=8011)
