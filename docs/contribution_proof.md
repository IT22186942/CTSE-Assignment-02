# Individual Contribution Proof

This submission was completed by a single contributor.

| Student                | Agent developed                                          | Tool implemented                                                                                                                                           | Test contribution                                                                                                        | Challenges faced                                                                                   |
| ---------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Abishek S (IT22186942) | Intake Agent, Policy Agent, Risk Agent, Resolution Agent | `load_return_requests`, `normalize_return_request`, `read_policy_text`, `match_policy`, `calculate_risk_score`, `build_decision`, `write_decision_outputs` | Missing field, validation, policy, risk, and end-to-end output tests in `tests/test_tools.py` and `tests/test_agents.py` | Completing the full pipeline alone while keeping the workflow deterministic, local, and auditable. |

## Evidence in the Repository

- Agent prompts: `src/returnwise_mas/prompts.py`
- Agent implementations: `src/returnwise_mas/agents.py`
- Custom tools: `src/returnwise_mas/tools.py`
- Shared state: `src/returnwise_mas/state.py`
- Observability logging: `src/returnwise_mas/observability.py`
- Evaluation harness: `tests/evaluation_harness.py`
