"""Compact manual review CSVs by selecting pattern representatives.

This script does not edit labels, create clean qrels, create pairs/splits, or
run benchmarks.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.io_utils import benchmark_dir, ensure_dir
from src.schema import DATASETS, validate_dataset


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
    "pattern_group",
    "duplicate_count",
    "review_note",
]

UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
REQ_RE = re.compile(r"\breq-[0-9a-f-]{8,}\b", re.I)
BLOCK_RE = re.compile(r"\bblk_-?\d+\b", re.I)
IP_PORT_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b")
TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b|"
    r"\b\d{6}\s+\d{6}\b|"
    r"\b[A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}\b"
)
HEX_RE = re.compile(r"\b[0-9a-f]{12,}\b", re.I)
NUMBER_RE = re.compile(r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?(?![A-Za-z_])")
WHITESPACE_RE = re.compile(r"\s+")


def read_manual_review(dataset: str, root: Path) -> list[dict[str, str]]:
    path = benchmark_dir(dataset, root) / "review" / "manual_review_v2.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing manual review v2: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_message(text: str) -> str:
    lowered = text.lower()
    lowered = TIMESTAMP_RE.sub("<ts>", lowered)
    lowered = REQ_RE.sub("<request_id>", lowered)
    lowered = UUID_RE.sub("<uuid>", lowered)
    lowered = BLOCK_RE.sub("<block_id>", lowered)
    lowered = IP_PORT_RE.sub("<ip>", lowered)
    lowered = HEX_RE.sub("<hex>", lowered)
    lowered = NUMBER_RE.sub("<num>", lowered)
    lowered = WHITESPACE_RE.sub(" ", lowered).strip()
    return lowered


def pattern_group(row: dict[str, str]) -> str:
    base = normalize_message(row.get("message") or row.get("raw_log") or "")
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]
    return f"{row['predicted_label']}:{digest}"


def risk_score(row: dict[str, str]) -> int:
    score = 0
    if row["review_priority"] == "high":
        score += 100
    elif row["review_priority"] == "medium":
        score += 50
    if row["predicted_label"] == "uncertain":
        score += 90
    if row["predicted_label"] == "unsupported":
        score += 85
    if row["query_level"] == "hard":
        score += 70
    if row.get("needs_review", "").lower() == "true":
        score += 60
    if row["category"] == "unknown":
        score += 50
    if row["dataset"] == "hdfs" and row["category"] == "storage":
        score += 45
    if row["dataset"] == "openstack" and row["category"] == "latency":
        if "duration" in row.get("reason", "").lower():
            score += 45
    if row["dataset"] == "apache" and row["category"] in {"permission", "service_unavailable"}:
        score += 35
    reason = row.get("reason", "").lower()
    if "weak" in reason or "broad" in reason:
        score += 30
    return score


def representative_rows(rows: list[dict[str, str]], max_per_group: int = 3) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[pattern_group(row)].append(row)

    selected: list[dict[str, str]] = []
    for group_id, group_rows in grouped.items():
        ordered = sorted(
            group_rows,
            key=lambda row: (-risk_score(row), row.get("log_id", ""), row.get("message", "")),
        )
        for row in ordered[:max_per_group]:
            copied = dict(row)
            copied["pattern_group"] = group_id
            copied["duplicate_count"] = str(len(group_rows))
            selected.append(copied)
    return selected


def label_limit(label: str) -> int | None:
    if label == "positive":
        return 5
    if label == "hard_negative":
        return 5
    if label == "uncertain":
        return 10
    if label == "unsupported":
        return None
    return 5


def compact_query_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for label in ("unsupported", "uncertain", "positive", "hard_negative"):
        label_rows = [row for row in rows if row["predicted_label"] == label]
        if not label_rows:
            continue
        reps = representative_rows(label_rows)
        reps.sort(key=lambda row: (-risk_score(row), row["pattern_group"], row.get("log_id", "")))
        limit = label_limit(label)
        selected.extend(reps if limit is None else reps[:limit])

    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, str]] = []
    for row in selected:
        key = (row["query_id"], row.get("log_id", ""), row["predicted_label"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    unique.sort(
        key=lambda row: (
            row["query_id"],
            {"unsupported": 0, "uncertain": 1, "positive": 2, "hard_negative": 3}.get(row["predicted_label"], 9),
            -risk_score(row),
            row.get("pattern_group", ""),
        )
    )
    return unique


def compact_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_query: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_query[row["query_id"]].append(row)

    compacted: list[dict[str, str]] = []
    for query_id in sorted(by_query):
        compacted.extend(compact_query_rows(by_query[query_id]))
    return [to_output_row(row) for row in compacted]


def to_output_row(row: dict[str, str]) -> dict[str, str]:
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
        "predicted_label": row["predicted_label"],
        "review_label": row["review_label"],
        "reason": row.get("reason", ""),
        "needs_review": row.get("needs_review", ""),
        "review_priority": row["review_priority"],
        "pattern_group": row.get("pattern_group", pattern_group(row)),
        "duplicate_count": row.get("duplicate_count", "1"),
        "review_note": row.get("review_note", ""),
    }


def write_compact_csv(dataset: str, root: Path, rows: list[dict[str, str]]) -> Path:
    output_path = benchmark_dir(dataset, root) / "review" / "manual_review_compact_v2.csv"
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


def build_report(dataset: str, original: list[dict[str, str]], compacted: list[dict[str, str]]) -> str:
    reduction = 0.0 if not original else (1 - len(compacted) / len(original)) * 100
    labels = Counter(row["predicted_label"] for row in compacted)
    priorities = Counter(row["review_priority"] for row in compacted)
    query_patterns: dict[str, set[str]] = defaultdict(set)
    for row in compacted:
        query_patterns[row["query_id"]].add(row["pattern_group"])
    top_patterns = sorted(query_patterns.items(), key=lambda item: (-len(item[1]), item[0]))[:15]
    warning_queries = sorted(
        {
            row["query_id"]
            for row in compacted
            if row["predicted_label"] in {"uncertain", "unsupported"}
            or row["query_level"] == "hard"
            or row["category"] == "unknown"
        }
    )
    return "\n".join(
        [
            f"# Manual Review Compact Report: {dataset}",
            "",
            f"- Original manual review rows: {len(original)}",
            f"- Compact manual review rows: {len(compacted)}",
            f"- Reduction: {reduction:.1f}%",
            f"- Queries retained: {len({row['query_id'] for row in compacted})}",
            "",
            "## Predicted Label Distribution",
            "",
            markdown_table([["predicted_label", "count"]] + [[key, str(value)] for key, value in labels.most_common()]),
            "",
            "## Review Priority Distribution",
            "",
            markdown_table([["review_priority", "count"]] + [[key, str(value)] for key, value in priorities.most_common()]),
            "",
            "## Top Queries By Pattern Count",
            "",
            markdown_table([["query_id", "pattern_count"]] + [[query_id, str(len(patterns))] for query_id, patterns in top_patterns]),
            "",
            "## Queries Still Needing Careful Review",
            "",
            markdown_table([["query_id"]] + [[query_id] for query_id in warning_queries]),
        ]
    )


def write_report(dataset: str, root: Path, original: list[dict[str, str]], compacted: list[dict[str, str]]) -> Path:
    output_path = benchmark_dir(dataset, root) / "analysis" / "manual_review_compact_report.md"
    ensure_dir(output_path.parent)
    output_path.write_text(build_report(dataset, original, compacted), encoding="utf-8")
    return output_path


def run_dataset(dataset: str, root: Path) -> tuple[Path, Path, list[dict[str, str]], list[dict[str, str]]]:
    dataset = validate_dataset(dataset)
    original = read_manual_review(dataset, root)
    compacted = compact_rows(original)
    csv_path = write_compact_csv(dataset, root, compacted)
    report_path = write_report(dataset, root, original, compacted)
    return csv_path, report_path, original, compacted


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
        csv_path, report_path, original, compacted = run_dataset(dataset, args.root)
        reduction = 0.0 if not original else (1 - len(compacted) / len(original)) * 100
        print(f"Dataset: {dataset}")
        print(f"Original rows: {len(original)}")
        print(f"Compact rows: {len(compacted)}")
        print(f"Reduction: {reduction:.1f}%")
        print(f"Compact CSV: {csv_path}")
        print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
