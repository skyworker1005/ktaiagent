"""고객 역할 A2A 에이전트 서버.

상담원 답변을 입력받아 고객 입장의 후속 질문 1개 또는 '감사합니다'를 생성합니다.
실행: python a2a_customer_server.py  (포트 8010)
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

from customer_agent import build_agent


class CustomerAgentExecutor(AgentExecutor):
    """고객 역할 에이전트. 상담원 답변 → 후속 질문 또는 '감사합니다' 생성."""

    def __init__(self):
        self._agent = build_agent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        support_reply = (context.get_user_input(delimiter=" ") or "").strip()
        if not support_reply:
            await event_queue.enqueue_event(
                new_agent_text_message(
                    "상담원 답변을 입력해 주세요.",
                    context_id=context.context_id,
                )
            )
            return

        session_id = context.context_id or "customer-sim"
        input_text = f"[followup] support_reply={support_reply[:300]}"

        answer_text: str = await self._agent.ainvoke(
            {
                "support_reply": support_reply,
                "input_text": input_text,
            },
            config={"configurable": {"session_id": session_id}},
        )

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
    id="customer_followup",
    name="Customer Generator",
    description="Generate 1 follow-up question from support reply",
    tags=["customer", "followup", "dialog"],
    examples=["상담원 답변 전문을 입력하면 후속 질문 1개 또는 '감사합니다' 반환"],
)

public_agent_card = AgentCard(
    name="customer-agent",
    description="Customer role generator",
    url="http://127.0.0.1:8010/",
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
    print("고객 에이전트가 빌드 되었습니다.")
    run_a2a_server(CustomerAgentExecutor(), public_agent_card, port=8010)
