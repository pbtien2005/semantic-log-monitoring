"""Prepare a focused manual-review CSV for qrels v2 labels.

This script samples risky review candidates only. It does not edit labels,
create clean qrels, create pairs/splits, or run benchmarks.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.io_utils import benchmark_dir, ensure_dir, read_jsonl
from src.schema import DATASETS, validate_dataset


REVIEW_LABELS = {"positive", "hard_negative", "uncertain", "unsupported", "ignore"}
OUTPUT_COLUMNS = [
    "dataset",
    "query_id",
    "query",
    "query_level",
    "category",
    "intent",
    "log_id",
    "message",
    "raw_log",
    "predicted_label",
    "review_label",
    "reason",
    "needs_review",
    "review_priority",
    "review_note",
]


def read_review_candidates(dataset: str, root: Path) -> list[dict[str, str]]:
    path = benchmark_dir(dataset, root) / "review" / "review_candidates_v2.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing review candidates v2: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_qrels(dataset: str, root: Path) -> dict[str, dict[str, Any]]:
    path = benchmark_dir(dataset, root) / "qrels_v2.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Missing qrels v2: {path}")
    return {str(row["query_id"]): row for row in read_jsonl(path)}


def query_stats(rows: list[dict[str, str]]) -> dict[str, Counter[str]]:
    stats: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        stats[row["query_id"]][row["predicted_label"]] += 1
    return stats


def is_high_priority(row: dict[str, str], qrel: dict[str, Any], stats: Counter[str]) -> bool:
    if row["predicted_label"] in {"uncertain", "unsupported"}:
        return True
    if str(qrel.get("needs_review", False)).lower() == "true":
        return True
    if not qrel.get("positive_log_ids"):
        return True
    if row["query_level"] == "hard":
        return True
    return False


def priority_for(row: dict[str, str], qrel: dict[str, Any], stats: Counter[str], sampled: bool) -> str:
    if is_high_priority(row, qrel, stats):
        return "high"
    if sampled:
        return "medium"
    return "low"


def risk_score(row: dict[str, str], qrel: dict[str, Any], stats: Counter[str]) -> int:
    score = 0
    if row["predicted_label"] == "uncertain":
        score += 100
    if row["predicted_label"] == "unsupported":
        score += 95
    if str(qrel.get("needs_review", False)).lower() == "true":
        score += 80
    if row["query_level"] == "hard":
        score += 70
    if row["category"] == "unknown":
        score += 60
    if row["category"] == "latency" and row.get("numeric_evidence"):
        score += 50
    if row["category"] == "storage" and row["dataset"] == "hdfs":
        score += 45
    if row["category"] == "service_unavailable":
        score += 40
    if len(qrel.get("positive_log_ids", [])) < 3:
        score += 35
    if stats.get("uncertain", 0) >= 5:
        score += 25
    return score


def make_output_row(row: dict[str, str], priority: str) -> dict[str, str]:
    predicted_label = row["predicted_label"]
    if predicted_label not in REVIEW_LABELS:
        predicted_label = "uncertain"
    return {
        "dataset": row["dataset"],
        "query_id": row["query_id"],
        "query": row["query"],
        "query_level": row["query_level"],
        "category": row["category"],
        "intent": row["intent"],
        "log_id": row.get("log_id", ""),
        "message": row.get("message", ""),
        "raw_log": row.get("raw_log", ""),
        "predicted_label": predicted_label,
        "review_label": predicted_label,
        "reason": row.get("reason", ""),
        "needs_review": row.get("needs_review", ""),
        "review_priority": priority,
        "review_note": "",
    }


def select_rows(dataset: str, root: Path) -> list[dict[str, str]]:
    rows = read_review_candidates(dataset, root)
    qrels = read_qrels(dataset, root)
    stats = query_stats(rows)
    selected_keys: set[tuple[str, str, str]] = set()
    selected: list[tuple[int, dict[str, str], str]] = []

    rows_by_query: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_query[row["query_id"]].append(row)

    for row in rows:
        qrel = qrels[row["query_id"]]
        if is_high_priority(row, qrel, stats[row["query_id"]]):
            key = (row["query_id"], row.get("log_id", ""), row["predicted_label"])
            if key not in selected_keys:
                selected_keys.add(key)
                selected.append((risk_score(row, qrel, stats[row["query_id"]]), row, "high"))

    for query_id, query_rows in rows_by_query.items():
        qrel = qrels[query_id]
        if str(qrel.get("needs_review", False)).lower() == "true":
            continue
        if not qrel.get("positive_log_ids"):
            continue
        for label in ("positive", "hard_negative"):
            sampled_count = 0
            for row in query_rows:
                if row["predicted_label"] != label:
                    continue
                key = (row["query_id"], row.get("log_id", ""), row["predicted_label"])
                if key in selected_keys:
                    continue
                selected_keys.add(key)
                selected.append((risk_score(row, qrel, stats[query_id]), row, "medium"))
                sampled_count += 1
                if sampled_count >= 3:
                    break

    selected.sort(
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}[item[2]],
            -item[0],
            item[1]["query_id"],
            item[1].get("log_id", ""),
        )
    )
    return [make_output_row(row, priority) for _, row, priority in selected]


def write_manual_review(dataset: str, root: Path, rows: list[dict[str, str]]) -> Path:
    output_path = benchmark_dir(dataset, root) / "review" / "manual_review_v2.csv"
    ensure_dir(output_path.parent)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def markdown_table(rows: list[list[str]]) -> str:
    if len(rows) == 1:
        return "_None._\n"
    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * len(rows[0])) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines) + "\n"


def build_report(dataset: str, root: Path, selected_rows: list[dict[str, str]]) -> str:
    all_rows = read_review_candidates(dataset, root)
    qrels = read_qrels(dataset, root)
    priorities = Counter(row["review_priority"] for row in selected_rows)
    categories = Counter(row["category"] for row in selected_rows)
    labels = Counter(row["predicted_label"] for row in selected_rows)
    review_queries = {
        query_id for query_id, qrel in qrels.items() if qrel.get("needs_review") or not qrel.get("positive_log_ids")
    }
    return "\n".join(
        [
            f"# Manual Review Sampling Report: {dataset}",
            "",
            f"- Total review_candidates_v2 rows: {len(all_rows)}",
            f"- Selected manual_review_v2 rows: {len(selected_rows)}",
            "- Priority counts: "
            + ", ".join(f"{key}={priorities.get(key, 0)}" for key in ("high", "medium", "low")),
            f"- Queries needing review: {len(review_queries)}",
            "",
            "## Category Distribution",
            "",
            markdown_table([["category", "count"]] + [[key, str(value)] for key, value in categories.most_common()]),
            "",
            "## Predicted Label Distribution",
            "",
            markdown_table([["predicted_label", "count"]] + [[key, str(value)] for key, value in labels.most_common()]),
        ]
    )


def write_report(dataset: str, root: Path, selected_rows: list[dict[str, str]]) -> Path:
    output_path = benchmark_dir(dataset, root) / "analysis" / "manual_review_sampling_report.md"
    ensure_dir(output_path.parent)
    output_path.write_text(build_report(dataset, root, selected_rows), encoding="utf-8")
    return output_path


def run_dataset(dataset: str, root: Path) -> tuple[Path, Path, list[dict[str, str]]]:
    dataset = validate_dataset(dataset)
    selected = select_rows(dataset, root)
    manual_path = write_manual_review(dataset, root, selected)
    report_path = write_report(dataset, root, selected)
    return manual_path, report_path, selected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for index, dataset in enumerate(datasets):
        if index:
            print()
        manual_path, report_path, selected = run_dataset(dataset, args.root)
        priorities = Counter(row["review_priority"] for row in selected)
        print(f"Dataset: {dataset}")
        print(f"Manual review rows: {len(selected)}")
        print(
            "Priorities: "
            + ", ".join(f"{key}={priorities.get(key, 0)}" for key in ("high", "medium", "low"))
        )
        print(f"Manual review CSV: {manual_path}")
        print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
