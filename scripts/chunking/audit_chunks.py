"""Audit generated chunk artifacts for shape and normalization quality."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.core.io_utils import benchmark_dir, chunking_dir, ensure_dir, read_jsonl
from src.core.schema import DATASETS, validate_dataset


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
    "<len>",
    "<duration>",
    "<num>",
)

RAW_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("request_id", re.compile(r"\breq-[0-9a-fA-F-]{36}\b")),
    ("uuid", re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")),
    ("hex_id", re.compile(r"\b[0-9a-fA-F]{32}\b")),
    ("block_id", re.compile(r"\bblk_-?\d+\b")),
    ("ip", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b")),
)


def load_artifacts(dataset: str, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    dataset = validate_dataset(dataset)
    logs = list(read_jsonl(benchmark_dir(dataset, root) / "logs.jsonl"))
    line_chunks = list(read_jsonl(chunking_dir(dataset, root) / "log_lines.jsonl"))
    template_chunks = list(read_jsonl(chunking_dir(dataset, root) / "templates.jsonl"))
    return logs, line_chunks, template_chunks


def percent(count: int, total: int) -> str:
    if not total:
        return "0.0%"
    return f"{count / total:.1%}"


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
    ids = [str(chunk.get("chunk_id")) for chunk in chunks]
    unique_count = len(set(ids))
    return unique_count == len(ids), unique_count


def template_text(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata", {})
    return str(metadata.get("template") or "")


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
            suspicious.append((str(chunk["chunk_id"]), "too_few_semantic_tokens", template))
        if placeholder_ratio(template) >= 0.65:
            suspicious.append((str(chunk["chunk_id"]), "placeholder_heavy", template))
        if occurrence_count == 1:
            suspicious.append((str(chunk["chunk_id"]), "singleton", template))
    return suspicious


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
                ["template_chunks", str(len(template_chunks))],
                ["line_chunks_match_logs", "PASS" if len(logs) == len(line_chunks) else "FAIL"],
                ["unique_line_chunk_ids", f"{'PASS' if line_unique_ok else 'FAIL'} ({line_unique_count})"],
                ["unique_template_chunk_ids", f"{'PASS' if template_unique_ok else 'FAIL'} ({template_unique_count})"],
                ["singleton_templates", f"{singleton_count} ({percent(singleton_count, len(template_chunks))})"],
            ],
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
        "## Top Templates",
        "",
        markdown_table(
            ["count", "component", "level", "template"],
            [
                [
                    str(chunk.get("metadata", {}).get("occurrence_count")),
                    str(chunk.get("component")),
                    str(chunk.get("level")),
                    template_text(chunk),
                ]
                for chunk in top_templates(template_chunks, sample_limit)
            ],
        ),
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
    parser.add_argument("--sample-limit", type=int, default=10)
    return parser.parse_args()


def print_summary(dataset: str, logs: list[dict[str, Any]], line_chunks: list[dict[str, Any]], template_chunks: list[dict[str, Any]], report_path: Path) -> None:
    raw_hits = raw_pattern_hits(template_chunks)
    suspicious = suspicious_templates(template_chunks)
    singleton_count = sum(
        1
        for chunk in template_chunks
        if int(chunk.get("metadata", {}).get("occurrence_count") or 0) == 1
    )
    print(f"Dataset: {dataset}")
    print(f"Logs/line chunks/templates: {len(logs)}/{len(line_chunks)}/{len(template_chunks)}")
    print(f"Line count match: {'PASS' if len(logs) == len(line_chunks) else 'FAIL'}")
    print(f"Raw pattern leakage: " + ", ".join(f"{name}={len(chunks)}" for name, chunks in raw_hits.items()))
    print(f"Singleton templates: {singleton_count} ({percent(singleton_count, len(template_chunks))})")
    print(f"Suspicious templates: {len(suspicious)}")
    print(f"Report: {report_path}")


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for index, dataset in enumerate(datasets):
        if index:
            print()
        logs, line_chunks, template_chunks = load_artifacts(dataset, args.root)
        report = build_report(dataset, logs, line_chunks, template_chunks, args.sample_limit)
        report_path = write_report(dataset, args.root, report)
        print_summary(dataset, logs, line_chunks, template_chunks, report_path)


if __name__ == "__main__":
    main()
