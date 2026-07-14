"""Analyze unsupported query-bank entries against real logs.

This script suggests candidate patterns for review. It does not create labels,
qrels, pairs, or benchmark results.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))

from infra.scripts.benchmark.validate_query_bank import apply_filters, validate_dataset_queries
from src.benchmark.query_bank import QUERY_BANK
from src.core.io_utils import ensure_dir, read_jsonl
from src.core.schema import DATASETS, validate_dataset
from src.rules.category_rules import log_text, rules_for


DISCOVERY_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "apache": {
        "service_unavailable": (
            "error state",
            "workerenv",
            "mod_jk",
            "file does not exist",
            "not found",
            "failed to open",
            "script not found",
        ),
        "permission": (
            "directory index forbidden",
            "client denied",
            "forbidden by rule",
            "permission denied",
        ),
        "connection": (
            "connection reset",
            "broken pipe",
            "client closed connection",
            "socket",
        ),
        "unknown": (
            "scoreboard",
            "worker",
            "child",
            "init",
            "notice",
        ),
    },
    "openstack": {
        "latency": ("took", "slow", "delayed", "scheduling delay"),
        "storage": ("imagecache", "base file", "_base", "image cache"),
        "network": ("network-vif", "neutron", "vif", "binding", "port"),
        "database": ("database", "hypervisor", "power states"),
        "service_unavailable": (
            "no valid host",
            "instance failed",
            "service down",
            "unavailable",
        ),
        "unknown": (
            "nova",
            "instance",
            "lifecycle",
            "claim",
            "resource",
            "metadata",
            "scheduler",
        ),
    },
    "hdfs": {
        "storage": (
            "blk_",
            "blockmap",
            "addstoredblock",
            "packetresponder",
            "fsdataset",
            "replication",
            "pipeline",
        ),
        "service_unavailable": (
            "exception while serving",
            "got exception while serving",
            "exception",
            "failed",
            "node down",
            "datanode dead",
        ),
        "connection": ("socket", "connection", "broken pipe", "host"),
        "network": ("socket", "packet", "host", ":50010"),
        "unknown": ("verification succeeded", "warn", "error", "exception"),
    },
}


TOKEN_RE = re.compile(r"[A-Za-z_.$-][A-Za-z0-9_.$:-]{2,}")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "logs",
    "log",
    "query",
    "true",
    "false",
    "none",
    "info",
    "warn",
    "error",
}


def escape_cell(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def markdown_table(rows: list[list[str]]) -> str:
    if len(rows) == 1:
        return "_None._\n"
    header = rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines) + "\n"


def pattern_counts(
    dataset: str,
    category: str,
    logs: list[dict[str, Any]],
) -> Counter[str]:
    patterns = (
        tuple(rule.pattern for rule in rules_for(dataset, category))
        + DISCOVERY_PATTERNS.get(dataset, {}).get(category, ())
    )
    counts: Counter[str] = Counter()
    for log in logs:
        text = log_text(log)
        for pattern in patterns:
            if pattern.startswith("\\"):
                continue
            if pattern.lower() in text:
                counts[pattern] += 1
    return counts


def frequent_terms(logs: list[dict[str, Any]], *, limit: int = 12) -> Counter[str]:
    counts: Counter[str] = Counter()
    for log in logs:
        for token in TOKEN_RE.findall(log_text(log)):
            token = token.lower().strip(":-")
            if token in STOPWORDS or len(token) < 4:
                continue
            if re.fullmatch(r"\d+(?:\.\d+)+(?::\d+)?", token):
                continue
            counts[token] += 1
    return Counter(dict(counts.most_common(limit)))


def sample_messages(logs: list[dict[str, Any]], *, limit: int = 3) -> list[str]:
    samples: list[str] = []
    seen: set[str] = set()
    for log in logs:
        message = str(log.get("message") or log.get("raw_log") or "")
        if message in seen:
            continue
        seen.add(message)
        samples.append(message[:220])
        if len(samples) >= limit:
            break
    return samples


def suggestion_from_patterns(
    pattern_counter: Counter[str],
    term_counter: Counter[str],
) -> str:
    if pattern_counter:
        top = ", ".join(pattern for pattern, _ in pattern_counter.most_common(5))
        return f"Review adding or strengthening pattern(s): {top}."
    if term_counter:
        top = ", ".join(term for term, _ in term_counter.most_common(5))
        return f"No direct pattern hit; inspect frequent terms: {top}."
    return "No useful pattern found; consider revising or dropping this query."


def build_report(dataset: str, root: Path) -> str:
    dataset = validate_dataset(dataset)
    analysis_path = (
        root
        / "data"
        / "benchmark"
        / dataset
        / "analysis"
        / "query_bank_validation.md"
    )
    previous_report_present = analysis_path.exists()
    logs_path = root / "data" / "benchmark" / dataset / "logs.jsonl"
    logs = list(read_jsonl(logs_path))
    validations = validate_dataset_queries(dataset, root)
    unsupported = [result for result in validations if not result.supported]

    rows = [[
        "query_id",
        "category",
        "filters",
        "filtered_logs",
        "candidate_patterns",
        "frequent_terms",
        "sample_messages",
        "suggestion",
    ]]

    for result in unsupported:
        filtered_logs = apply_filters(logs, result.spec)
        patterns = pattern_counts(dataset, result.spec.category, filtered_logs)
        terms = frequent_terms(filtered_logs)
        rows.append(
            [
                result.query_id,
                result.spec.category,
                escape_cell(
                    {
                        "component": result.spec.filters.component,
                        "level": result.spec.filters.level,
                        "time_range": result.spec.filters.time_range,
                    }
                ),
                str(len(filtered_logs)),
                escape_cell(
                    ", ".join(
                        f"{pattern}={count}"
                        for pattern, count in patterns.most_common(8)
                    )
                ),
                escape_cell(
                    ", ".join(
                        f"{term}={count}" for term, count in terms.most_common(8)
                    )
                ),
                escape_cell(" / ".join(sample_messages(filtered_logs))),
                suggestion_from_patterns(patterns, terms),
            ]
        )

    lines = [
        f"# Unsupported Query Analysis: {dataset}",
        "",
        f"- Query bank entries: {len(QUERY_BANK[dataset])}",
        f"- Unsupported queries under current rules: {len(unsupported)}",
        f"- Existing validation report found: {'yes' if previous_report_present else 'no'}",
        "",
        "## Unsupported Queries",
        "",
        markdown_table(rows),
    ]
    return "\n".join(lines)


def write_report(dataset: str, root: Path) -> Path:
    output_dir = root / "data" / "benchmark" / dataset / "analysis"
    ensure_dir(output_dir)
    output_path = output_dir / "unsupported_query_analysis.md"
    output_path.write_text(build_report(dataset, root), encoding="utf-8")
    return output_path


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
        output_path = write_report(dataset, args.root)
        unsupported = [
            result
            for result in validate_dataset_queries(dataset, args.root)
            if not result.supported
        ]
        print(f"Dataset: {dataset}")
        print(f"Report: {output_path}")
        print(f"Unsupported queries: {len(unsupported)}")


if __name__ == "__main__":
    main()
