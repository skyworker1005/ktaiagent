import os
from langchain_core.tools import tool

# 데이터 저장 디렉토리 설정 (없으면 생성)
DATA_DIR = "./agent_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

@tool
def save_file(filename: str, content: str) -> str:
    """
    에이전트가 작업한 내용이나 수집한 데이터를 파일로 저장합니다.
    - filename: 저장할 파일 이름 (예: 'gdp_data.txt', 'result.csv')
    - content: 저장할 텍스트 내용
    """
    try:
        file_path = os.path.join(DATA_DIR, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"성공적으로 '{file_path}'에 저장되었습니다."
    except Exception as e:
        return f"파일 저장 중 오류 발생: {str(e)}"

@tool
def list_data_files() -> str:
    """
    agent_data 폴더 내에 있는 모든 파일의 목록을 가져옵니다.
    에이전트가 어떤 데이터 파일이 저장되어 있는지 확인하고 싶을 때 사용합니다.
    """
    try:
        if not os.path.exists(DATA_DIR):
            return f"안내: '{DATA_DIR}' 폴더가 존재하지 않습니다. 아직 생성된 파일이 없습니다."
        
        files = os.listdir(DATA_DIR)
        if not files:
            return f"안내: '{DATA_DIR}' 폴더가 비어 있습니다."
        
        # 파일 목록을 줄바꿈으로 구분하여 문자열로 반환
        file_list = "\n".join([f"- {f}" for f in files])
        return f"현재 '{DATA_DIR}' 폴더 내 파일 목록:\n{file_list}"
    except Exception as e:
        return f"파일 목록을 가져오는 중 오류 발생: {str(e)}"

@tool
def read_file(filename: str) -> str:
    """
    지정한 파일의 내용을 읽어옵니다. 
    이전 에이전트가 저장한 데이터를 참조할 때 유용합니다.
    - filename: 읽어올 파일 이름
    """
    try:
        file_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(file_path):
            return f"오류: '{filename}' 파일을 찾을 수 없습니다."
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        return f"파일 읽기 중 오류 발생: {str(e)}"
    
@tool
def delete_file(filename: str) -> str:
    """
    agent_data 폴더 내의 특정 파일을 삭제합니다.
    불필요해진 임시 파일이나 잘못된 데이터 파일을 제거할 때 사용합니다.
    - filename: 삭제할 파일 이름 (예: 'temp_data.txt')
    """
    try:
        file_path = os.path.join(DATA_DIR, filename)
        
        if not os.path.exists(file_path):
            return f"오류: '{filename}' 파일을 찾을 수 없어 삭제에 실패했습니다."
        
        os.remove(file_path)
        return f"성공적으로 '{filename}' 파일을 삭제했습니다."
    except Exception as e:
        return f"파일 삭제 중 오류 발생: {str(e)}"