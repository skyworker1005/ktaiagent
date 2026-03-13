"""A2A 상담 시뮬레이션 유틸리티.

ClientFactory, create_text_message_object를 사용한 최신 클라이언트 API.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, List

import httpx

from a2a.client import ClientFactory, create_text_message_object
from a2a.client.client import ClientConfig
from a2a.client.card_resolver import A2ACardResolver
from a2a.types import AgentCard, Message, Task


CUSTOMER_BASE = os.getenv("CUSTOMER_BASE", "http://127.0.0.1:8010")
SUPPORT_BASE = os.getenv("SUPPORT_BASE", "http://127.0.0.1:8011")


async def _get_agent_card(base_url: str, httpx_client: httpx.AsyncClient) -> AgentCard:
    """에이전트 카드를 가져옵니다."""
    resolver = A2ACardResolver(httpx_client, base_url)
    return await resolver.get_agent_card()


def _extract_text_from_message(msg: Message) -> str:
    """Message 객체에서 텍스트를 추출합니다."""
    if not getattr(msg, "parts", None):
        return ""
    texts = []
    for part in msg.parts:
        if hasattr(part, "root") and hasattr(part.root, "text"):
            texts.append(part.root.text)
        elif isinstance(part, dict) and "root" in part:
            root = part["root"]
            if isinstance(root, dict) and "text" in root:
                texts.append(root["text"])
    return " ".join(texts)


# RAG+LLM 응답 대기용으로 타임아웃을 충분히 둠 (상담원 에이전트가 검색·생성에 시간 소요)
_DEFAULT_HTTP_TIMEOUT = 300.0


async def build_client(base_url: str) -> tuple[Any, httpx.AsyncClient]:
    """base_url의 A2A 에이전트에 연결해 (client, httpx_client) 튜플을 반환합니다."""
    http_client = httpx.AsyncClient(timeout=_DEFAULT_HTTP_TIMEOUT)
    config = ClientConfig(streaming=False, httpx_client=http_client)
    card = await _get_agent_card(base_url, http_client)
    card_jsonrpc = card.model_copy(update={"preferred_transport": "JSONRPC"})
    client = await ClientFactory.connect(card_jsonrpc, client_config=config)
    return (client, http_client)


async def send_to_support(support, question: str) -> str:
    """상담원 에이전트에 질문을 보내고 응답 텍스트를 반환합니다. support는 build_client(SUPPORT_BASE)의 첫 번째 반환값(클라이언트)."""
    msg = create_text_message_object(content=question)
    response_msg = None
    async for event in support.send_message(msg):
        if isinstance(event, Message):
            response_msg = event
            break
    if response_msg:
        return _extract_text_from_message(response_msg)
    return "응답을 받지 못했습니다."


async def ask_customer_followup(customer, support_reply: str) -> str:
    """고객 에이전트에 상담원 답변을 보내고 고객 후속 질문/감사 메시지를 반환합니다. customer는 build_client(CUSTOMER_BASE)의 첫 번째 반환값(클라이언트)."""
    msg = create_text_message_object(content=support_reply)
    response_msg = None
    async for event in customer.send_message(msg):
        if isinstance(event, Message):
            response_msg = event
            break
    if response_msg:
        return _extract_text_from_message(response_msg)
    return "응답을 받지 못했습니다."


def save_transcript(
    transcript: List[dict], prefix: str = "a2a-sim", return_path: bool = False
) -> str | None:
    """transcript([{"who": "customer"|"support", "text": "..."}, ...])를 타임스탬프 붙은 jsonl/md로 저장합니다.
    return_path=True이면 jsonl 파일 경로(문자열)를 반환합니다.
    기본은 utils.py와 같은 디렉터리, 쓰기 실패 시 임시 디렉터리에 저장합니다."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    jsonl_name = f"{prefix}-{ts}.jsonl"
    md_name = f"{prefix}-{ts}.md"

    def write_files(out_dir: Path) -> None:
        jsonl_path = out_dir / jsonl_name
        md_path = out_dir / md_name
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for row in transcript:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        with open(md_path, "w", encoding="utf-8") as f:
            for row in transcript:
                who = row.get("who", "")
                text = (row.get("text") or "").strip()
                f.write(f"**{who}**\n\n{text}\n\n")
        print(f"[LOG] saved -> {jsonl_path} / {md_path}")

    out_dir = Path(__file__).resolve().parent
    try:
        write_files(out_dir)
        final_path = out_dir / jsonl_name
    except OSError as e:
        # PermissionError(13), ReadOnlyFileSystem 등 모든 쓰기 오류에 대비
        fallback_dir = Path(tempfile.gettempdir()) / "a2a-sim"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        try:
            write_files(fallback_dir)
            final_path = fallback_dir / jsonl_name
            print(f"[LOG] 쓰기 실패({e}) → 임시 폴더에 저장: {fallback_dir}")
        except OSError:
            raise

    if return_path:
        return str(final_path.resolve())
    return None
