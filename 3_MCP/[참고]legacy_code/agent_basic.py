from langchain.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from client_common import MCPClient
from langchain.tools import tool
import os
import asyncio

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv('../env', override=True)
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
END_POINT = os.getenv('END_POINT')
MODEL_NAME = os.getenv('MODEL_NAME')
print(AZURE_OPENAI_API_KEY[:10])
print(MODEL_NAME)

AZURE_OPENAI_EMB_API_KEY = os.getenv('AZURE_OPENAI_EMB_API_KEY')
EMB_END_POINT = os.getenv('EMB_END_POINT')
EMB_MODEL_NAME = os.getenv('EMB_MODEL_NAME')

os.environ['LANGCHAIN_API_KEY'] = os.getenv('LANGSMITH_API_KEY')
os.environ['LANGCHAIN_ENDPOINT'] = os.getenv('LANGCHAIN_ENDPOINT')
os.environ['LANGCHAIN_TRACING_V2'] = 'true'  # true, false
os.environ['LANGCHAIN_PROJECT'] = 'AGENT'

if os.getenv('LANGCHAIN_TRACING_V2') == "true":
    if len(os.getenv('LANGCHAIN_API_KEY')) > 0:
        print('랭스미스로 추적 중입니다 :', os.getenv('LANGSMITH_API_KEY')[:10])
    else:
        print('랭스미스 키가 확인되지 않았습니다.')


MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp")


@tool("say_hello")
async def say_hello(name: str) -> str:
    """이름을 받아서 인사합니다."""
    async with MCPClient() as cli:
        return await cli.call("say_hello", {"name": name})


@tool("app_info")
async def app_info() -> str:
    """앱의 정보를 반환합니다."""
    async with MCPClient() as cli:
        return await cli.read("myinfo://app-info")


@tool("tool_list")
async def tool_list() -> str:
    """사용할 수 있는 툴 목록을 반환합니다."""
    async with MCPClient() as cli:
        return await cli.list_tools()

TOOLS = [say_hello, app_info, tool_list]

PROMPT = """
당신은 친절한 안내원입니다. 유저에게 친절하게 인사하세요.
도구를 적절히 사용해 유저의 요청을 처리하세요.

상대가 이름을 밝힐경우 say_hello 툴을 사용하세요.
상대가 인사를 원하지만 이름을 밝히지 않을경우 임의의 이름을 만들어서 say_hello 툴을 사용하세요.
앱의 정보는 app_info에 들어가 있습니다.
사용할 수 있는 툴 목록은 tool_list에 들어가 있습니다.

tool을 사용할 필요가 없는 일반적인 질문에 대해서는 tool을 콜링하지 말고 간단하고 친절하게 답변하세요.
"""


def build_agent():

    llm = AzureChatOpenAI(
        model=os.environ['MODEL_NAME'],
        azure_deployment=os.environ["MODEL_NAME"],
        azure_endpoint=os.environ["END_POINT"],
        openai_api_version="2025-03-01-preview",
        openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )
    return create_agent(llm, TOOLS, system_prompt=PROMPT, checkpointer=InMemorySaver())


async def main():
    agent = build_agent()
    session_id = "1"

    while True:
        user_in = input("> ").strip()
        if not user_in:
            continue
        if user_in.lower() in ("/q", "/quit", "exit"):
            print("종료합니다.")
            break
        result = await agent.ainvoke({"messages": [{"role": "user", "content": user_in}]}, config={"configurable": {"session_id": session_id}})
        answer = result['messages'][-1].content
        print(answer)

if __name__ == "__main__":
    asyncio.run(main())
