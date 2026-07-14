"""Calculate retrieval and RCA metrics from an evaluation result JSONL file."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.io import read_jsonl, write_json
from evaluation.metrics import calculate_retrieval_metrics
from evaluation.paths import dataset_dir, reports_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--queries", type=Path, default=dataset_dir() / "groundtruth_queries.jsonl")
    parser.add_argument("--incidents", type=Path, default=dataset_dir() / "incidents.jsonl")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--k", type=int, action="append", dest="ks")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or reports_dir() / f"{args.results.stem}_metrics.json"
    metrics = write_retrieval_metrics_report(
        results_path=args.results,
        queries_path=args.queries,
        incidents_path=args.incidents,
        output_path=output,
        ks=tuple(args.ks or (5, 10, 24)),
    )
    print(f"Wrote retrieval metrics for {metrics['experiment']} to {output}")
    print(f"Queries: {metrics['query_count']}")
    print(f"Hit@10: {metrics['retrieval'].get('hit@10', metrics['retrieval'].get('hit@5'))}")
    print(f"nDCG@10: {metrics['retrieval'].get('ndcg@10', metrics['retrieval'].get('ndcg@5'))}")
    print(
        "RootCauseHit@10: "
        f"{metrics['rca'].get('root_cause_hit@10', metrics['rca'].get('root_cause_hit@5'))}"
    )


def write_retrieval_metrics_report(
    *,
    results_path: Path,
    queries_path: Path,
    incidents_path: Path,
    output_path: Path,
    ks: tuple[int, ...] = (5, 10, 24),
) -> dict[str, object]:
    metrics = calculate_retrieval_metrics(
        results=list(read_jsonl(results_path)),
        queries=list(read_jsonl(queries_path)),
        incidents=list(read_jsonl(incidents_path)),
        ks=ks,
    )
    write_json(output_path, metrics)
    return metrics


if __name__ == "__main__":
    main()
