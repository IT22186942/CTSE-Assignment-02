# Demo Video Script

Target length: 4 to 5 minutes.

## 0:00 - 0:30: Introduce the Problem

Explain that ReturnWise MAS is a local multi-agent system for e-commerce return request triage. It reviews return requests, checks policy, scores risk, and writes final support decisions.

## 0:30 - 1:10: Show the Architecture

Open `docs/technical_report.md` and briefly show the workflow diagram. Mention the four agents:

- Intake Agent
- Policy Agent
- Risk Agent
- Resolution Agent

Explain that the system uses shared `WorkflowState` and JSONL logs.

## 1:10 - 1:50: Show Input Data and Policy

Open:

- `sample_data/return_requests.json`
- `sample_data/return_policy.md`

Point out that the data and policy are local files. Mention that no paid cloud API key is needed.

## 1:50 - 2:40: Run the MAS

Run:

```bash
python -m returnwise_mas --input sample_data/return_requests.json --policy sample_data/return_policy.md --no-llm
```

For the Ollama demo, run without `--no-llm` after starting Ollama:

```bash
python -m returnwise_mas --input sample_data/return_requests.json --policy sample_data/return_policy.md --model phi3
```

Explain that `--no-llm` is useful for deterministic testing, while the normal mode calls the local Ollama model for short audit notes.

## 2:40 - 3:25: Show Outputs

Open:

- `outputs/return_decisions.md`
- `outputs/return_decisions.json`

Show one approved or replacement request and one escalated request. Explain how policy and risk are combined.

## 3:25 - 4:10: Show Observability

Open the latest file in `logs/`. Show entries for:

- `agent_start`
- `tool_call`
- `tool_result`
- `agent_end`

Explain that this proves the agents used tools and passed state through the workflow.

## 4:10 - 4:50: Run Evaluation

Run:

```bash
python tests/evaluation_harness.py
python -m unittest discover -s tests -p "test_*.py"
```

Explain that the tests check output structure, policy behavior, risk score bounds, and local-only constraints.

## 4:50 - 5:00: Close

End by saying that the project meets the assignment requirements: four agents, custom tools, local Ollama integration, state management, observability, and evaluation.
