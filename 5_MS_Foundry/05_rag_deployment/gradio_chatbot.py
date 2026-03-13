import gradio as gr
import requests

# API 엔드포인트 (test_rag_remote.py와 동일한 형식)
BASE_URL = "https://rag-agent-api-2.jollyriver-05a3f375.westus2.azurecontainerapps.io"
def _content_to_str(content):
    """Gradio 메시지 content를 문자열로 변환 (문자열 또는 리스트 형식 모두 처리)"""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
        return " ".join(parts).strip()
    return ""

def chat_with_rag(query, thread_id):
    """
    RAG API에 질문을 보내고 응답 문자열을 반환하는 함수
    
    Args:
        query: 사용자 질문 (문자열 또는 Gradio content 리스트)
        thread_id: 대화 스레드 ID
    
    Returns:
        응답 문자열 (에러 시 에러 메시지)
    """
    query = _content_to_str(query)
    if not query:
        return ""
    
    try:
        # API 요청 (test_rag_remote.py와 동일한 형식)
        url = f"{BASE_URL}/chat"
        headers = {"Content-Type": "application/json"}
        payload = {
            "query": query,
            "thread_id": thread_id if thread_id else "user1"
        }
        
        # RAG+에이전트 응답이 느릴 수 있음 (검색·LLM·Cosmos DB 등)
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "응답을 받을 수 없습니다.")
            
    except requests.exceptions.RequestException as e:
        return f"❌ 네트워크 에러: {str(e)}"
    except Exception as e:
        return f"❌ 에러: {str(e)}"

def create_chatbot_interface():
    """Gradio 챗봇 인터페이스를 생성하고 반환하는 함수"""
    # Gradio 인터페이스 생성
    with gr.Blocks(title="통신사 고객 상담 RAG 챗봇", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 📞 통신사 고객 상담 RAG 챗봇
            
            Azure Container Apps에 배포된 RAG 시스템을 사용하는 챗봇입니다.
            통신사 약관에 대한 질문을 자유롭게 해보세요!
            (첫 응답은 1~2분 걸릴 수 있습니다.)
            """
        )
        
        with gr.Row():
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    label="대화",
                    height=500
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="질문 입력",
                        placeholder="예: giga wifi가 뭐야?",
                        scale=4,
                        container=False
                    )
                    submit_btn = gr.Button("전송", variant="primary", scale=1)
            
            with gr.Column(scale=1):
                thread_id_input = gr.Textbox(
                    label="Thread ID",
                    value="user1",
                    placeholder="user1",
                    info="대화 세션을 구분하는 ID입니다"
                )
                clear_btn = gr.Button("대화 초기화", variant="stop")
                gr.Markdown(
                    """
                    ### 💡 사용 팁
                    - Thread ID를 변경하면 새로운 대화 세션이 시작됩니다
                    - 같은 Thread ID를 사용하면 이전 대화 맥락을 유지합니다
                    - "그 서비스는?" 같은 맥락 질문도 가능합니다
                    """
                )
        
        # 이벤트 핸들러 (Gradio Chatbot 형식: {"role": "user"|"assistant", "content": "..."})
        def user_message(user_msg, thread_id, history):
            return "", history + [{"role": "user", "content": user_msg}]
        
        def bot_message(history, thread_id):
            # content가 문자열 또는 리스트일 수 있음
            query = _content_to_str(history[-1]["content"])
            answer = chat_with_rag(query, thread_id)
            return history + [{"role": "assistant", "content": answer}]
        
        msg.submit(
            user_message,
            inputs=[msg, thread_id_input, chatbot],
            outputs=[msg, chatbot]
        ).then(
            bot_message,
            inputs=[chatbot, thread_id_input],
            outputs=[chatbot]
        )
        
        submit_btn.click(
            user_message,
            inputs=[msg, thread_id_input, chatbot],
            outputs=[msg, chatbot]
        ).then(
            bot_message,
            inputs=[chatbot, thread_id_input],
            outputs=[chatbot]
        )
        
        clear_btn.click(lambda: ([], "user1"), outputs=[chatbot, thread_id_input])  # 빈 히스토리 = messages 형식 []
    
    return demo

if __name__ == "__main__":
    demo = create_chatbot_interface()
    demo.launch(share=True, server_name="0.0.0.0", server_port=7860)
