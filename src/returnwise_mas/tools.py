from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from returnwise_mas.state import PolicyMatch, ReturnDecision, ReturnRequest, RiskAssessment


REQUIRED_REQUEST_FIELDS = {
    "request_id",
    "customer_id",
    "product_name",
    "category",
    "purchase_date",
    "request_date",
    "reason",
    "item_condition",
    "order_value",
    "previous_returns_90_days",
}


def load_return_requests(input_path: str | Path) -> list[dict[str, Any]]:
    """Read return requests from a local JSON file.

    Args:
        input_path: Path to a JSON file containing a list of request objects.

    Returns:
        Raw request dictionaries exactly as read from disk.

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If the JSON root is not a list of objects.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Return request file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("Return request JSON must contain a list of objects.")
    return data


def normalize_return_request(raw_request: dict[str, Any]) -> ReturnRequest:
    """Validate and normalize one raw return request.

    Args:
        raw_request: Request object from the input JSON file.

    Returns:
        A normalized return request with expected value types.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    missing = sorted(REQUIRED_REQUEST_FIELDS - set(raw_request))
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    try:
        normalized: ReturnRequest = {
            "request_id": str(raw_request["request_id"]).strip(),
            "customer_id": str(raw_request["customer_id"]).strip(),
            "product_name": str(raw_request["product_name"]).strip(),
            "category": str(raw_request["category"]).strip().lower(),
            "purchase_date": str(raw_request["purchase_date"]).strip(),
            "request_date": str(raw_request["request_date"]).strip(),
            "reason": str(raw_request["reason"]).strip(),
            "item_condition": str(raw_request["item_condition"]).strip().lower(),
            "order_value": float(raw_request["order_value"]),
            "previous_returns_90_days": int(raw_request["previous_returns_90_days"]),
        }
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid request field type: {exc}") from exc

    if not normalized["request_id"] or not normalized["reason"]:
        raise ValueError("Request id and reason cannot be empty.")
    if normalized["order_value"] < 0:
        raise ValueError("Order value cannot be negative.")
    if normalized["previous_returns_90_days"] < 0:
        raise ValueError("Previous returns cannot be negative.")

    _parse_iso_date(normalized["purchase_date"])
    _parse_iso_date(normalized["request_date"])
    return normalized


def read_policy_text(policy_path: str | Path) -> str:
    """Read the local return policy markdown file.

    Args:
        policy_path: Path to a local markdown policy file.

    Returns:
        Policy text used by the Policy Agent.

    Raises:
        FileNotFoundError: If the policy file cannot be found.
        ValueError: If the policy file is empty.
    """
    path = Path(policy_path)
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("Policy file is empty.")
    return text


def match_policy(request: ReturnRequest, policy_text: str) -> PolicyMatch:
    """Match a return request against the local policy rules.

    The policy text is accepted as an argument so the tool is auditable and
    does not silently rely on hidden constants.

    Args:
        request: Normalized return request.
        policy_text: Local markdown policy used for the decision.

    Returns:
        A policy match containing eligibility, return window, and reason.
    """
    if "Return Policy" not in policy_text:
        raise ValueError("Policy text does not look like the expected return policy.")

    days_since_purchase = (_parse_iso_date(request["request_date"]) - _parse_iso_date(request["purchase_date"])).days
    reason = request["reason"].lower()
    category = request["category"]
    condition = request["item_condition"]

    window_days = 30
    suggested_status = "approve"
    policy_reason = "Standard return window applies."

    if "broken" in reason or "damaged" in reason or condition == "damaged":
        window_days = 14
        suggested_status = "replace"
        policy_reason = "Damaged-on-arrival policy applies."
    elif "defect" in reason or "stopped working" in reason or "fault" in reason:
        window_days = 60
        suggested_status = "replace"
        policy_reason = "Defective item policy applies."
    elif category == "apparel":
        window_days = 45
        suggested_status = "approve"
        policy_reason = "Apparel policy applies for unused items."
    elif category == "electronics" and condition == "used":
        window_days = 30
        suggested_status = "escalate"
        policy_reason = "Used electronics returned for preference reasons require review."

    eligible = days_since_purchase <= window_days
    if not eligible:
        suggested_status = "reject" if suggested_status != "escalate" else "escalate"
        policy_reason = f"{policy_reason} Request is outside the {window_days}-day window."
    elif category == "apparel" and condition not in {"unused", "new"}:
        eligible = False
        suggested_status = "reject"
        policy_reason = "Apparel must be unused and resaleable."

    return {
        "request_id": request["request_id"],
        "window_days": window_days,
        "days_since_purchase": days_since_purchase,
        "eligible": eligible,
        "policy_reason": policy_reason,
        "suggested_status": suggested_status,
    }


