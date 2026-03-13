import os
import time
import hashlib
from dotenv import load_dotenv
from tqdm import tqdm

# 고도화된 로더 및 스플리터 추가
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchFieldDataType, SearchableField,
    SearchField, VectorSearch, HnswAlgorithmConfiguration, 
    VectorSearchProfile, SemanticConfiguration, SemanticPrioritizedFields,
    SemanticField, SemanticSearch
)
from azure.core.exceptions import ResourceNotFoundError

# 환경 변수 로드
load_dotenv("../../env")
INDEX_NAME = os.getenv("INDEX_NAME", "telecom-terms-index")
EMBED_MODEL = "text-embedding-3-small"

client = AzureOpenAI(
    azure_endpoint=os.getenv("END_POINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview"
)

#인덱스(Index) 생성 및 설정
def delete_and_create_index(index_name):
    """인덱스 초기화 로직 (동일)"""
    credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
    index_client = SearchIndexClient(endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"), credential=credential)

    try:
        index_client.delete_index(index_name)
    except ResourceNotFoundError:
        pass

    # 하이브리드 + 시맨틱 설정
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="my-hnsw")],
        profiles=[VectorSearchProfile(name="my-vector-profile", algorithm_configuration_name="my-hnsw")]
    )

    semantic_search = SemanticSearch(configurations=[
        SemanticConfiguration(
            name="my-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(content_fields=[SemanticField(field_name="content")])
        )
    ])

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="ko.microsoft"),
        SearchField(name="content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True, vector_search_dimensions=1536, vector_search_profile_name="my-vector-profile"),
        SimpleField(name="source", type=SearchFieldDataType.String),
        SimpleField(name="page", type=SearchFieldDataType.Int32),
        SimpleField(name="chunk_id", type=SearchFieldDataType.Int32)
    ]

    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search, semantic_search=semantic_search)
    index_client.create_index(index)

def process_pdf_with_chunking(pdf_path):
    print(f"PyMuPDF로 문서 로드 중: {pdf_path}")
    loader = PyMuPDFLoader(pdf_path)
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    chunks = text_splitter.split_documents(docs)
    print(f"생성된 총 청크 수: {len(chunks)}")
    return chunks

def get_embedding(text):
    return client.embeddings.create(input=[text.replace("\n", " ")], model=EMBED_MODEL).data[0].embedding

def upload_documents(chunks, index_name):
    search_client = SearchClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        index_name=index_name,
        credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
    )
    
    documents = []
    for i, chunk in enumerate(tqdm(chunks, desc="임베딩 및 문서 준비")):
        # 메타데이터 추출
        source_file = os.path.basename(chunk.metadata.get("source", "unknown.pdf"))
        page_num = chunk.metadata.get("page", 0) + 1 # 0-based to 1-based

        documents.append({
            "id": hashlib.md5(f"{source_file}_{i}".encode()).hexdigest(), # 중복 방지 고유 ID
            "content": chunk.page_content,
            "content_vector": get_embedding(chunk.page_content),
            "source": source_file,
            "page": page_num,
            "chunk_id": i
        })
        time.sleep(0.02) # Rate Limit 방지

    print(f"{len(documents)}개 데이터 업로드 중...")
    search_client.upload_documents(documents)
    print("하이브리드 인덱싱 완료!")

def main():
    pdf_path = "../../data/pdf/InternetServiceToU.pdf"
    if os.path.exists(pdf_path):
        delete_and_create_index(INDEX_NAME)
        chunks = process_pdf_with_chunking(pdf_path)
        upload_documents(chunks, INDEX_NAME)
    else:
        print("파일을 찾을 수 없습니다.")

if __name__ == "__main__":
    main()