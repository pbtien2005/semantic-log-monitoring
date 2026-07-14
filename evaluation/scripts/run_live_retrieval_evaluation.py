"""Run benchmark queries against live production retrieval paths."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.live_retrieval import LiveRetrievalOptions, run_live_retrieval_evaluation
from evaluation.paths import dataset_dir, results_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["direct", "api"], default="direct")
    parser.add_argument("--queries", type=Path, default=dataset_dir() / "groundtruth_queries.jsonl")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--experiment")
    parser.add_argument("--top-k", type=int, default=24)
    parser.add_argument("--template-k", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dataset")
    parser.add_argument("--level")
    parser.add_argument("--component")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--endpoint", default="/api/chat")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--milvus-uri")
    parser.add_argument("--embedding-model")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    experiment = args.experiment or (
        "production_direct_v1" if args.mode == "direct" else "production_api_v1"
    )
    output = args.output or results_dir() / f"retrieval_{experiment}.jsonl"
    options = LiveRetrievalOptions(
        queries_path=args.queries,
        output_path=output,
        mode=args.mode,
        experiment=experiment,
        top_k=args.top_k,
        template_k=args.template_k,
        limit=args.limit,
        dataset=args.dataset,
        level=args.level,
        component=args.component,
        base_url=args.base_url,
        endpoint=args.endpoint,
        timeout_seconds=args.timeout_seconds,
        **optional_dependency_args(args),
    )
    count = run_live_retrieval_evaluation(options)
    print(f"Wrote {count} live retrieval rows to {output}")
    print(f"Experiment: {experiment}")
    print(f"Mode: {args.mode}")


def optional_dependency_args(args: argparse.Namespace) -> dict[str, str]:
    values = {}
    if args.milvus_uri:
        values["milvus_uri"] = args.milvus_uri
    if args.embedding_model:
        values["embedding_model"] = args.embedding_model
    return values


if __name__ == "__main__":
    main()
