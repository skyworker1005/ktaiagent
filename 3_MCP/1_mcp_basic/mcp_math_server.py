from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b


# 로컬 서브프로세스로 실행
# LangChain이 MCP 서버 프로그램을 직접 실행해서 메시지를 교환
# 보안이 좋고 빠르다.
if __name__ == "__main__":
    mcp.run(transport="stdio")
