# https://apidog.com/kr/blog/fastmcp-kr/


from fastmcp import FastMCP

mcp = FastMCP(name="basic_calculator")


@mcp.tool
def add(a: int, b: int) -> int:
    """덧셈 : 두 수를 더합니다. a + b"""
    print(f"덧셈 : {a} + {b}")
    return a + b


@mcp.tool
def subtract(a: int, b: int) -> int:
    """뺄셈 : 두 수를 뺍니다. a - b"""
    print(f"뺄셈 : {a} - {b}")
    return a - b


@mcp.tool
def multiply(a: int, b: int) -> int:
    """곱셈 : 두 수를 곱합니다. a * b"""
    print(f"곱셈 : {a} * {b}")
    return a * b


@mcp.tool
def divide(a: int, b: int) -> int:
    """나눗셈 : 두 수를 나눕니다. a / b"""
    print(f"나눗셈 : {a} / {b}")
    return a / b


@mcp.tool
def square(a: int) -> int:
    """제곱(square) : 수의 제곱을 계산합니다. a ^ 2"""
    print(f"제곱 : {a} ^ 2")
    return a ** 2


@mcp.tool
def square_root(a: int) -> int:
    """제곱근(square_root) : 수의 제곱근을 계산합니다. sqrt(a)"""
    print(f"제곱근 : sqrt({a})")
    return a ** 0.5


APP_CONFIG = {
    "name": "basic_calculator",
    "description": "앱의 구성요소를 제공합니다.",
    "version": "0.0.1",
    "author": "Kim jintae",
    "email": "jt.kim@fake.com",
}


import json

@mcp.resource("data://config")
def get_config() -> str:           # ← str로 변경
    return json.dumps(APP_CONFIG, ensure_ascii=False)


USER_PROFILES = {
    100: {"name": "테스트 유저", "status": "active", "email": "test@test.com", "phone": "010-1234-5678"},
    101: {"name": "민수", "status": "active", "email": "minsoo@test.com", "phone": "010-1234-5678"},
    102: {"name": "영희", "status": "inactive", "email": "younghee@test.com", "phone": "010-1234-5678"},
    103: {"name": "진태", "status": "active", "email": "jintae@test.com", "phone": "010-일2삼三4-56 78"},
}


@mcp.resource("users://{user_id}/profile")
def get_user_profile(user_id: int) -> str:     # ← str로 변경
    return json.dumps(USER_PROFILES.get(user_id, {"error": "사용자를 찾을 수 없습니다."}), ensure_ascii=False)



@mcp.prompt("greeting")
def greeting(name: str) -> str:
    """인사하는 프롬프트를 반환합니다."""
    return f"""당신은 친절한 안내원입니다. 다음의 유저: {name}에게 친절하게 인사하세요."""


if __name__ == "__main__":
    mcp.run(transport="stdio")
