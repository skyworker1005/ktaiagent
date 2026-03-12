
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


def build_agent():

    loader = PyMuPDFLoader(
        "../../data/pdf/InternetServiceToU.pdf", mode="page")
    docs = loader.load()
    for doc in docs:
        doc.metadata["producer"] = ""
        doc.metadata["creator"] = ""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
        separators=["\n\n", "\n", "  ", " "]
    )
    splits = splitter.split_documents(docs)
    vectordb = FAISS.from_documents(splits, embeddings)

    @tool(response_format="content")
    def retrieve_context(query: str):
        """질문에 대한 정보를 검색하는 도구
        ## return data는 아래 두 가지
        - serialized : 검색된 문서의 내용의 직렬화된 문자열
        - retrieved_docs : 검색된 문서의 목록(document의 list)"""
        retrieved_docs = vectordb.similarity_search(query, k=5)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\nContent: {doc.page_content}")
            for doc in retrieved_docs
        )
        return serialized

    tools = [retrieve_context]
    prompt = (
        "너는 통신사 고객상담을 위한 이용약관 문서 기반 QA 어시스턴트다. 한국어로 간단하게 답하고 아래 규칙을 지켜라.\n"
        "1) 제공된 컨텍스트(표/본문)에서만 근거를 찾아 답한다.\n"
        "2) 컨텍스트 내에 해당하는 정보가 없으면 모른다고 말한다. 추측 금지.\n"
        "3) 숫자/조건/예외는 정확히 인용하라.\n"
        "4) 표 내용이라면 행/열 헤더를 함께 언급해 맥락을 명확히 한다.\n"
        "5) 필요한 경우 네가 고객에게 질문을 하거나 정보를 요청할 수 있다.\n"
        "5) 마지막에 참조한 문서와 출처 페이지를 인용하라.\n"
    )

    return create_agent(llm, tools, system_prompt=prompt, checkpointer=InMemorySaver())
