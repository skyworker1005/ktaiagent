
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from uuid import uuid4
from typing import Dict
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv
import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser

load_dotenv('../../env', override=True)
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
END_POINT = os.getenv('END_POINT')
MODEL_NAME = os.getenv('MODEL_NAME')

AZURE_OPENAI_EMB_API_KEY = os.getenv('AZURE_OPENAI_EMB_API_KEY')
EMB_END_POINT = os.getenv('EMB_END_POINT')
EMB_MODEL_NAME = os.getenv('EMB_MODEL_NAME')


llm = AzureChatOpenAI(
    model=os.environ['MODEL_NAME'],
    azure_deployment=os.environ["MODEL_NAME"],
    azure_endpoint=os.environ["END_POINT"],
    openai_api_version="2025-03-01-preview",
    openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
)

embeddings = AzureOpenAIEmbeddings(
    model=os.environ["EMB_MODEL_NAME"],
    azure_endpoint=os.environ["EMB_END_POINT"],
    azure_deployment=os.environ["EMB_MODEL_NAME"],
    openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
)

_HISTORY_STORE: Dict[str, ChatMessageHistory] = {}

def get_session_history(session_id: str) -> ChatMessageHistory:
    """세션ID별 InMemory 히스토리 반환(없으면 생성)."""
    if session_id not in _HISTORY_STORE:
        _HISTORY_STORE[session_id] = ChatMessageHistory()
    return _HISTORY_STORE[session_id]

def build_agent():
    """
    입력: support_reply (상담원 답변 전문)
    출력: 고객 입장에서 '후속 질문 1개' 또는 해결 시 '감사합니다'
    """
    system_msg = (
        "너는 통신사 고객 역할을 연기하는 에이전트다.\n"
        "규칙:\n"
        "1) 입력된 상담원 답변(support_reply)을 읽고, 대화의 맥락과 톤, 성격을 일관되게 고려하여 \n"
        "   고객 입장에서 자연스러운 '후속 질문 1개'만 생성한다.\n"
        "2) 이해가 되지 않는 부분이 있으면 상담원에게 재질문을 할 수도 있다.\n"
        "3) 어느 정도 궁금증이 해결되었다고 판단되면 '감사합니다' 한 단어만 출력한다.\n"
        "4) 접두사/말머리(예: '고객:')는 붙이지 말고 결과만 출력한다."
        "5) 실제 고객인 것처럼 행동하라"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_msg),
        MessagesPlaceholder("history"),
        ("human",
         "상담원 답변(support_reply):\n{support_reply}\n\n")
    ])

    core = prompt | llm | StrOutputParser()

    chain = RunnableWithMessageHistory(
        core,
        get_session_history,
        input_messages_key="input_text",
        history_messages_key="history",
    )
    return chain
