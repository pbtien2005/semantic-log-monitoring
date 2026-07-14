"""Run a retrieval experiment over generated evaluation logs."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.paths import dataset_dir, results_dir
from evaluation.retrieval_runner import SUPPORTED_EXPERIMENTS, RetrievalRunOptions, run_retrieval_evaluation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", choices=sorted(SUPPORTED_EXPERIMENTS), required=True)
    parser.add_argument("--logs", type=Path, default=dataset_dir() / "logs.jsonl")
    parser.add_argument("--queries", type=Path, default=dataset_dir() / "groundtruth_queries.jsonl")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top-k", type=int, default=24)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or results_dir() / f"retrieval_{args.experiment}.jsonl"
    count = run_retrieval_evaluation(
        RetrievalRunOptions(
            logs_path=args.logs,
            queries_path=args.queries,
            output_path=output,
            experiment=args.experiment,
            top_k=args.top_k,
            limit=args.limit,
        )
    )
    print(f"Wrote {count} retrieval result rows to {output}")


if __name__ == "__main__":
    main()