def calculate_risk_score(request: ReturnRequest, policy_match: PolicyMatch) -> RiskAssessment:
    """Calculate an operational risk score for a return request.

    Args:
        request: Normalized return request.
        policy_match: Policy result for the same request.

    Returns:
        Risk score, level, and human-readable internal flags.
    """
    score = 0
    flags: list[str] = []

    if request["previous_returns_90_days"] >= 4:
        score += 35
        flags.append("high recent return volume")
    elif request["previous_returns_90_days"] >= 2:
        score += 15
        flags.append("moderate recent return volume")

    if request["order_value"] >= 250:
        score += 25
        flags.append("high value item")
    elif request["order_value"] >= 100:
        score += 10
        flags.append("medium value item")

    if request["item_condition"] == "used":
        score += 20
        flags.append("item has been used")
    elif request["item_condition"] == "damaged":
        score += 10
        flags.append("damage evidence may be required")

    if not policy_match["eligible"]:
        score += 25
        flags.append("outside policy eligibility")

    score = min(score, 100)
    if score >= 60:
        level = "high"
    elif score >= 25:
        level = "medium"
    else:
        level = "low"

    return {
        "request_id": request["request_id"],
        "score": score,
        "level": level,
        "flags": flags or ["no major risk signals"],
    }


def build_decision(
    request: ReturnRequest,
    policy_match: PolicyMatch,
    risk_assessment: RiskAssessment,
) -> ReturnDecision:
    """Create a final support decision from policy and risk outputs.

    Args:
        request: Normalized return request.
        policy_match: Policy match for the request.
        risk_assessment: Risk score for the request.

    Returns:
        A final decision object suitable for JSON and markdown output.
    """
    status = policy_match["suggested_status"]
    if risk_assessment["level"] == "high":
        status = "escalate"
    elif not policy_match["eligible"]:
        status = "reject"

    if status == "approve":
        customer_message = (
            f"Your return request for {request['product_name']} is eligible. "
            "We can approve the return once the item is received and checked."
        )
        next_action = "Send return label and await warehouse inspection."
    elif status == "replace":
        customer_message = (
            f"Your request for {request['product_name']} is eligible for replacement review. "
            "Please share any photos or details needed by support."
        )
        next_action = "Offer replacement or refund after evidence check."
    elif status == "reject":
        customer_message = (
            f"We reviewed your request for {request['product_name']}, but it is outside the current return policy."
        )
        next_action = "Close request with policy explanation."
    else:
        customer_message = (
            f"Your request for {request['product_name']} needs a manual support review before a final answer."
        )
        next_action = "Escalate to senior support with policy and risk notes."

    internal_reason = f"{policy_match['policy_reason']} Risk: {risk_assessment['level']} ({risk_assessment['score']}/100)."
    return {
        "request_id": request["request_id"],
        "status": status,
        "customer_message": customer_message,
        "internal_reason": internal_reason,
        "next_action": next_action,
        "risk_level": risk_assessment["level"],
    }


def write_decision_outputs(output_dir: str | Path, decisions: list[ReturnDecision]) -> dict[str, str]:
    """Write final decisions to markdown and JSON files.

    Args:
        output_dir: Directory where outputs should be created.
        decisions: Final decision objects produced by the Resolution Agent.

    Returns:
        Mapping with paths to the generated markdown and JSON files.
    """
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "return_decisions.json"
    markdown_path = path / "return_decisions.md"

    json_path.write_text(json.dumps(decisions, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# ReturnWise Decision Report",
        "",
        f"Total requests reviewed: {len(decisions)}",
        "",
    ]
    for decision in decisions:
        lines.extend(
            [
                f"## {decision['request_id']} - {decision['status'].title()}",
                "",
                f"**Risk level:** {decision['risk_level']}",
                "",
                f"**Customer message:** {decision['customer_message']}",
                "",
                f"**Internal reason:** {decision['internal_reason']}",
                "",
                f"**Next action:** {decision['next_action']}",
                "",
            ]
        )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Expected ISO date YYYY-MM-DD, got {value!r}") from exc

