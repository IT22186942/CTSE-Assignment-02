from __future__ import annotations

import json
import os
from pathlib import Path

from returnwise_mas.graph import run_pipeline


def run_evaluation() -> dict[str, object]:
    """Run a deterministic group-level evaluation of the full MAS workflow."""
    state = run_pipeline(
        input_path="sample_data/return_requests.json",
        policy_path="sample_data/return_policy.md",
        output_dir="outputs/evaluation",
        log_dir="logs/evaluation",
        enable_llm=False,
    )
    decisions = state.get("decisions", [])
    failures: list[str] = []

    if len(decisions) != 4:
        failures.append("Expected four final decisions.")

    for decision in decisions:
        if decision["status"] not in {"approve", "replace", "escalate", "reject"}:
            failures.append(f"Invalid status for {decision['request_id']}.")
        if not decision["customer_message"].strip():
            failures.append(f"Missing customer message for {decision['request_id']}.")
        if "OpenAI" in decision["customer_message"] or "Anthropic" in decision["customer_message"]:
            failures.append(f"Paid API reference leaked into {decision['request_id']}.")

    risks = state.get("risk_assessments", [])
    for risk in risks:
        if not 0 <= risk["score"] <= 100:
            failures.append(f"Risk score out of range for {risk['request_id']}.")

    forbidden_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    present_forbidden_keys = [key for key in forbidden_keys if os.environ.get(key)]
    if present_forbidden_keys:
        failures.append("Paid cloud API keys should not be required or used.")

    report = {
        "passed": not failures,
        "failures": failures,
        "decision_count": len(decisions),
        "log_path": state.get("log_path"),
        "output_path": str(Path("outputs/evaluation/return_decisions.json")),
    }
    Path("outputs/evaluation").mkdir(parents=True, exist_ok=True)
    Path("outputs/evaluation/evaluation_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    result = run_evaluation()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)

