from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AgentRunLogger:
    """Append-only JSONL logger for agent inputs, tool calls, and outputs."""

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, event_type: str, agent: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "agent": agent,
            "payload": payload,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def agent_start(self, agent: str, payload: dict[str, Any]) -> None:
        self.event("agent_start", agent, payload)

    def agent_end(self, agent: str, payload: dict[str, Any]) -> None:
        self.event("agent_end", agent, payload)

    def tool_call(self, agent: str, tool: str, payload: dict[str, Any]) -> None:
        self.event("tool_call", agent, {"tool": tool, **payload})

    def tool_result(self, agent: str, tool: str, payload: dict[str, Any]) -> None:
        self.event("tool_result", agent, {"tool": tool, **payload})

    def error(self, agent: str, message: str) -> None:
        self.event("error", agent, {"message": message})

