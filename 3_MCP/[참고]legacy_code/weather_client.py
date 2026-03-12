# client_open_meteo.py
import os, asyncio
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession

MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp")

async def main():
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("[TOOLS]", [t.name for t in tools.tools])

            # 현재 날씨 호출 (서울 근처: 위도 37.57, 경도 126.98)
            result = await session.call_tool(
                "get_current_weather",
                {"latitude": 37.57, "longitude": 126.98},
            )

            print("\n[RESULT]")
            for c in result.content:
                print(c.text)
                # for k in c.keys():
                #     print(f"{k}: {c[k]}")

if __name__ == "__main__":
    asyncio.run(main())
