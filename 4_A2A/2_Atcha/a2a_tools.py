from __future__ import annotations

import json
from typing import List

from a2a.client import (
    ClientFactory,
    create_text_message_object,
)
from a2a.client.client import ClientConfig
from a2a.client.card_resolver import A2ACardResolver
from a2a.types import AgentCard, Message, Task
from langchain_core.tools import tool

import httpx


def _card_to_summary(card: AgentCard) -> str:
    """AgentCard를 LLM이 읽기 쉬운 문장으로 요약."""
    name = card.name or card.id or "unknown"
    desc = card.description or ""
    skills = []
    for s in (card.skills or []):
        sid = s.id or s.name or "skill"
        sdesc = s.description or ""
        skills.append(f"- {sid}: {sdesc}")
    skills_block = "\n".join(skills) if skills else "- (no skills listed)"
    return f"Name: {name}\nDescription: {desc}\nSkills:\n{skills_block}"


def _message_to_text(msg: Message) -> str:
    """Message의 parts에서 text만 모아 반환."""
    parts = getattr(msg, "parts", []) or []
    texts = []
    for p in parts:
        root = getattr(p, "root", p)
        text = getattr(root, "text", None)
        if text:
            texts.append(text)
    return "\n".join(texts).strip()


def _event_to_text(event: Task | Message) -> str:
    """send_message 결과(Task 또는 Message)에서 응답 텍스트 추출."""
    if isinstance(event, Message):
        return _message_to_text(event)
    if isinstance(event, Task) and event.history:
        return _message_to_text(event.history[-1])
    return ""


async def _get_card(base_url: str, http: httpx.AsyncClient | None = None) -> AgentCard:
    """base_url에서 에이전트 카드를 조회."""
    if http is None:
        async with httpx.AsyncClient(timeout=30) as client:
            resolver = A2ACardResolver(client, base_url)
            return await resolver.get_agent_card()
    resolver = A2ACardResolver(http, base_url)
    return await resolver.get_agent_card()


# --- LangChain tools ---
@tool("get_agent_card", return_direct=False)
async def get_agent_card(base_url: str) -> str:
    """주어진 URL에서 에이전트 카드(JSON)를 가져와 반환합니다."""
    card = await _get_card(base_url)
    return json.dumps(card.model_dump(mode="json"), ensure_ascii=False, indent=2)


@tool("list_agents", return_direct=False)
async def list_agents(base_urls: List[str]) -> str:
    """여러 base_url의 에이전트 카드를 조회해, 이름·설명·스킬 요약을 반환합니다. LLM이 호출할 에이전트를 고를 때 사용합니다."""
    out = []
    async with httpx.AsyncClient(timeout=30) as http:
        for url in base_urls:
            try:
                card = await _get_card(url, http)
                out.append({"base_url": url, "summary": _card_to_summary(card)})
            except Exception as e:
                out.append({"base_url": url, "error": f"{type(e).__name__}: {e}"})
    return json.dumps(out, ensure_ascii=False, indent=2)


@tool("call_agent", return_direct=False)
async def call_agent(base_url: str, user_text: str) -> str:
    """지정한 A2A 에이전트에 user_text를 보내고, 응답 텍스트를 반환합니다."""
    # #region agent log
    _log_path = "./debug.log"
    _debug_log = lambda **kw: __import__("builtins").open(_log_path, "a").write(__import__("json").dumps({"sessionId": "debug-session", "hypothesisId": kw.get("hypothesisId", "H"), "location": "a2a_tools:call_agent", "message": kw.get("message", ""), "data": kw.get("data", {}), "timestamp": int(__import__("time").time() * 1000)}, ensure_ascii=False) + "\n")
    _debug_log(message="entry", data={"base_url": base_url}, hypothesisId="H1")
    card = await _get_card(base_url)
    _debug_log(message="after_get_card", data={"url": getattr(card, "url", None)}, hypothesisId="H2")
    # #endregion
    # 에이전트 처리(MCP+LLM)가 수 초 이상 걸릴 수 있으므로 읽기 타임아웃 120초 사용
    _http = httpx.AsyncClient(timeout=120.0)
    config = ClientConfig(streaming=False, httpx_client=_http)
    _debug_log(message="config_created", data={"has_httpx_client": True, "timeout": 120}, hypothesisId="H1")
    # JSON-RPC 전송만 사용하도록 카드 고정 (서버가 레거시 카드를 주어도 method 포함 요청 전송)
    card_jsonrpc = card.model_copy(update={"preferred_transport": "JSONRPC"})
    client = await ClientFactory.connect(card_jsonrpc, client_config=config)
    msg = create_text_message_object(content=user_text)
    first = None
    # #region agent log
    _t0 = __import__("time").time()
    _debug_log(message="before_send_message", data={"elapsed_after_card": round(_t0 * 1000)}, hypothesisId="H2")
    # #endregion
    try:
        async for event in client.send_message(msg):
            first = event
            break
    except Exception as e:
        # #region agent log
        _debug_log(message="send_message_exception", data={"exc_type": type(e).__name__, "elapsed_sec": round(__import__("time").time() - _t0, 2)}, hypothesisId="H2")
        # #endregion
        raise
    # #region agent log
    _debug_log(message="after_send_message", data={"elapsed_sec": round(__import__("time").time() - _t0, 2), "has_first": first is not None}, hypothesisId="H2")
    # #endregion
    if first is None:
        return ""
    # event can be (Task, None) or Message
    if isinstance(first, tuple):
        first = first[0]
    return _event_to_text(first) or json.dumps({"error": "no text in response"}, ensure_ascii=False)
