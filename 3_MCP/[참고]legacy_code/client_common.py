import os
import json
from typing import Any, Dict, Optional, Iterable
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession

MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp")


class MCPClient:
    """
    Streamable HTTP 기반 MCP 세션 래퍼.
    - tool/resource/prompt 공통 사용 메서드 제공
    - 결과를 문자열로 정규화한 *_text 계열 메서드 포함
    """

    def __init__(self, url: str = MCP_URL):
        self.url = url
        self._ctx = None
        self._read = None
        self._write = None
        self._session: Optional[ClientSession] = None

    async def __aenter__(self):
        """
        Streamable HTTP 기반 MCP 세션 래퍼 초기화.
        """
        self._ctx = streamablehttp_client(self.url)
        self._read, self._write, _ = await self._ctx.__aenter__()
        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        Streamable HTTP 기반 MCP 세션 래퍼 종료.
        """
        if self._session:
            await self._session.__aexit__(exc_type, exc, tb)
        if self._ctx:
            await self._ctx.__aexit__(exc_type, exc, tb)

    async def list_tools(self) -> Iterable[str]:
        """
        툴 목록 조회.
        """
        resp = await self._session.list_tools()
        return [t.name for t in resp.tools]

    async def call(self, tool: str, args: Any) -> Dict[str, Any]:
        """
        툴 호출 (원형): 결과를 dict({"content":[{"text":...},...]})로 리턴
        """
        res = await self._session.call_tool(tool, arguments=args)
        out = []
        for c in (res.content or []):
            ctype = getattr(c, "type", None)
            if ctype == "text":
                out.append({"text": getattr(c, "text", "")})
            elif ctype == "json":
                out.append(
                    {"text": json.dumps(getattr(c, "json", {}), ensure_ascii=False)})
            else:
                out.append({"text": str(c)})
        return {"content": out}

    async def read(self, uri: str) -> str:
        """
        리소스 읽기 (원형): 문자열 하나로 합쳐 리턴
        """
        res = await self._session.read_resource(uri)
        parts = []
        for c in res.contents:
            ctype = getattr(c, "type", None)
            if ctype == "text":
                parts.append(getattr(c, "text", ""))
            elif ctype == "json":
                parts.append(json.dumps(
                    getattr(c, "json", {}), ensure_ascii=False))
            else:
                parts.append(str(c))
        return "\n".join(parts).strip()

    async def prompt(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        프롬프트 실행 (원형): messages를 보기 좋은 문자열로 합쳐 반환
        """
        res = await self._session.get_prompt(name, arguments=arguments)
        parts = []
        for m in res.messages:
            role = getattr(m, "role", "")
            content = getattr(m, "content", "")
            if isinstance(content, list):
                cparts = []
                for c in content:
                    if getattr(c, "type", None) == "text":
                        cparts.append(getattr(c, "text", ""))
                    else:
                        cparts.append(str(c))
                content = "\n".join(cparts)
            parts.append(f"[{role}] {content}" if role else str(content))
        return "\n".join(parts).strip()

    async def call_text(self, tool: str, args: Dict[str, Any]) -> str:
        """
        툴 호출 → 문자열 하나로 합쳐 반환.
        (외부에서 _mcp_call 대신 이 메서드를 사용)
        """
        result = await self.call(tool, args)
        return "\n".join(
            (c.get("text", "") if isinstance(c, dict) else str(c))
            for c in (result.get("content") or [])
        ).strip()

    async def read_text(self, uri: str) -> str:
        """
        리소스 읽기 → 문자열 반환.
        (외부에서 _mcp_read 대신 이 메서드를 사용)
        """
        return await self.read(uri)

    async def prompt_text(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        프롬프트 실행 → 문자열 반환.
        (외부에서 _mcp_prompt 대신 이 메서드를 사용)
        """
        return await self.prompt(name, arguments)
