from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from returnwise_mas.observability import AgentRunLogger
from returnwise_mas.ollama_client import OllamaClient
from returnwise_mas.prompts import INTAKE_PROMPT, POLICY_PROMPT, RESOLUTION_PROMPT, RISK_PROMPT
from returnwise_mas.state import PolicyMatch, ReturnRequest, RiskAssessment, WorkflowState
from returnwise_mas.tools import (
    build_decision,
    calculate_risk_score,
    load_return_requests,
    match_policy,
    normalize_return_request,
    read_policy_text,
    write_decision_outputs,
)


@dataclass(frozen=True)
class AgentContext:
    logger: AgentRunLogger
    llm: OllamaClient
    enable_llm: bool


class BaseAgent:
    name: str
    system_prompt: str

    def add_note(self, state: WorkflowState, note: str) -> None:
        state.setdefault("agent_notes", []).append({"agent": self.name, "note": note})

    def ask_llm_for_note(self, context: AgentContext, task_prompt: str) -> str | None:
        if not context.enable_llm:
            return None
        try:
            return context.llm.generate(self.system_prompt, task_prompt)
        except RuntimeError as exc:
            context.logger.error(self.name, str(exc))
            return None


class IntakeAgent(BaseAgent):
    name = "Intake Agent"
    system_prompt = INTAKE_PROMPT

    def run(self, state: WorkflowState, context: AgentContext) -> WorkflowState:
        context.logger.agent_start(self.name, {"input_path": state["input_path"]})
        context.logger.tool_call(self.name, "load_return_requests", {"path": state["input_path"]})
        raw_requests = load_return_requests(state["input_path"])
        context.logger.tool_result(self.name, "load_return_requests", {"count": len(raw_requests)})

        normalized: list[ReturnRequest] = []
        errors: list[str] = []
        for index, raw_request in enumerate(raw_requests, start=1):
            context.logger.tool_call(self.name, "normalize_return_request", {"index": index})
            try:
                normalized.append(normalize_return_request(raw_request))
                context.logger.tool_result(self.name, "normalize_return_request", {"index": index, "valid": True})
            except ValueError as exc:
                message = f"Request {index}: {exc}"
                errors.append(message)
                context.logger.tool_result(
                    self.name,
                    "normalize_return_request",
                    {"index": index, "valid": False, "error": message},
                )

        state["raw_requests"] = raw_requests
        state["requests"] = normalized
        state.setdefault("errors", []).extend(errors)
        self.add_note(state, f"Normalized {len(normalized)} request(s); {len(errors)} invalid request(s).")
        llm_note = self.ask_llm_for_note(
            context,
            f"Summarize the intake quality in one sentence. Valid requests: {len(normalized)}. Errors: {errors}",
        )
        if llm_note:
            self.add_note(state, llm_note)
        context.logger.agent_end(self.name, {"valid_requests": len(normalized), "errors": errors})
        return state


class PolicyAgent(BaseAgent):
    name = "Policy Agent"
    system_prompt = POLICY_PROMPT

    def run(self, state: WorkflowState, context: AgentContext) -> WorkflowState:
        context.logger.agent_start(self.name, {"request_count": len(state.get("requests", []))})
        context.logger.tool_call(self.name, "read_policy_text", {"path": state["policy_path"]})
        policy_text = read_policy_text(state["policy_path"])
        context.logger.tool_result(self.name, "read_policy_text", {"characters": len(policy_text)})

        matches: list[PolicyMatch] = []
        for request in state.get("requests", []):
            context.logger.tool_call(self.name, "match_policy", {"request_id": request["request_id"]})
            match = match_policy(request, policy_text)
            matches.append(match)
            context.logger.tool_result(self.name, "match_policy", match)

        state["policy_matches"] = matches
        self.add_note(state, f"Matched {len(matches)} request(s) against the local policy.")
        llm_note = self.ask_llm_for_note(
            context,
            "Give a concise audit note for these policy matches: " + str(matches),
        )
        if llm_note:
            self.add_note(state, llm_note)
        context.logger.agent_end(self.name, {"matches": matches})
        return state


