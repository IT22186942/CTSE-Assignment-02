from __future__ import annotations

from typing import Any, Literal, TypedDict


DecisionStatus = Literal["approve", "replace", "escalate", "reject"]
RiskLevel = Literal["low", "medium", "high"]


class ReturnRequest(TypedDict):
    request_id: str
    customer_id: str
    product_name: str
    category: str
    purchase_date: str
    request_date: str
    reason: str
    item_condition: str
    order_value: float
    previous_returns_90_days: int


class PolicyMatch(TypedDict):
    request_id: str
    window_days: int
    days_since_purchase: int
    eligible: bool
    policy_reason: str
    suggested_status: DecisionStatus


class RiskAssessment(TypedDict):
    request_id: str
    score: int
    level: RiskLevel
    flags: list[str]


class ReturnDecision(TypedDict):
    request_id: str
    status: DecisionStatus
    customer_message: str
    internal_reason: str
    next_action: str
    risk_level: RiskLevel


class AgentNote(TypedDict):
    agent: str
    note: str


class WorkflowState(TypedDict, total=False):
    run_id: str
    input_path: str
    policy_path: str
    output_dir: str
    log_path: str
    enable_llm: bool
    model: str
    raw_requests: list[dict[str, Any]]
    requests: list[ReturnRequest]
    policy_matches: list[PolicyMatch]
    risk_assessments: list[RiskAssessment]
    decisions: list[ReturnDecision]
    agent_notes: list[AgentNote]
    errors: list[str]

