"""Audit generated chunk artifacts for shape and normalization quality."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.core.io_utils import benchmark_dir, chunking_dir, ensure_dir, read_jsonl
from src.core.schema import DATASETS, validate_dataset
from src.chunking.template_matcher import DEFAULT_TEMPLATE_DIR


FILTER_FIELDS = (
    "component",
    "level",
    "timestamp_ms",
    "request_id",
    "instance_id",
    "block_id",
    "ip",
    "http_status",
    "duration_ms",
)
TEMPLATE_PLACEHOLDERS = (
    "<req_id>",
    "<instance_id>",
    "<uuid>",
    "<hex_id>",
    "<block_id>",
    "<block_id_list>",
    "<ip_port>",
    "<ip>",
    "<path>",
    "<status>",
    "<status_2xx>",
    "<status_3xx>",
    "<status_4xx>",
    "<status_5xx>",
    "<len>",
    "<duration>",
    "<duration_normal>",
    "<duration_slow>",
    "<state_code>",
    "<error_code>",
    "<exit_code>",
    "<retry_count>",
    "<port>",
    "<num>",
)

RAW_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("request_id", re.compile(r"\breq-[0-9a-fA-F-]{36}\b")),
    ("uuid", re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")),
    ("hex_id", re.compile(r"\b[0-9a-fA-F]{32}\b")),
    ("block_id", re.compile(r"\bblk_-?\d+\b")),
    ("ip", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b")),
)


def load_artifacts(
    dataset: str,
    root: Path,
    template_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    dataset = validate_dataset(dataset)
    logs = list(read_jsonl(benchmark_dir(dataset, root) / "logs.jsonl"))
    line_chunks = list(read_jsonl(chunking_dir(dataset, root) / "log_lines.jsonl"))
    template_base = root / template_dir if not template_dir.is_absolute() else template_dir
    catalog_records = list(read_jsonl(template_base / f"{dataset}_templates.jsonl"))
    return logs, line_chunks, catalog_records


def percent(count: int, total: int) -> str:
    if not total:
        return "0.0%"
    return f"{count / total:.1%}"


def average(values: list[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def null_rates(line_chunks: list[dict[str, Any]]) -> list[tuple[str, int, str]]:
    total = len(line_chunks)
    rows: list[tuple[str, int, str]] = []
    for field in FILTER_FIELDS:
        missing = sum(1 for chunk in line_chunks if is_missing(chunk.get(field)))
        rows.append((field, missing, percent(missing, total)))
    return rows


def unique_check(chunks: list[dict[str, Any]]) -> tuple[bool, int]:
    ids = [str(chunk.get("chunk_id") or chunk.get("template_id")) for chunk in chunks]
    unique_count = len(set(ids))
    return unique_count == len(ids), unique_count


def template_text(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata", {})
    return str(chunk.get("template") or metadata.get("template") or "")


def placeholder_ratio(template: str) -> float:
    tokens = template.split()
    if not tokens:
        return 0.0
    placeholder_tokens = sum(
        1 for token in tokens if any(marker in token for marker in TEMPLATE_PLACEHOLDERS)
    )
    return placeholder_tokens / len(tokens)


def raw_pattern_hits(template_chunks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    hits: dict[str, list[dict[str, Any]]] = {name: [] for name, _ in RAW_PATTERNS}
    for chunk in template_chunks:
        template = template_text(chunk)
        for name, pattern in RAW_PATTERNS:
            if pattern.search(template):
                hits[name].append(chunk)
    return hits


def suspicious_templates(template_chunks: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    suspicious: list[tuple[str, str, str]] = []
    for chunk in template_chunks:
        metadata = chunk.get("metadata", {})
        template = template_text(chunk)
        occurrence_count = metadata.get("occurrence_count", 0)
        semantic_tokens = [
            token
            for token in template.split()
            if not any(marker in token for marker in TEMPLATE_PLACEHOLDERS)
        ]
        if len(semantic_tokens) <= 2:
            suspicious.append((str(chunk.get("chunk_id") or chunk.get("template_id")), "too_few_semantic_tokens", template))
        if placeholder_ratio(template) >= 0.65:
            suspicious.append((str(chunk.get("chunk_id") or chunk.get("template_id")), "placeholder_heavy", template))
        if occurrence_count == 1:
            suspicious.append((str(chunk.get("chunk_id") or chunk.get("template_id")), "singleton", template))
    return suspicious


def chunk_signals(chunk: dict[str, Any], field: str) -> list[str]:
    metadata = chunk.get("metadata", {})
    values = metadata.get(field) or chunk.get(field) or []
    return [str(value) for value in values]


def quality_metrics(
    line_chunks: list[dict[str, Any]],
    template_chunks: list[dict[str, Any]],
) -> dict[str, int | str]:
    matched_template_ids = [
        str(chunk.get("template_id"))
        for chunk in line_chunks
        if chunk.get("metadata", {}).get("template_match_status") == "matched"
        and chunk.get("template_id")
    ]
    matched_count = len(matched_template_ids)
    unmatched_count = len(line_chunks) - matched_count
    catalog_template_ids = {str(record.get("template_id")) for record in template_chunks}
    seen_template_ids = set(matched_template_ids)
    ambiguous_count = sum(
        1 for chunk in line_chunks if int(chunk.get("metadata", {}).get("ambiguous_match_count") or 0) > 0
    )
    entity_coverage_count = sum(
        1
        for chunk in line_chunks
        if any(chunk.get("metadata", {}).get("entities", {}).values())
    )
    singleton_count = sum(
        1
        for chunk in template_chunks
        if int(chunk.get("metadata", {}).get("occurrence_count") or 0) == 1
    )
    top_20_count = sum(
        int(chunk.get("metadata", {}).get("occurrence_count") or 0)
        for chunk in top_templates(template_chunks, 20)
    )
    raw_hits = raw_pattern_hits(template_chunks)
    leaked_template_ids = {
        str(chunk.get("chunk_id"))
        for chunks in raw_hits.values()
        for chunk in chunks
    }
    over_normalized = {
        chunk_id
        for chunk_id, reason, _template in suspicious_templates(template_chunks)
        if reason in {"too_few_semantic_tokens", "placeholder_heavy"}
    }
    unknown_signal_count = sum(
        1
        for chunk in line_chunks
        if "unknown" in set(chunk_signals(chunk, "signals") + chunk_signals(chunk, "weak_signals"))
    )
    weak_signal_count = sum(1 for chunk in line_chunks if chunk_signals(chunk, "weak_signals"))
    embed_lengths = [len(str(chunk.get("embed_text") or "")) for chunk in line_chunks]

    return {
        "total_logs": len(line_chunks),
        "total_templates": len(template_chunks),
        "matched_template_count": matched_count,
        "unmatched_template_count": unmatched_count,
        "unmatched_template_ratio": percent(unmatched_count, len(line_chunks)),
        "templates_never_seen": len(catalog_template_ids - seen_template_ids),
        "ambiguous_match_count": ambiguous_count,
        "entity_extraction_coverage": percent(entity_coverage_count, len(line_chunks)),
        "unique_template_ratio": percent(len(template_chunks), len(line_chunks)),
        "singleton_template_ratio": percent(singleton_count, len(template_chunks)),
        "top_20_template_coverage": percent(top_20_count, len(line_chunks)),
        "unknown_signal_ratio": percent(unknown_signal_count, len(line_chunks)),
        "weak_signal_ratio": percent(weak_signal_count, len(line_chunks)),
        "avg_embed_text_length": f"{average(embed_lengths):.1f}",
        "templates_with_real_id_leak": len(leaked_template_ids),
        "templates_over_normalized": len(over_normalized),
    }


def top_templates(template_chunks: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return sorted(
        template_chunks,
        key=lambda chunk: (
            -int(chunk.get("metadata", {}).get("occurrence_count") or 0),
            str(chunk.get("component") or ""),
            str(chunk.get("level") or ""),
            template_text(chunk),
        ),
    )[:limit]


def match_counts(line_chunks: list[dict[str, Any]]) -> Counter[str]:
    return Counter(
        str(chunk.get("template_id"))
        for chunk in line_chunks
        if chunk.get("metadata", {}).get("template_match_status") == "matched"
        and chunk.get("template_id")
    )


def top_unmatched_normalized_templates(line_chunks: list[dict[str, Any]], limit: int) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for chunk in line_chunks:
        metadata = chunk.get("metadata", {})
        if metadata.get("template_match_status") != "matched":
            counter[str(metadata.get("template") or "")] += 1
    return counter.most_common(limit)


def field_presence(line_chunks: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for chunk in line_chunks:
        for field in FILTER_FIELDS:
            if not is_missing(chunk.get(field)):
                counter[field] += 1
    return counter


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(cell.replace("\n", "<br>") for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def build_report(dataset: str, logs: list[dict[str, Any]], line_chunks: list[dict[str, Any]], template_chunks: list[dict[str, Any]], sample_limit: int) -> str:
    line_unique_ok, line_unique_count = unique_check(line_chunks)
    template_unique_ok, template_unique_count = unique_check(template_chunks)
    raw_hits = raw_pattern_hits(template_chunks)
    suspicious = suspicious_templates(template_chunks)
    singleton_count = sum(
        1
        for chunk in template_chunks
        if int(chunk.get("metadata", {}).get("occurrence_count") or 0) == 1
    )
    presence = field_presence(line_chunks)
    metrics = quality_metrics(line_chunks, template_chunks)
    template_match_counts = match_counts(line_chunks)
    never_seen = [
        str(record.get("template_id"))
        for record in template_chunks
        if str(record.get("template_id")) not in template_match_counts
    ]
    top_catalog_templates = top_templates(template_chunks, sample_limit)
    catalog_columns = ["priority", "template"]
    if any("component" in chunk for chunk in top_catalog_templates):
        catalog_columns.insert(1, "component")
    if any("level" in chunk for chunk in top_catalog_templates):
        insert_at = 2 if "component" in catalog_columns else 1
        catalog_columns.insert(insert_at, "level")
    catalog_rows = [
        [
            template_text(chunk) if column == "template" else str(chunk.get(column) or "")
            for column in catalog_columns
        ]
        for chunk in top_catalog_templates
    ]

    report: list[str] = [
        f"# Chunk Audit: {dataset}",
        "",
        "## Counts",
        "",
        markdown_table(
            ["metric", "value"],
            [
                ["logs", str(len(logs))],
                ["line_chunks", str(len(line_chunks))],
                ["catalog_templates", str(len(template_chunks))],
                ["line_chunks_match_logs", "PASS" if len(logs) == len(line_chunks) else "FAIL"],
                ["unique_line_chunk_ids", f"{'PASS' if line_unique_ok else 'FAIL'} ({line_unique_count})"],
                ["unique_catalog_template_ids", f"{'PASS' if template_unique_ok else 'FAIL'} ({template_unique_count})"],
                ["singleton_templates", f"{singleton_count} ({percent(singleton_count, len(template_chunks))})"],
            ],
        ),
        "",
        "## Quality Metrics",
        "",
        markdown_table(
            ["metric", "value"],
            [[name, str(value)] for name, value in metrics.items()],
        ),
        "",
        "## Filter Field Null Rates",
        "",
        markdown_table(
            ["field", "present", "missing", "missing_rate"],
            [
                [field, str(presence[field]), str(missing), rate]
                for field, missing, rate in null_rates(line_chunks)
            ],
        ),
        "",
        "## Raw Pattern Leakage In Templates",
        "",
        markdown_table(
            ["pattern", "template_count"],
            [[name, str(len(chunks))] for name, chunks in raw_hits.items()],
        ),
        "",
        "## Match Count By Template",
        "",
        markdown_table(
            ["template_id", "match_count"],
            [[template_id, str(count)] for template_id, count in template_match_counts.most_common(sample_limit)],
        ),
        "",
        "## Top Unmatched Normalized Templates",
        "",
        markdown_table(
            ["count", "normalized_template"],
            [[str(count), template] for template, count in top_unmatched_normalized_templates(line_chunks, sample_limit)],
        ),
        "",
        "## Catalog Templates Never Seen",
        "",
        markdown_table(
            ["template_id"],
            [[template_id] for template_id in never_seen[:sample_limit]],
        ),
        "",
        "## Top Catalog Templates",
        "",
        markdown_table(catalog_columns, catalog_rows),
        "",
        "## Suspicious Template Samples",
        "",
    ]

    if suspicious:
        report.append(
            markdown_table(
                ["reason", "chunk_id", "template"],
                [[reason, chunk_id, template] for chunk_id, reason, template in suspicious[:sample_limit]],
            )
        )
    else:
        report.append("_None._")

    report.extend(["", "## Line Chunk Samples", ""])
    report.append(
        markdown_table(
            ["chunk_id", "embed_text"],
            [
                [str(chunk.get("chunk_id")), str(chunk.get("embed_text"))]
                for chunk in line_chunks[:sample_limit]
            ],
        )
    )
    return "\n".join(report) + "\n"


def write_report(dataset: str, root: Path, report: str) -> Path:
    path = ensure_dir(chunking_dir(dataset, root)) / "audit.md"
    path.write_text(report, encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR)
    parser.add_argument("--sample-limit", type=int, default=10)
    return parser.parse_args()


def print_summary(dataset: str, logs: list[dict[str, Any]], line_chunks: list[dict[str, Any]], template_chunks: list[dict[str, Any]], report_path: Path) -> None:
    raw_hits = raw_pattern_hits(template_chunks)
    suspicious = suspicious_templates(template_chunks)
    metrics = quality_metrics(line_chunks, template_chunks)
    print(f"Dataset: {dataset}")
    print(f"Logs/line chunks/catalog templates: {len(logs)}/{len(line_chunks)}/{len(template_chunks)}")
    print(f"Line count match: {'PASS' if len(logs) == len(line_chunks) else 'FAIL'}")
    print(f"Matched/unmatched: {metrics['matched_template_count']}/{metrics['unmatched_template_count']} ({metrics['unmatched_template_ratio']} unmatched)")
    print("Raw pattern leakage: " + ", ".join(f"{name}={len(chunks)}" for name, chunks in raw_hits.items()))
    print(f"Suspicious templates: {len(suspicious)}")
    print(f"Report: {report_path}")


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for index, dataset in enumerate(datasets):
        if index:
            print()
        logs, line_chunks, template_chunks = load_artifacts(dataset, args.root, args.template_dir)
        report = build_report(dataset, logs, line_chunks, template_chunks, args.sample_limit)
        report_path = write_report(dataset, args.root, report)
        print_summary(dataset, logs, line_chunks, template_chunks, report_path)


if __name__ == "__main__":
    main()