class RiskAgent(BaseAgent):
    name = "Risk Agent"
    system_prompt = RISK_PROMPT

    def run(self, state: WorkflowState, context: AgentContext) -> WorkflowState:
        requests_by_id = {request["request_id"]: request for request in state.get("requests", [])}
        context.logger.agent_start(self.name, {"request_count": len(requests_by_id)})

        assessments: list[RiskAssessment] = []
        for policy_match in state.get("policy_matches", []):
            request = requests_by_id[policy_match["request_id"]]
            context.logger.tool_call(self.name, "calculate_risk_score", {"request_id": request["request_id"]})
            assessment = calculate_risk_score(request, policy_match)
            assessments.append(assessment)
            context.logger.tool_result(self.name, "calculate_risk_score", assessment)

        state["risk_assessments"] = assessments
        self.add_note(state, f"Calculated risk for {len(assessments)} request(s).")
        llm_note = self.ask_llm_for_note(
            context,
            "Write one internal risk summary sentence for these assessments: " + str(assessments),
        )
        if llm_note:
            self.add_note(state, llm_note)
        context.logger.agent_end(self.name, {"assessments": assessments})
        return state


class ResolutionAgent(BaseAgent):
    name = "Resolution Agent"
    system_prompt = RESOLUTION_PROMPT

    def run(self, state: WorkflowState, context: AgentContext) -> WorkflowState:
        context.logger.agent_start(self.name, {"output_dir": state["output_dir"]})
        requests_by_id = {request["request_id"]: request for request in state.get("requests", [])}
        risks_by_id = {risk["request_id"]: risk for risk in state.get("risk_assessments", [])}

        decisions = []
        for policy_match in state.get("policy_matches", []):
            request = requests_by_id[policy_match["request_id"]]
            risk = risks_by_id[policy_match["request_id"]]
            context.logger.tool_call(self.name, "build_decision", {"request_id": request["request_id"]})
            decision = build_decision(request, policy_match, risk)
            decisions.append(decision)
            context.logger.tool_result(self.name, "build_decision", decision)

        context.logger.tool_call(self.name, "write_decision_outputs", {"output_dir": state["output_dir"]})
        output_paths = write_decision_outputs(state["output_dir"], decisions)
        context.logger.tool_result(self.name, "write_decision_outputs", output_paths)

        state["decisions"] = decisions
        self.add_note(state, f"Wrote {len(decisions)} decision(s) to {output_paths['markdown']}.")
        llm_note = self.ask_llm_for_note(
            context,
            "Check whether these customer messages are polite and concise. Reply in one sentence: " + str(decisions),
        )
        if llm_note:
            self.add_note(state, llm_note)
        context.logger.agent_end(self.name, {"decisions": decisions, "outputs": output_paths})
        return state


def build_agent_context(state: WorkflowState) -> AgentContext:
    return AgentContext(
        logger=AgentRunLogger(state["log_path"]),
        llm=OllamaClient(model=state.get("model", "phi3")),
        enable_llm=state.get("enable_llm", True),
    )


def run_intake(state: WorkflowState) -> WorkflowState:
    return IntakeAgent().run(state, build_agent_context(state))


def run_policy(state: WorkflowState) -> WorkflowState:
    return PolicyAgent().run(state, build_agent_context(state))


def run_risk(state: WorkflowState) -> WorkflowState:
    return RiskAgent().run(state, build_agent_context(state))


def run_resolution(state: WorkflowState) -> WorkflowState:
    return ResolutionAgent().run(state, build_agent_context(state))


AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "intake": IntakeAgent,
    "policy": PolicyAgent,
    "risk": RiskAgent,
    "resolution": ResolutionAgent,
}


def agent_prompt_catalog() -> dict[str, dict[str, Any]]:
    """Return prompt and tool ownership details for documentation and audits."""
    return {
        "intake": {
            "agent": IntakeAgent.name,
            "system_prompt": IntakeAgent.system_prompt.strip(),
            "primary_tools": ["load_return_requests", "normalize_return_request"],
        },
        "policy": {
            "agent": PolicyAgent.name,
            "system_prompt": PolicyAgent.system_prompt.strip(),
            "primary_tools": ["read_policy_text", "match_policy"],
        },
        "risk": {
            "agent": RiskAgent.name,
            "system_prompt": RiskAgent.system_prompt.strip(),
            "primary_tools": ["calculate_risk_score"],
        },
        "resolution": {
            "agent": ResolutionAgent.name,
            "system_prompt": ResolutionAgent.system_prompt.strip(),
            "primary_tools": ["build_decision", "write_decision_outputs"],
        },
    }

