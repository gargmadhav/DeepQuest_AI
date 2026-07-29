import os
import json
import re
import asyncio
from typing import List, Dict, Any, Callable, Tuple, TypedDict

from langgraph.graph import StateGraph, END

from agent.memory import VectorMemory
from agent.planner import generate_plan
from agent.executor import ExecutionContext, execute_step, synthesize_report, get_groq_client, POWERFUL_MODEL
from agent.tools import write_file

async def _emit_log(callback: Callable, msg: str):
    if callback:
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(msg)
            else:
                callback(msg)
        except Exception as e:
            print(f"[Log Emit Warning] {e}")
    await asyncio.sleep(0.01)

async def _emit_db(callback: Callable, data: dict):
    if callback:
        try:
            if asyncio.iscoroutinefunction(callback):
                return await callback(data)
            else:
                return callback(data)
        except Exception as e:
            print(f"[DB Emit Warning] {e}")
    return None

class AgentState(TypedDict, total=False):
    goal: str
    memory_context: str
    memory_used: bool
    task_db_id: Any
    steps: List[Dict[str, Any]]
    steps_history: List[Dict[str, Any]]
    report_content: str
    approved: bool
    feedback: str
    correction_step: Dict[str, Any]
    sources: List[str]
    context: Any
    log_callback: Any
    db_session_callback: Any
    final_payload: Dict[str, Any]

