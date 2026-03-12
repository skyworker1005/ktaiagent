"""상담 대화 평가 A2A 에이전트 서버 (RAGAS 기반, 파일 기반 평가).

폴더 내 대화 파일들을 읽어서 RAGAS AspectCritic tool로 평가하고 CSV로 저장합니다.
실행: python a2a_evaluator_server.py  (포트 8012)
"""

import csv
import json
import os
import time
import uvicorn
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("../../env", override=True)

from langchain_openai import AzureChatOpenAI
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from ragas import SingleTurnSample
from ragas.metrics import AspectCritic

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

# #region agent log helper
import time as _dbg_time
import json as _dbg_json

LOG_PATH = "/mnt/c/Users/KaiPharm/dev/ML/강의/langchain/[수업자료]Ch3_멀티_에이전트/.cursor/debug.log"

def _dbg(hid: str, location: str, message: str, data: dict | None = None, run_id: str = "pre-fix") -> None:
    """Append a single NDJSON log line for debug mode."""
    payload = {
        "sessionId": "debug-session",
        "runId": run_id,
        "hypothesisId": hid,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(_dbg_time.time() * 1000),
    }
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(_dbg_json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion



def _get_llm():
    return AzureChatOpenAI(
        model=os.environ.get("MODEL_NAME", ""),
        azure_deployment=os.environ.get("MODEL_NAME", ""),
        azure_endpoint=os.environ.get("END_POINT", ""),
        openai_api_version="2025-03-01-preview",
        openai_api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
    )


def _parse_conversation_from_file(file_path: str) -> tuple[str, str]:
    """JSON 파일에서 고객 질문(user_input)과 상담원 답변(response) 추출."""
    with open(file_path, "r", encoding="utf-8") as f:
        situation = json.load(f)
    
    customer_parts = []
    support_parts = []
    for turn in situation:
        who = turn.get("who", "")
        text = turn.get("text", "")
        if who == "customer":
            customer_parts.append(text)
        elif who == "support":
            support_parts.append(text)
    
    user_input = " ".join(customer_parts) if customer_parts else ""
    response = " ".join(support_parts) if support_parts else ""
    return user_input, response


def _build_evaluator_agent():
    """RAGAS AspectCritic tool을 사용하는 평가 에이전트 생성."""
    llm = _get_llm()
    
    # RAGAS AspectCritic 메트릭 생성
    relevant_metric = AspectCritic(
        name="relevance",
        llm=llm,
        definition="고객 질문에 대해 상담원이 관련 있는 올바른 정보를 제공했는지 평가. 관련 답변을 제공했으면 1, 그렇지 않으면 0.",
    )
    
    polite_metric = AspectCritic(
        name="politeness",
        llm=llm,
        definition="상담원 발화가 예의 있고 공손한지 평가. 예의 있으면 1, 아니면 0.",
    )

    @tool
    def list_evaluation_files(folder_path: str) -> str:
        """평가할 대화 파일 목록을 반환하는 도구.
        
        Args:
            folder_path: eval_runs/run_YYYYMMDD_HHMMSS 형식의 폴더 경로
        
        Returns:
            JSON 문자열: {"files": ["전체경로1", "전체경로2", ...], "folder": "폴더경로"}
        """
        folder = Path(folder_path)
        if not folder.exists():
            return json.dumps({"files": [], "error": f"폴더가 없습니다: {folder_path}"}, ensure_ascii=False)
        files = sorted([str(f) for f in folder.glob("situation_*.json")])
        _dbg("H1", "list_evaluation_files", "listed files", {"folder": str(folder), "count": len(files)})
        return json.dumps({"files": files, "folder": str(folder), "count": len(files)}, ensure_ascii=False)

    @tool
    async def evaluate_file_relevance(file_path: str) -> str:
        """파일에서 대화를 읽어 관련성을 평가하는 RAGAS 도구.
        
        Args:
            file_path: situation_XX.json 파일의 전체 경로 (예: eval_runs/run_xxx/situation_00.json)
        
        Returns:
            "1" (관련 답변) 또는 "0" (관련 없음)
        """
        try:
            user_input, response = _parse_conversation_from_file(file_path)
            if not user_input or not response:
                _dbg("H2", "evaluate_file_relevance", "missing content", {"file": file_path, "user_len": len(user_input), "resp_len": len(response)})
                return "0"
            sample = SingleTurnSample(user_input=user_input, response=response)
            score = await relevant_metric.single_turn_ascore(sample)
            _dbg("H2", "evaluate_file_relevance", "scored", {"file": file_path, "score": score})
            return str(int(score))
        except Exception:
            return "0"

    @tool
    async def evaluate_file_politeness(file_path: str) -> str:
        """파일에서 대화를 읽어 예의성을 평가하는 RAGAS 도구.
        
        Args:
            file_path: situation_XX.json 파일의 전체 경로
        
        Returns:
            "1" (예의 있음) 또는 "0" (예의 없음)
        """
        try:
            user_input, response = _parse_conversation_from_file(file_path)
            if not user_input or not response:
                _dbg("H3", "evaluate_file_politeness", "missing content", {"file": file_path, "user_len": len(user_input), "resp_len": len(response)})
                return "0"
            sample = SingleTurnSample(user_input=user_input, response=response)
            score = await polite_metric.single_turn_ascore(sample)
            _dbg("H3", "evaluate_file_politeness", "scored", {"file": file_path, "score": score})
            return str(int(score))
        except Exception:
            return "0"

    @tool
    def save_evaluation_results_csv(results_json: str, output_folder: str = "evaluation_results") -> str:
        """평가 결과 리스트를 CSV 파일로 저장하는 도구.
        
        Args:
            results_json: JSON 문자열, [{"file": "situation_00.json", "relevant": 1, "polite": 1}, ...] 형식
            output_folder: 저장할 폴더명 (기본값: evaluation_results)
        
        Returns:
            저장된 파일 경로
        """
        try:
            results = json.loads(results_json)
            if not results:
                return "오류: 결과가 비어있습니다."
            
            output_dir = Path(output_folder)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            csv_path = output_dir / f"evaluation_results_{timestamp}.csv"
            
            # file 필드가 전체 경로일 수 있으므로 파일명만 추출
            normalized_results = []
            for row in results:
                file_val = row.get("file", "")
                if "/" in file_val or "\\" in file_val:
                    file_val = Path(file_val).name
                normalized_results.append({
                    "file": file_val,
                    "relevant": row.get("relevant", 0),
                    "polite": row.get("polite", 0),
                })
            
            fieldnames = ["file", "relevant", "polite"]
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in normalized_results:
                    writer.writerow(row)
            
            _dbg("H4", "save_evaluation_results_csv", "csv saved", {"path": str(csv_path), "count": len(normalized_results)})
            return f"저장 완료: {csv_path} (총 {len(normalized_results)}건)"
        except Exception:
            return "CSV 저장 중 오류 발생"

    tools = [list_evaluation_files, evaluate_file_relevance, evaluate_file_politeness, save_evaluation_results_csv]
    
    system_prompt = """너는 상담 대화 평가 에이전트다. 폴더 기반 평가 워크플로우를 정확히 따라라:

1) list_evaluation_files(folder_path): 평가할 폴더 경로를 넣어 파일 목록(전체 경로) 확인
2) 각 파일(전체 경로)에 대해:
   - evaluate_file_relevance(file_path): 관련성 평가 (0 또는 1 반환)
   - evaluate_file_politeness(file_path): 예의성 평가 (0 또는 1 반환)
3) 모든 파일 평가가 끝나면, 결과를 JSON 배열로 모아서:
   [{"file": "situation_00.json", "relevant": 1, "polite": 1}, {"file": "situation_01.json", "relevant": 0, "polite": 1}, ...]
   형식으로 정리
4) save_evaluation_results_csv(results_json, "evaluation_results")로 CSV 저장

중요: 
- list_evaluation_files가 반환한 "files" 배열의 각 항목(전체 경로)을 그대로 evaluate_file_relevance와 evaluate_file_politeness에 전달하라
- 모든 파일 평가가 끝난 뒤에만 save_evaluation_results_csv를 한 번 호출하라
- file 필드는 파일명만 (예: "situation_00.json") 저장하라"""

    return create_agent(llm, tools, system_prompt=system_prompt, checkpointer=InMemorySaver())


class EvaluatorAgentExecutor(AgentExecutor):
    """폴더 경로를 받아 파일 기반으로 RAGAS tool로 평가하고 CSV 저장."""

    def __init__(self):
        self._agent = _build_evaluator_agent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raw = (context.get_user_input(delimiter="\n") or "").strip()
        _dbg("H5", "execute", "entry", {"raw_len": len(raw), "context_id": context.context_id})
        if not raw:
            await event_queue.enqueue_event(
                new_agent_text_message(
                    "평가할 폴더 경로를 입력하세요. 예: eval_runs/run_20260205_120000",
                    context_id=context.context_id,
                )
            )
            return

        try:
            result = await self._agent.ainvoke(
                {"messages": [{"role": "user", "content": raw}]},
                config={"configurable": {"thread_id": context.context_id or "eval-1"}},
            )
            messages = result.get("messages", [])
            output_text = messages[-1].content if messages and hasattr(messages[-1], "content") else ""
            
            if not output_text:
                output_text = "평가 완료. 결과를 확인하세요."
            _dbg("H5", "execute", "agent success", {"output_len": len(output_text)})
        except Exception:
            output_text = "평가 중 오류 발생"
            _dbg("H5", "execute", "agent error", {"error": "exception"})

        await event_queue.enqueue_event(
            new_agent_text_message(output_text, context_id=context.context_id)
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise NotImplementedError("Cancel is not supported")


skill = AgentSkill(
    id="eval_support_conversation",
    name="Evaluate support conversation",
    description="Evaluate conversation files in a folder using RAGAS AspectCritic tools and save results to CSV",
    tags=["evaluation", "support", "conversation", "ragas", "file-based"],
    examples=["eval_runs/run_20260205_120000 폴더의 파일들을 평가해줘"],
)

public_agent_card = AgentCard(
    name="evaluator-agent",
    description="Evaluates support conversation files using RAGAS AspectCritic tools and saves to CSV",
    url="http://127.0.0.1:8012/",
    preferred_transport="JSONRPC",
    version="0.3.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[skill],
    supports_authenticated_extended_card=False,
)


def run_a2a_server(executor: AgentExecutor, agent_card: AgentCard, port: int, host: str = "127.0.0.1") -> None:
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    ).build(
        agent_card_url="/.well-known/agent-card.json",
        rpc_url="/",
    )
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    print("평가 에이전트가 빌드 되었습니다 (RAGAS AspectCritic tool, 파일 기반 평가).")
    run_a2a_server(EvaluatorAgentExecutor(), public_agent_card, port=8012)
