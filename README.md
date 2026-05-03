# ReturnWise MAS

ReturnWise MAS is a locally hosted multi-agent system for e-commerce return request triage. It uses a team of four agents to read return requests, match them against a local policy file, score operational risk, and write clear resolution reports.

The project is designed for the SE4010 CTSE Assignment 2 brief:

- 4 distinct agents
- Custom Python tools with type hints and docstrings
- Shared global state between agents
- JSONL observability logs
- Local Ollama SLM integration
- LangGraph orchestration when installed
- Automated evaluation tests

## Agents

1. **Intake Agent** normalizes and validates return requests from a local JSON file.
2. **Policy Agent** checks the return policy and assigns a policy outcome.
3. **Risk Agent** scores fraud, abuse, and operational risk.
4. **Resolution Agent** creates final customer-service decisions and writes reports.

## Local Setup

Install Python 3.10 or later, then install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Install and start Ollama, then pull a small local model:

```bash
ollama pull phi3
ollama serve
```

Run the system:

```bash
python -m returnwise_mas --input sample_data/return_requests.json --policy sample_data/return_policy.md
```

For test runs without calling Ollama:

```bash
python -m returnwise_mas --input sample_data/return_requests.json --policy sample_data/return_policy.md --no-llm
```

## Outputs

Each run creates:

- `outputs/return_decisions.md`
- `outputs/return_decisions.json`
- `logs/<run-id>.jsonl`

The JSONL log records agent inputs, tool calls, outputs, and errors.

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The evaluation harness is in `tests/evaluation_harness.py`. It runs the full workflow with deterministic local settings and checks policy accuracy, risk bounds, output structure, and security expectations.

## Report

The technical report is available at `docs/technical_report.md`. A short demo video guide is available at `docs/demo_script.md`.