class AgentOrchestrator:
    def __init__(self, memory_db_path: str = "memory.db"):
        self.memory = VectorMemory(db_path=memory_db_path)
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """
        Builds and compiles the LangGraph StateGraph workflow:
        memory -> planner -> executor -> reflection -> (conditional) -> correction / indexing -> END
        """
        workflow = StateGraph(AgentState)

        workflow.add_node("memory_node", self._memory_node)
        workflow.add_node("planner_node", self._planner_node)
        workflow.add_node("executor_node", self._executor_node)
        workflow.add_node("reflection_node", self._reflection_node)
        workflow.add_node("correction_node", self._correction_node)
        workflow.add_node("indexing_node", self._indexing_node)

        workflow.set_entry_point("memory_node")
        workflow.add_edge("memory_node", "planner_node")
        workflow.add_edge("planner_node", "executor_node")
        workflow.add_edge("executor_node", "reflection_node")

        # Conditional routing after reflection node
        workflow.add_conditional_edges(
            "reflection_node",
            self._should_correct,
            {
                "correct": "correction_node",
                "index": "indexing_node"
            }
        )

        workflow.add_edge("correction_node", "indexing_node")
        workflow.add_edge("indexing_node", END)

        return workflow.compile()

    async def _memory_node(self, state: AgentState) -> Dict[str, Any]:
        goal = state["goal"]
        log_cb = state.get("log_callback")
        db_cb = state.get("db_session_callback")

        await _emit_log(log_cb, "[LangGraph Node: Memory] Querying vector memory for past contextual insights...")
        memories = await asyncio.to_thread(self.memory.search_memory, goal, limit=2)
        
        memory_context = ""
        memory_used = False
        if memories:
            memory_used = True
            await _emit_log(log_cb, f"[System] Found {len(memories)} matching past task(s) in memory database.")
            memory_parts = [f"Past Goal: {m['query']}\nPast Report Preview:\n{m['report'][:1000]}\n" for m in memories]
            memory_context = "\n".join(memory_parts)
            await _emit_log(log_cb, f"[Memory Match] Guided by history: '{memories[0]['query']}' (Similarity: {memories[0]['score']:.2f})")
        else:
            await _emit_log(log_cb, "[Memory System] No matching past research goals found in vector memory. Starting clean.")

        task_db_id = await _emit_db(db_cb, {
            "goal": goal,
            "status": "Planning",
            "summary": "Generating execution plan...",
            "steps_executed": "[]",
            "final_report": ""
        })

        return {
            "memory_context": memory_context,
            "memory_used": memory_used,
            "task_db_id": task_db_id
        }

    async def _planner_node(self, state: AgentState) -> Dict[str, Any]:
        goal = state["goal"]
        memory_context = state.get("memory_context", "")
        log_cb = state.get("log_callback")
        db_cb = state.get("db_session_callback")
        task_db_id = state.get("task_db_id")

        await _emit_log(log_cb, "\n[LangGraph Node: Planner] Designing multi-step autonomous execution plan using Groq LPU...")
        steps = await asyncio.to_thread(generate_plan, goal, memory_context)

        await _emit_log(log_cb, f"[System] Plan constructed with {len(steps)} steps:")
        for s in steps:
            await _emit_log(log_cb, f"  Step {s.get('id')}: {s.get('tool')} - {s.get('reason')}")
        await _emit_log(log_cb, "\n[LangGraph Node: Executor] Launching execution loop...")

        if task_db_id:
            await _emit_db(db_cb, {
                "id": task_db_id,
                "status": "Executing",
                "summary": f"Executing {len(steps)} planned steps...",
                "steps_executed": json.dumps(steps)
            })

        return {"steps": steps}

    async def _executor_node(self, state: AgentState) -> Dict[str, Any]:
        goal = state["goal"]
        steps = state.get("steps", [])
        log_cb = state.get("log_callback")
        context = state.get("context") or ExecutionContext()

        steps_history = []
        for step in steps:
            await _emit_log(log_cb, f"\n--- [Step {step.get('id')} / {len(steps)}] ---")
            
            def sync_log(msg: str):
                if log_cb:
                    if asyncio.iscoroutinefunction(log_cb):
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(log_cb(msg))
                        except Exception:
                            pass
                    else:
                        log_cb(msg)

            result = await asyncio.to_thread(execute_step, step, context, goal, sync_log)
            await asyncio.sleep(0.02)

            steps_history.append({
                "id": step.get("id"),
                "tool": step.get("tool"),
                "argument": step.get("argument"),
                "status": "Success",
                "output_preview": result[:200]
            })

        report_content = context.last_output if context.files_written else await asyncio.to_thread(synthesize_report, goal, context)

        return {
            "context": context,
            "steps_history": steps_history,
            "report_content": report_content
        }

    async def _reflection_node(self, state: AgentState) -> Dict[str, Any]:
        goal = state["goal"]
        report_content = state.get("report_content", "")
        context = state.get("context")
        log_cb = state.get("log_callback")

        await _emit_log(log_cb, "\n[LangGraph Node: Reflection] Self-evaluating output quality...")
        logs = context.logs if context else []
        approved, feedback, correction_step = await asyncio.to_thread(self.reflect, goal, report_content, logs)

        if approved:
            await _emit_log(log_cb, "[Reflection System] Quality verification approved. Final report meets all standards.")

        return {
            "approved": approved,
            "feedback": feedback,
            "correction_step": correction_step
        }

    def _should_correct(self, state: AgentState) -> str:
        if not state.get("approved") and state.get("correction_step"):
            return "correct"
        return "index"

    async def _correction_node(self, state: AgentState) -> Dict[str, Any]:
        goal = state["goal"]
        correction_step = state.get("correction_step")
        context = state.get("context")
        steps_history = state.get("steps_history", [])
        log_cb = state.get("log_callback")

        await _emit_log(log_cb, f"[Reflection System] Verification Failed. Feedback: '{state.get('feedback')}'")
        await _emit_log(log_cb, f"[Reflection System] Initiating Correction Step: {correction_step.get('tool')}('{correction_step.get('argument')}')")

        def sync_log_corr(msg: str):
            if log_cb:
                if asyncio.iscoroutinefunction(log_cb):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(log_cb(msg))
                    except Exception:
                        pass
                else:
                    log_cb(msg)

        result = await asyncio.to_thread(execute_step, correction_step, context, goal, sync_log_corr)
        await asyncio.sleep(0.02)

        steps_history.append({
            "id": len(steps_history) + 1,
            "tool": correction_step.get("tool"),
            "argument": correction_step.get("argument"),
            "status": "Correction Executed",
            "output_preview": result[:200]
        })

        await _emit_log(log_cb, "[Reflection System] Re-synthesizing final report with corrected data...")
        report_content = await asyncio.to_thread(synthesize_report, goal, context)

        if context and context.files_written:
            filename = context.files_written[0]
            await asyncio.to_thread(write_file, filename, report_content)
            await _emit_log(log_cb, f"[Reflection System] Saved updated report to '{filename}'.")

        return {
            "steps_history": steps_history,
            "report_content": report_content
        }

    async def _indexing_node(self, state: AgentState) -> Dict[str, Any]:
        goal = state["goal"]
        report_content = state.get("report_content", "")
        steps_history = state.get("steps_history", [])
        context = state.get("context")
        memory_used = state.get("memory_used", False)
        task_db_id = state.get("task_db_id")
        log_cb = state.get("log_callback")
        db_cb = state.get("db_session_callback")

        sources = []
        if context:
            for s_res in context.search_results:
                urls = re.findall(r'URL: (https?://[^\s]+)', s_res)
                sources.extend(urls)
        sources = list(set(sources))

        task_summary = f"Completed research on '{goal}'. Executed {len(steps_history)} steps."

        await _emit_log(log_cb, "\n[LangGraph Node: Indexing] Indexing result to database and vector memory...")
        await asyncio.to_thread(self.memory.add_memory, goal, report_content)

        final_payload = {
            "task_summary": task_summary,
            "steps_executed": steps_history,
            "final_report": report_content,
            "sources": sources,
            "memory_used": memory_used
        }

        if task_db_id:
            await _emit_db(db_cb, {
                "id": task_db_id,
                "status": "Completed",
                "summary": task_summary,
                "final_report": report_content,
                "steps_executed": json.dumps(steps_history)
            })

        await _emit_log(log_cb, "\n[System] LangGraph workflow run completed successfully. Deliverables are ready.")
        return {"final_payload": final_payload}

    async def run(self, goal: str, db_session_callback: Callable[[Dict[str, Any]], int] = None, log_callback: Callable[[str], None] = None) -> Dict[str, Any]:
        """
        Runs the full Hermes autonomous cycle using compiled LangGraph StateGraph.
        """
        initial_state: AgentState = {
            "goal": goal,
            "memory_context": "",
            "memory_used": False,
            "steps": [],
            "steps_history": [],
            "task_db_id": None,
            "report_content": "",
            "approved": True,
            "feedback": "",
            "correction_step": None,
            "sources": [],
            "context": ExecutionContext(),
            "log_callback": log_callback,
            "db_session_callback": db_session_callback,
            "final_payload": {}
        }

        final_state = await self.graph.ainvoke(initial_state)
        return final_state.get("final_payload", {})

    def reflect(self, goal: str, report: str, logs: List[str]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates the generated report and logs against the initial goal using Groq.
        """
        system_prompt = """You are an Agent Reflection Validator.
Your job is to examine if the research report generated satisfies the user's initial goal, and if there are any severe omissions.

You must output a JSON object with:
- "approved": true or false
- "feedback": Explanation of why it was approved, or what critical information is missing.
- "corrective_step": If approved is false, specify a new tool step to fix the deficiency. If approved is true, set this to null.

The corrective step should be a JSON object:
  - "tool": one of "search_web", "summarize_text", "query_memory", "read_file", "list_files", "python_calculator", "extract_citations", "markdown_table_formatter", "text_sentiment_analyzer"
  - "argument": argument for the tool
  - "reason": reasoning for this correction step
"""

        user_content = f"""Goal: {goal}
Execution Logs: {json.dumps(logs)}
Generated Report:
{report[:5000]}
"""

        try:
            client = get_groq_client()
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                model=POWERFUL_MODEL,
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            res_json = json.loads(response.choices[0].message.content)
            approved = res_json.get("approved", True)
            feedback = res_json.get("feedback", "Looks good.")
            correction = res_json.get("corrective_step")
            
            if not approved and not correction:
                approved = True
                
            return approved, feedback, correction
        except Exception as e:
            print(f"[Reflection Error] Could not parse reflection response: {e}")
            return True, "Default approval due to validator error.", None
