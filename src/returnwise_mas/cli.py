from __future__ import annotations

import argparse
import json
from pathlib import Path

from returnwise_mas.graph import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the ReturnWise local multi-agent system.")
    parser.add_argument("--input", default="sample_data/return_requests.json", help="Path to return requests JSON.")
    parser.add_argument("--policy", default="sample_data/return_policy.md", help="Path to local return policy markdown.")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated reports.")
    parser.add_argument("--log-dir", default="logs", help="Directory for JSONL observability logs.")
    parser.add_argument("--model", default="phi3", help="Local Ollama model name.")
    parser.add_argument("--no-llm", action="store_true", help="Run deterministic workflow without calling Ollama.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    final_state = run_pipeline(
        input_path=args.input,
        policy_path=args.policy,
        output_dir=args.output_dir,
        log_dir=args.log_dir,
        model=args.model,
        enable_llm=not args.no_llm,
    )

    summary = {
        "run_id": final_state["run_id"],
        "decisions": len(final_state.get("decisions", [])),
        "errors": final_state.get("errors", []),
        "output_dir": str(Path(args.output_dir).resolve()),
        "log_path": str(Path(final_state["log_path"]).resolve()),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

