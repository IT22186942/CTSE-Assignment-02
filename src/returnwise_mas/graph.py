from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from returnwise_mas.agents import run_intake, run_policy, run_resolution, run_risk
from returnwise_mas.state import WorkflowState


class SequentialWorkflow:
    """Small fallback runner used when LangGraph is not installed."""

    def invoke(self, state: WorkflowState) -> WorkflowState:
        for node in (run_intake, run_policy, run_risk, run_resolution):
            state = node(state)
        return state


def build_workflow() -> object:
    """Build the ReturnWise workflow using LangGraph when available."""
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return SequentialWorkflow()

    workflow = StateGraph(WorkflowState)
    workflow.add_node("intake", run_intake)
    workflow.add_node("policy", run_policy)
    workflow.add_node("risk", run_risk)
    workflow.add_node("resolution", run_resolution)
    workflow.set_entry_point("intake")
    workflow.add_edge("intake", "policy")
    workflow.add_edge("policy", "risk")
    workflow.add_edge("risk", "resolution")
    workflow.add_edge("resolution", END)
    return workflow.compile()


def run_pipeline(
    input_path: str,
    policy_path: str,
    output_dir: str = "outputs",
    log_dir: str = "logs",
    model: str = "phi3",
    enable_llm: bool = True,
) -> WorkflowState:
    """Run the complete multi-agent return triage workflow."""
    run_id = f"returnwise-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    state: WorkflowState = {
        "run_id": run_id,
        "input_path": input_path,
        "policy_path": policy_path,
        "output_dir": output_dir,
        "log_path": str(Path(log_dir) / f"{run_id}.jsonl"),
        "model": model,
        "enable_llm": enable_llm,
        "agent_notes": [],
        "errors": [],
    }
    workflow = build_workflow()
    return workflow.invoke(state)  # type: ignore[attr-defined]

