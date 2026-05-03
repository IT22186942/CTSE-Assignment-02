from __future__ import annotations

import unittest

from returnwise_mas.tools import (
    calculate_risk_score,
    match_policy,
    normalize_return_request,
    read_policy_text,
)


class ToolTests(unittest.TestCase):
    def test_normalize_return_request_rejects_missing_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing required fields"):
            normalize_return_request({"request_id": "RET-X"})

    def test_policy_matches_defective_electronics(self) -> None:
        request = normalize_return_request(
            {
                "request_id": "RET-1",
                "customer_id": "CUS-1",
                "product_name": "Headphones",
                "category": "electronics",
                "purchase_date": "2026-04-01",
                "request_date": "2026-04-20",
                "reason": "Stopped working",
                "item_condition": "opened",
                "order_value": 150,
                "previous_returns_90_days": 0,
            }
        )
        policy = read_policy_text("sample_data/return_policy.md")
        match = match_policy(request, policy)
        self.assertTrue(match["eligible"])
        self.assertEqual(match["window_days"], 60)
        self.assertEqual(match["suggested_status"], "replace")

    def test_risk_score_escalates_high_value_used_repeat_return(self) -> None:
        request = normalize_return_request(
            {
                "request_id": "RET-2",
                "customer_id": "CUS-2",
                "product_name": "Camera",
                "category": "electronics",
                "purchase_date": "2026-01-01",
                "request_date": "2026-05-01",
                "reason": "Changed my mind",
                "item_condition": "used",
                "order_value": 300,
                "previous_returns_90_days": 5,
            }
        )
        policy = {
            "request_id": "RET-2",
            "window_days": 30,
            "days_since_purchase": 120,
            "eligible": False,
            "policy_reason": "Outside window.",
            "suggested_status": "escalate",
        }
        risk = calculate_risk_score(request, policy)
        self.assertEqual(risk["level"], "high")
        self.assertLessEqual(risk["score"], 100)
        self.assertGreaterEqual(risk["score"], 0)
        self.assertIn("high recent return volume", risk["flags"])


if __name__ == "__main__":
    unittest.main()
