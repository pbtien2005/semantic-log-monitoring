"""Validate QUERY_BANK coverage against real logs.jsonl files.

This script does not create qrels, pairs, or benchmark artifacts. It only checks
whether each query has rule-based candidate logs in its own dataset.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.category_rules import RuleMatch, match_log
from src.io_utils import ensure_dir, read_jsonl
from src.query_bank import QUERY_BANK, QuerySpec
from src.schema import DATASETS, validate_dataset


@dataclass(slots=True)
class QueryValidation:
    query_id: str
    spec: QuerySpec
    filtered_log_count: int
    candidate_count: int
    supported: bool
    weak_candidate_count: int
    matched_patterns: Counter[str]
    needs_review: bool
    reasons: list[str]
    suggestion: str


def apply_filters(logs: list[dict[str, Any]], spec: QuerySpec) -> list[dict[str, Any]]:
    filters = spec.filters
    filtered = logs
    if filters.component is not None:
        filtered = [log for log in filtered if log.get("component") == filters.component]
    if filters.level is not None:
        filtered = [log for log in filtered if log.get("level") == filters.level]
    return filtered


def candidate_matches(
    dataset: str,
    category: str,
    logs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, Counter[str]]:
    candidates: list[dict[str, Any]] = []
    weak_candidate_count = 0
    matched_patterns: Counter[str] = Counter()
    for log in logs:
        matches = match_log(dataset, category, log)
        if not matches:
            continue
        candidates.append(log)
        if all(match.weak for match in matches):
            weak_candidate_count += 1
        for match in matches:
            marker = "~" if match.weak else ""
            matched_patterns[f"{marker}{match.pattern}"] += 1
    return candidates, weak_candidate_count, matched_patterns


def has_filter(spec: QuerySpec) -> bool:
    return (
        spec.filters.component is not None
        or spec.filters.level is not None
        or spec.filters.time_range is not None
    )


def review_reasons(
    spec: QuerySpec,
    filtered_log_count: int,
    candidate_count: int,
    weak_candidate_count: int,
    total_logs: int,
) -> list[str]:
    reasons: list[str] = []
    if spec.category == "unknown":
        reasons.append("unknown category uses ERROR/WARN-only fallback")
    if filtered_log_count == 0:
        reasons.append("filter matches no logs")
    if candidate_count == 0:
        reasons.append("no candidate logs found")
    if candidate_count > 0:
        if weak_candidate_count == candidate_count:
            reasons.append("only weak keyword/pattern matches")
        elif weak_candidate_count:
            reasons.append("some weak keyword/pattern matches")
        denominator = filtered_log_count or total_logs
        if denominator and candidate_count / denominator >= 0.7:
            reasons.append("candidate set is broad")
        elif candidate_count >= 500:
            reasons.append("candidate set is large")
    return reasons


def suggestion_for(spec: QuerySpec, reasons: list[str]) -> str:
    if "filter matches no logs" in reasons:
        return "Fix or remove the component/level filter so it matches logs.jsonl."
    if "no candidate logs found" in reasons:
        return (
            "Revise the query category or add a dataset-specific keyword rule before "
            "using it for qrels."
        )
    if "candidate set is broad" in reasons or "candidate set is large" in reasons:
        return "Make the query more specific or add a component/level filter."
    if "only weak keyword/pattern matches" in reasons:
        return "Keep for review, but add a stronger dataset-specific pattern if possible."
    if "some weak keyword/pattern matches" in reasons:
        return "Candidate logs exist, but inspect weak matches before creating qrels."
    if spec.category == "unknown":
        return "Manually review; unknown queries rely on abnormal-level or anomaly patterns."
    return "Looks supported by the current keyword rules."


def validate_dataset_queries(dataset: str, root: Path) -> list[QueryValidation]:
    dataset = validate_dataset(dataset)
    specs = QUERY_BANK[dataset]
    logs_path = root / "data" / "benchmark" / dataset / "logs.jsonl"
    logs = list(read_jsonl(logs_path))
    if not logs:
        raise ValueError(f"No logs found for {dataset}: {logs_path}")

    results: list[QueryValidation] = []
    for index, spec in enumerate(specs, start=1):
        query_id = f"{dataset}_q{index:03d}"
        filtered_logs = apply_filters(logs, spec)
        candidates, weak_candidate_count, matched_patterns = candidate_matches(
            dataset,
            spec.category,
            filtered_logs,
        )
        reasons = review_reasons(
            spec=spec,
            filtered_log_count=len(filtered_logs),
            candidate_count=len(candidates),
            weak_candidate_count=weak_candidate_count,
            total_logs=len(logs),
        )
        results.append(
            QueryValidation(
                query_id=query_id,
                spec=spec,
                filtered_log_count=len(filtered_logs),
                candidate_count=len(candidates),
                supported=bool(candidates),
                weak_candidate_count=weak_candidate_count,
                matched_patterns=matched_patterns,
                needs_review=bool(reasons),
                reasons=reasons,
                suggestion=suggestion_for(spec, reasons),
            )
        )
    return results


def filter_dict(spec: QuerySpec) -> dict[str, str | None]:
    return {
        "component": spec.filters.component,
        "level": spec.filters.level,
        "time_range": spec.filters.time_range,
    }


def markdown_table(rows: list[list[str]]) -> str:
    if not rows:
        return "_None._\n"
    header = rows[0]
    separator = ["---"] * len(header)
    body = rows[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines) + "\n"


def escape_cell(value: Any) -> str:
    text = str(value).replace("\n", " ").replace("|", "\\|")
    return text


def format_patterns(patterns: Counter[str], *, limit: int = 5) -> str:
    if not patterns:
        return ""
    return ", ".join(
        f"{pattern}={count}" for pattern, count in patterns.most_common(limit)
    )


def build_report(dataset: str, results: list[QueryValidation]) -> str:
    total = len(results)
    levels = Counter(result.spec.query_level for result in results)
    languages = Counter(result.spec.language for result in results)
    categories = Counter(result.spec.category for result in results)
    supported = sum(1 for result in results if result.supported)
    unsupported = total - supported
    with_filter = [result for result in results if has_filter(result.spec)]
    filter_no_match = [
        result for result in with_filter if result.filtered_log_count == 0
    ]
    needs_review = [result for result in results if result.needs_review]
    broad = [
        result
        for result in results
        if "candidate set is broad" in result.reasons
        or "candidate set is large" in result.reasons
    ]

    lines = [
        f"# Query Bank Validation: {dataset}",
        "",
        "## Summary",
        "",
        f"- Total queries: {total}",
        "- Query levels: "
        + ", ".join(f"{key}={levels[key]}" for key in ("easy", "medium", "hard")),
        "- Languages: " + ", ".join(f"{key}={languages[key]}" for key in ("vi", "en")),
        "- Categories: "
        + ", ".join(f"{key}={value}" for key, value in categories.most_common()),
        f"- Queries with candidate logs: {supported}",
        f"- Queries without candidate logs: {unsupported}",
        f"- Queries with filters: {len(with_filter)}",
        f"- Filters with no matching logs: {len(filter_no_match)}",
        f"- Queries needing review: {len(needs_review)}",
        f"- Broad queries: {len(broad)}",
        "",
        "## Filter Mismatches",
        "",
    ]

    lines.append(
        markdown_table(
            [["query_id", "query", "category", "filters", "suggestion"]]
            + [
                [
                    result.query_id,
                    escape_cell(result.spec.query),
                    result.spec.category,
                    escape_cell(filter_dict(result.spec)),
                    result.suggestion,
                ]
                for result in filter_no_match
            ]
        )
    )

    lines.extend(["", "## Queries Needing Review", ""])
    lines.append(
        markdown_table(
            [
                [
                    "query_id",
                    "level",
                    "language",
                    "category",
                    "candidates",
                    "matched_patterns",
                    "reasons",
                    "query",
                    "suggestion",
                ]
            ]
            + [
                [
                    result.query_id,
                    result.spec.query_level,
                    result.spec.language,
                    result.spec.category,
                    str(result.candidate_count),
                    escape_cell(format_patterns(result.matched_patterns)),
                    escape_cell(", ".join(result.reasons)),
                    escape_cell(result.spec.query),
                    result.suggestion,
                ]
                for result in needs_review
            ]
        )
    )

    lines.extend(["", "## Suggestions To Revise Or Drop", ""])
    revise_or_drop = [
        result
        for result in results
        if not result.supported
        or "candidate set is broad" in result.reasons
        or "candidate set is large" in result.reasons
    ]
    lines.append(
        markdown_table(
            [["query_id", "candidate_count", "matched_patterns", "query", "suggestion"]]
            + [
                [
                    result.query_id,
                    str(result.candidate_count),
                    escape_cell(format_patterns(result.matched_patterns)),
                    escape_cell(result.spec.query),
                    result.suggestion,
                ]
                for result in revise_or_drop
            ]
        )
    )

    lines.extend(["", "## Per-Query Candidate Counts", ""])
    lines.append(
        markdown_table(
            [
                [
                    "query_id",
                    "level",
                    "language",
                    "category",
                    "filters",
                    "filtered_logs",
                    "candidate_logs",
                    "weak_candidates",
                    "matched_patterns",
                    "supported",
                ]
            ]
            + [
                [
                    result.query_id,
                    result.spec.query_level,
                    result.spec.language,
                    result.spec.category,
                    escape_cell(filter_dict(result.spec)),
                    str(result.filtered_log_count),
                    str(result.candidate_count),
                    str(result.weak_candidate_count),
                    escape_cell(format_patterns(result.matched_patterns)),
                    "yes" if result.supported else "no",
                ]
                for result in results
            ]
        )
    )
    return "\n".join(lines)


def write_report(dataset: str, root: Path, results: list[QueryValidation]) -> Path:
    output_dir = root / "data" / "benchmark" / dataset / "analysis"
    ensure_dir(output_dir)
    output_path = output_dir / "query_bank_validation.md"
    output_path.write_text(build_report(dataset, results), encoding="utf-8")
    return output_path


def print_stats(dataset: str, results: list[QueryValidation], output_path: Path) -> None:
    total = len(results)
    levels = Counter(result.spec.query_level for result in results)
    languages = Counter(result.spec.language for result in results)
    categories = Counter(result.spec.category for result in results)
    supported = sum(1 for result in results if result.supported)
    with_filter = sum(1 for result in results if has_filter(result.spec))
    filter_mismatch = sum(
        1 for result in results if has_filter(result.spec) and result.filtered_log_count == 0
    )
    needs_review = sum(1 for result in results if result.needs_review)
    weak_supported = sum(
        1
        for result in results
        if result.supported and result.weak_candidate_count == result.candidate_count
    )
    print(f"Dataset: {dataset}")
    print(f"Report: {output_path}")
    print(f"Queries: {total}")
    print(
        "Levels: "
        + ", ".join(f"{key}={levels[key]}" for key in ("easy", "medium", "hard"))
    )
    print("Languages: " + ", ".join(f"{key}={languages[key]}" for key in ("vi", "en")))
    print(
        "Categories: "
        + ", ".join(f"{key}={value}" for key, value in categories.most_common())
    )
    print(f"Supported: {supported}")
    print(f"Unsupported: {total - supported}")
    print(f"Queries with filters: {with_filter}")
    print(f"Filter mismatches: {filter_mismatch}")
    print(f"Needs review: {needs_review}")
    print(f"Weak-only supported: {weak_supported}")


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
        results = validate_dataset_queries(dataset, args.root)
        output_path = write_report(dataset, args.root, results)
        print_stats(dataset, results, output_path)


if __name__ == "__main__":
    main()
