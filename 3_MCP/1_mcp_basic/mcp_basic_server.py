from fastmcp import FastMCP

mcp = FastMCP(name="mcp_basic_example")


@mcp.tool
def say_hello(name: str) -> str:
    """이름(name)을 받아서 인사말을 반환합니다."""
    return f"Hello, {name}! Nice to meet you."


APP_INFO = {
    "name": "mcp_basic_example",
    "description": "앱의 구성요소를 제공합니다.",
    "version": "0.0.1",
    "author": "Kim jintae",
    "email": "jt.kim@fake.com",
}


# 읽기 전용 데이터 컨텍스트
# 고유 URI를 가지고 있어서 해당 URI를 통해 데이터를 가져올 수 있음
# @mcp.resource("myinfo://app-info")
# def get_app_info() -> dict:
#     "앱의 정보를 제공합니다."
#     return APP_INFO

  # ✅ 수정 (str로 반환)
import json

@mcp.resource("myinfo://app-info")
def get_app_info() -> str:
    "앱의 정보를 제공합니다."
    return json.dumps(APP_INFO, ensure_ascii=False)

# 미리 설계된 템플릿
@mcp.prompt
def language(country: str, name: str) -> str:
    """country(string)와 name(string)을 받아서 해당 국가의 언어로 인사하는 프롬프트를 반환합니다."""
    return f"해당 나라의 언어로 짧고 친절하게 인사해줘. 국가 : '{country}', 이름 : '{name}'"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
