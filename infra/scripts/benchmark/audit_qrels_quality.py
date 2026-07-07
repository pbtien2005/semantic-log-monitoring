"""Audit qrels/review candidates for likely rule-label quality issues."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.benchmark.query_bank import QUERY_BANK
from src.core.io_utils import benchmark_dir, ensure_dir
from src.core.schema import DATASETS, validate_dataset
from src.rules.category_rules import extract_took_seconds, score_log, scoring_profile


def escape_cell(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def markdown_table(rows: list[list[str]]) -> str:
    if len(rows) == 1:
        return "_None._\n"
    lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * len(rows[0])) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines) + "\n"


def load_review_rows(dataset: str, root: Path) -> list[dict[str, str]]:
    path = benchmark_dir(dataset, root) / "review" / "review_candidates.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing review candidates: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def row_to_log(row: dict[str, str]) -> dict[str, Any]:
    return {
        "log_id": row.get("log_id", ""),
        "raw_log": row.get("raw_log", ""),
        "message": row.get("message", ""),
        "level": "",
        "component": "",
    }


def suspicion_reason(dataset: str, row: dict[str, str]) -> str | None:
    if row.get("predicted_label") != "positive":
        return None
    category = row["category"]
    log = row_to_log(row)
    scored = score_log(dataset, category, log)
    profile = scoring_profile(category)
    label = scored.label(profile)
    text = f"{row.get('raw_log', '')} {row.get('message', '')}".lower()

    if category == "latency":
        seconds = extract_took_seconds(text)
        if seconds is not None and seconds < 5:
            return f"latency false positive: took {seconds:.2f}s < 5s"
        if seconds is not None and seconds < 10:
            return f"latency uncertain: took {seconds:.2f}s between 5s and 10s"
    if category == "service_unavailable" and any(
        marker in text
        for marker in ("vm stopped", "vm started", "lifecycle event", "completed successfully")
    ):
        return "service_unavailable false positive: normal lifecycle event"
    if category == "storage" and dataset == "hdfs" and scored.label(profile) != "positive":
        return "storage false positive risk: block-only or normal storage event"
    if category == "unknown":
        return "broad unknown positive: generic error/warn/exception requires review"
    if label != "positive":
        return f"v2 scoring would mark as {label}: {scored.reason}"
    if scored.weak_only:
        return "weak-only match should be reviewed"
    return None


def audit_dataset(dataset: str, root: Path) -> str:
    dataset = validate_dataset(dataset)
    rows = load_review_rows(dataset, root)
    by_query: dict[str, list[dict[str, str]]] = defaultdict(list)
    suspected: list[tuple[dict[str, str], str]] = []
    pattern_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        by_query[row["query_id"]].append(row)
        if row.get("predicted_label") == "positive":
            scored = score_log(dataset, row["category"], row_to_log(row))
            for pattern in scored.matched_strong_patterns:
                pattern_counts[row["query_id"]][pattern] += 1
            for pattern in scored.matched_weak_patterns:
                pattern_counts[row["query_id"]][f"~{pattern}"] += 1
            reason = suspicion_reason(dataset, row)
            if reason:
                suspected.append((row, reason))

    summary_rows = [["query_id", "positive", "hard_negative", "uncertain", "patterns"]]
    for query_id in sorted(by_query):
        counts = Counter(row["predicted_label"] for row in by_query[query_id])
        summary_rows.append(
            [
                query_id,
                str(counts.get("positive", 0)),
                str(counts.get("hard_negative", 0)),
                str(counts.get("uncertain", 0)),
                escape_cell(", ".join(f"{p}={c}" for p, c in pattern_counts[query_id].most_common(6))),
            ]
        )

    suspected_rows = [["query_id", "category", "reason", "message", "suggestion"]]
    for row, reason in suspected[:80]:
        suspected_rows.append(
            [
                row["query_id"],
                row["category"],
                escape_cell(reason),
                escape_cell((row.get("message") or row.get("raw_log") or "")[:220]),
                suggestion_for(row["category"], reason),
            ]
        )

    return "\n".join(
        [
            f"# Qrels Quality Audit: {dataset}",
            "",
            f"- Review rows: {len(rows)}",
            f"- Positive rows suspected: {len(suspected)}",
            "",
            "## Per Query Label Counts",
            "",
            markdown_table(summary_rows),
            "",
            "## Top Suspected False Positives",
            "",
            markdown_table(suspected_rows),
        ]
    )


def suggestion_for(category: str, reason: str) -> str:
    if category == "latency":
        return "Use duration thresholds: <5s hard_negative/ignore, 5-10s uncertain, >=10s positive."
    if category == "storage":
        return "Require storage issue context, not block-only matches."
    if category == "service_unavailable":
        return "Exclude normal lifecycle events; require failed/unavailable/crashed/exception evidence."
    if category == "unknown":
        return "Keep needs_review=true; avoid confident positives from generic error/warn only."
    return "Move weak matches to uncertain unless stronger evidence exists."


def write_report(dataset: str, root: Path) -> Path:
    output = benchmark_dir(dataset, root) / "analysis" / "qrels_quality_audit.md"
    ensure_dir(output.parent)
    output.write_text(audit_dataset(dataset, root), encoding="utf-8")
    return output


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
        report = write_report(dataset, args.root)
        rows = load_review_rows(dataset, args.root)
        suspected = sum(1 for row in rows if suspicion_reason(dataset, row))
        print(f"Dataset: {dataset}")
        print(f"Report: {report}")
        print(f"Suspected positive issues: {suspected}")


if __name__ == "__main__":
    main()
