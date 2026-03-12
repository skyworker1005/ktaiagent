# uv run --active python minimal_client.py
import asyncio
import json
import logging
from uuid import uuid4

import httpx


BASE_URL = "http://localhost:9999"
CARD_PATH = "/.well-known/agent-card.json"  # 서버가 이 경로로 카드 제공
DEFAULT_SEND_PATH = "/messages"             # 기본 REST 엔드포인트
DEFAULT_STREAM_PATH = "/messages/stream"    # 기본 스트리밍 엔드포인트(있으면)


async def main():
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("client")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as http:
        # 1) 에이전트 카드 조회
        log.info(f"GET {CARD_PATH}")
        r = await http.get(CARD_PATH)
        r.raise_for_status()
        card = r.json()
        log.info("Agent Card:\n" + json.dumps(card, indent=2, ensure_ascii=False))
        
        log.info("=========================================================")

        # 2) 카드에서 HTTP 엔드포인트 추출(없으면 기본값 사용)
        http_meta = card.get("http", {}) if isinstance(card, dict) else {}
        endpoints = http_meta.get("endpoints", {}) if isinstance(http_meta, dict) else {}
        send_path = endpoints.get("sendMessage", DEFAULT_SEND_PATH)
        stream_path = endpoints.get("sendMessageStreaming", DEFAULT_STREAM_PATH)

        # 3) 단건 메시지 호출
        payload = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": "how much is 10 USD in INR?"}],
                "messageId": uuid4().hex,
            }
        }
        log.info(f"POST {send_path}")
        
        log.info("=========================================================")
        
        resp = await http.post(send_path, json=payload)
        resp.raise_for_status()
        print("\n=== /messages response ===")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
