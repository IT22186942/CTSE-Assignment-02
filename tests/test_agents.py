from __future__ import annotations

import json
import unittest
from pathlib import Path

from returnwise_mas.graph import run_pipeline


class AgentWorkflowTests(unittest.TestCase):
    def test_full_pipeline_generates_decisions_and_logs(self) -> None:
        output_dir = Path("outputs/test-run")
        log_dir = Path("logs/test-run")

        state = run_pipeline(
            input_path="sample_data/return_requests.json",
            policy_path="sample_data/return_policy.md",
            output_dir=str(output_dir),
            log_dir=str(log_dir),
            enable_llm=False,
        )

        self.assertEqual(len(state["decisions"]), 4)
        self.assertTrue((output_dir / "return_decisions.md").exists())
        self.assertTrue((output_dir / "return_decisions.json").exists())
        self.assertTrue(Path(state["log_path"]).exists())

        log_lines = Path(state["log_path"]).read_text(encoding="utf-8").splitlines()
        self.assertTrue(any('"agent": "Intake Agent"' in line for line in log_lines))
        self.assertTrue(any('"event_type": "tool_call"' in line for line in log_lines))

        decisions = json.loads((output_dir / "return_decisions.json").read_text(encoding="utf-8"))
        status_by_id = {decision["request_id"]: decision["status"] for decision in decisions}
        self.assertEqual(status_by_id["RET-1001"], "replace")
        self.assertEqual(status_by_id["RET-1003"], "escalate")


if __name__ == "__main__":
    unittest.main()
