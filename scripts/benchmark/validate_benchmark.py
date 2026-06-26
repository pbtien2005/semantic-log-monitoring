"""Validate silver benchmark artifacts without mixing datasets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.benchmark.query_bank import QUERY_BANK
from src.core.io_utils import benchmark_dir, read_jsonl
from src.core.schema import (
    DATASETS,
    SchemaValidationError,
    validate_dataset,
    validate_log_record,
    validate_pair_record,
    validate_qrel_record,
)


def load_required(path: Path, name: str) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {name}: {path}")
    return list(read_jsonl(path))


def query_ids_for(dataset: str) -> set[str]:
    return {f"{dataset}_q{index:03d}" for index, _ in enumerate(QUERY_BANK[dataset], start=1)}


def validate_dataset_benchmark(dataset: str, root: Path) -> dict[str, Any]:
    dataset = validate_dataset(dataset)
    bench = benchmark_dir(dataset, root)
    logs = load_required(bench / "logs.jsonl", "logs.jsonl")
    qrels = load_required(bench / "qrels_silver.jsonl", "qrels_silver.jsonl")
    pairs = load_required(bench / "pairs.jsonl", "pairs.jsonl")
    splits = {
        "train": load_required(bench / "splits" / "train.jsonl", "splits/train.jsonl"),
        "dev": load_required(bench / "splits" / "dev.jsonl", "splits/dev.jsonl"),
        "test": load_required(bench / "splits" / "test.jsonl", "splits/test.jsonl"),
    }

    log_ids: set[str] = set()
    for log in logs:
        validate_log_record(log)
        if log["dataset"] != dataset:
            raise SchemaValidationError(f"Mixed dataset in logs: {log['dataset']}")
        if log["log_id"] in log_ids:
            raise SchemaValidationError(f"Duplicate log_id: {log['log_id']}")
        log_ids.add(str(log["log_id"]))

    expected_query_ids = query_ids_for(dataset)
    seen_qrels: set[str] = set()
    no_positive: list[str] = []
    needs_review: list[str] = []
    for qrel in qrels:
        validate_qrel_record(qrel)
        query_id = str(qrel["query_id"])
        if qrel["label_source"] != "silver_auto_v2":
            raise SchemaValidationError(f"{query_id} label_source must be silver_auto_v2")
        if query_id in seen_qrels:
            raise SchemaValidationError(f"Duplicate qrel query_id: {query_id}")
        if query_id not in expected_query_ids:
            raise SchemaValidationError(f"Unknown qrel query_id: {query_id}")
        seen_qrels.add(query_id)
        positives = set(qrel["positive_log_ids"])
        negatives = set(qrel["hard_negative_log_ids"])
        if positives & negatives:
            raise SchemaValidationError(f"{query_id} has positive/negative overlap")
        for log_id in positives | negatives:
            if log_id not in log_ids:
                raise SchemaValidationError(f"{query_id} references unknown log_id: {log_id}")
        if not positives:
            no_positive.append(query_id)
        if qrel["needs_review"]:
            needs_review.append(query_id)

    pair_query_ids: set[str] = set()
    for pair in pairs:
        validate_pair_record(pair)
        if pair["dataset"] != dataset:
            raise SchemaValidationError(f"Mixed dataset in pairs: {pair['dataset']}")
        if pair["query_id"] not in expected_query_ids:
            raise SchemaValidationError(f"Unknown pair query_id: {pair['query_id']}")
        if pair["positive_log_id"] not in log_ids or pair["negative_log_id"] not in log_ids:
            raise SchemaValidationError(f"Pair references unknown log_id: {pair['query_id']}")
        if pair["positive_log_id"] == pair["negative_log_id"]:
            raise SchemaValidationError(f"Pair has same positive/negative log: {pair['query_id']}")
        pair_query_ids.add(str(pair["query_id"]))

    split_query_ids: dict[str, set[str]] = {}
    split_pair_total = 0
    for split_name, records in splits.items():
        ids = {str(record["query_id"]) for record in records}
        split_query_ids[split_name] = ids
        split_pair_total += len(records)
        for record in records:
            validate_pair_record(record)
    if split_pair_total != len(pairs):
        raise SchemaValidationError("Split pair counts do not sum to pairs.jsonl count")
    if split_query_ids["train"] & split_query_ids["dev"]:
        raise SchemaValidationError("train/dev query_id overlap")
    if split_query_ids["train"] & split_query_ids["test"]:
        raise SchemaValidationError("train/test query_id overlap")
    if split_query_ids["dev"] & split_query_ids["test"]:
        raise SchemaValidationError("dev/test query_id overlap")

    return {
        "logs": len(logs),
        "queries": len(qrels),
        "pairs": len(pairs),
        "train": len(splits["train"]),
        "dev": len(splits["dev"]),
        "test": len(splits["test"]),
        "needs_review": len(needs_review),
        "no_positive": len(no_positive),
        "warnings": {
            "no_positive": no_positive,
            "needs_review": needs_review,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    failed = False
    for index, dataset in enumerate(datasets):
        if index:
            print()
        try:
            result = validate_dataset_benchmark(dataset, args.root)
            print(f"Dataset: {dataset}")
            print("Validation: PASS")
            print(
                "Counts: "
                + ", ".join(
                    f"{key}={result[key]}"
                    for key in ("logs", "queries", "pairs", "train", "dev", "test", "needs_review", "no_positive")
                )
            )
            if result["warnings"]["no_positive"]:
                print("Warning no positive: " + ", ".join(result["warnings"]["no_positive"]))
            if result["warnings"]["needs_review"]:
                print("Warning needs_review: " + ", ".join(result["warnings"]["needs_review"][:20]))
                if len(result["warnings"]["needs_review"]) > 20:
                    print(f"Warning needs_review remaining: {len(result['warnings']['needs_review']) - 20}")
        except Exception as exc:
            failed = True
            print(f"Dataset: {dataset}")
            print("Validation: FAIL")
            print(str(exc))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
