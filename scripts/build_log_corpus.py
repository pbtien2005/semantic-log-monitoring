"""Build per-dataset logs.jsonl corpora from LogHub files."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.io_utils import benchmark_dir, raw_dir, write_jsonl
from src.schema import DATASETS, LogRecord, validate_dataset, validate_log_record
from src.text_utils import (
    extract_component,
    extract_event_id,
    extract_level,
    extract_structured_message,
    extract_timestamp,
    infer_level,
    infer_timestamp,
    normalize_message,
    stable_log_id,
)


LOG_SUFFIXES = {".log", ".txt", ".csv"}

APACHE_BRACKET_RE = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+\[(?P<level>[^\]]+)\]\s*(?P<message>.*)$"
)
OPENSTACK_RE = re.compile(
    r"^(?:(?P<source_log>\S+\.log(?:\.\S+)?)\s+)?"
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)"
    r"\s+(?P<pid>\d+)\s+(?P<level>[A-Z]+)\s+"
    r"(?P<component>[A-Za-z0-9_.$-]+)\s*(?P<message>.*)$"
)
HDFS_RE = re.compile(
    r"^(?P<timestamp>\d{6}\s+\d{6})\s+(?P<pid>\d+)\s+"
    r"(?P<level>[A-Z]+)\s+(?P<component>[^:\s]+):\s*(?P<message>.*)$"
)


@dataclass(slots=True)
class ParsedLine:
    message: str
    timestamp: str | None = None
    component: str | None = None
    level: str | None = None
    event_id: str | None = None


@dataclass(slots=True)
class BuildStats:
    dataset: str
    lines_read: int = 0
    records_created: int = 0
    skipped_lines: int = 0
    error_lines: int = 0
    level_counts: Counter[str] = field(default_factory=Counter)

    def observe_record(self, record: LogRecord) -> None:
        self.records_created += 1
        if record.level:
            self.level_counts[record.level] += 1


@dataclass(slots=True)
class BuildResult:
    records: list[dict[str, Any]]
    stats: BuildStats
    output_path: Path


def is_log_file(path: Path) -> bool:
    return (
        path.is_file()
        and path.name != ".gitkeep"
        and not path.name.startswith(".")
        and path.suffix.lower() in LOG_SUFFIXES
    )


def iter_source_files(dataset_raw_dir: Path) -> list[Path]:
    if not dataset_raw_dir.exists():
        raise FileNotFoundError(f"Raw dataset directory not found: {dataset_raw_dir}")

    candidates = sorted(path for path in dataset_raw_dir.rglob("*") if is_log_file(path))
    structured = [path for path in candidates if path.name.endswith("_structured.csv")]
    if structured:
        return structured
    if not candidates:
        raise FileNotFoundError(f"No .log, .txt, or .csv files found in {dataset_raw_dir}")
    return candidates


def source_key(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def clean_level(level: str | None) -> str | None:
    if level is None:
        return None
    cleaned = level.strip().strip("[]").upper()
    if cleaned == "WARNING":
        return "WARN"
    return cleaned or None


def parse_apache(raw_log: str) -> ParsedLine:
    match = APACHE_BRACKET_RE.match(raw_log)
    if match:
        return ParsedLine(
            message=normalize_message(match.group("message") or raw_log),
            timestamp=match.group("timestamp").strip() or None,
            level=clean_level(match.group("level")),
        )
    return ParsedLine(
        message=raw_log,
        timestamp=infer_timestamp(raw_log),
        level=clean_level(infer_level(raw_log)),
    )


def parse_openstack(raw_log: str) -> ParsedLine:
    match = OPENSTACK_RE.match(raw_log)
    if match:
        return ParsedLine(
            message=normalize_message(match.group("message") or raw_log),
            timestamp=match.group("timestamp").strip() or None,
            component=match.group("component").strip() or None,
            level=clean_level(match.group("level")),
        )
    return ParsedLine(
        message=raw_log,
        timestamp=infer_timestamp(raw_log),
        level=clean_level(infer_level(raw_log)),
    )


def parse_hdfs(raw_log: str) -> ParsedLine:
    match = HDFS_RE.match(raw_log)
    if match:
        return ParsedLine(
            message=normalize_message(match.group("message") or raw_log),
            timestamp=match.group("timestamp").strip() or None,
            component=match.group("component").strip() or None,
            level=clean_level(match.group("level")),
        )
    return ParsedLine(
        message=raw_log,
        timestamp=infer_timestamp(raw_log),
        level=clean_level(infer_level(raw_log)),
    )


def parse_raw_line(dataset: str, raw_log: str) -> ParsedLine:
    if dataset == "apache":
        return parse_apache(raw_log)
    if dataset == "openstack":
        return parse_openstack(raw_log)
    if dataset == "hdfs":
        return parse_hdfs(raw_log)
    validate_dataset(dataset)
    return ParsedLine(message=raw_log)


def make_record(
    *,
    dataset: str,
    source_file: Path,
    source_id: str,
    line_number: int,
    raw_log: str,
    parsed: ParsedLine,
) -> LogRecord:
    message = normalize_message(parsed.message or raw_log)
    return LogRecord(
        log_id=stable_log_id(dataset, source_id, line_number, raw_log),
        dataset=validate_dataset(dataset),
        raw_log=raw_log,
        message=message,
        timestamp=parsed.timestamp,
        component=parsed.component,
        level=clean_level(parsed.level),
        event_id=parsed.event_id,
        source_file=str(source_file),
        line_number=line_number,
    )


def read_structured_csv(
    dataset: str,
    path: Path,
    root: Path,
    stats: BuildStats,
) -> Iterator[LogRecord]:
    source_id = source_key(path, root)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file has no header: {path}")
        for row_number, row in enumerate(reader, start=1):
            stats.lines_read += 1
            try:
                raw_log = normalize_message(row.get("Line", "") or row.get("RawLog", "") or "")
                message = normalize_message(extract_structured_message(row))
                raw_log = raw_log or message
                if not raw_log:
                    stats.skipped_lines += 1
                    continue
                parsed = ParsedLine(
                    message=message or raw_log,
                    timestamp=extract_timestamp(row, raw_log),
                    component=extract_component(row),
                    level=extract_level(row, raw_log),
                    event_id=extract_event_id(row),
                )
                yield make_record(
                    dataset=dataset,
                    source_file=path,
                    source_id=source_id,
                    line_number=row_number,
                    raw_log=raw_log,
                    parsed=parsed,
                )
            except Exception:
                stats.error_lines += 1
                stats.skipped_lines += 1


def read_raw_lines(
    dataset: str,
    path: Path,
    root: Path,
    stats: BuildStats,
) -> Iterator[LogRecord]:
    source_id = source_key(path, root)
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            stats.lines_read += 1
            try:
                raw_log = normalize_message(line)
                if not raw_log:
                    stats.skipped_lines += 1
                    continue
                parsed = parse_raw_line(dataset, raw_log)
                yield make_record(
                    dataset=dataset,
                    source_file=path,
                    source_id=source_id,
                    line_number=line_number,
                    raw_log=raw_log,
                    parsed=parsed,
                )
            except Exception:
                stats.error_lines += 1
                stats.skipped_lines += 1


def build_dataset(dataset: str, root: Path, output: Path | None = None) -> BuildResult:
    dataset = validate_dataset(dataset)
    stats = BuildStats(dataset=dataset)
    records: list[dict[str, Any]] = []
    for source_file in iter_source_files(raw_dir(dataset, root)):
        iterator: Iterator[LogRecord]
        if source_file.name.endswith("_structured.csv"):
            iterator = read_structured_csv(dataset, source_file, root, stats)
        else:
            iterator = read_raw_lines(dataset, source_file, root, stats)
        for record in iterator:
            validate_log_record(record.to_dict())
            stats.observe_record(record)
            records.append(record.to_dict())

    if not records:
        raise ValueError(f"No log records produced for dataset: {dataset}")

    output_path = output or benchmark_dir(dataset, root) / "logs.jsonl"
    write_jsonl(output_path, records)
    return BuildResult(records=records, stats=stats, output_path=output_path)


def format_level_counts(level_counts: Counter[str]) -> str:
    if not level_counts:
        return "none"
    return ", ".join(
        f"{level}={count}" for level, count in sorted(level_counts.items())
    )


def print_stats(result: BuildResult) -> None:
    stats = result.stats
    print(f"Dataset: {stats.dataset}")
    print(f"Output: {result.output_path}")
    print(f"Lines read: {stats.lines_read}")
    print(f"Log records created: {stats.records_created}")
    print(f"Error/skip lines: {stats.error_lines}/{stats.skipped_lines}")
    print(f"Level distribution: {format_level_counts(stats.level_counts)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        required=True,
        choices=(*DATASETS, "all"),
        help="Dataset to build, or 'all' to build apache, openstack, and hdfs.",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path. Only valid when --dataset is not 'all'.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dataset == "all" and args.output is not None:
        raise SystemExit("--output can only be used with one dataset, not --dataset all")

    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for index, dataset in enumerate(datasets):
        result = build_dataset(dataset, args.root, args.output)
        if index:
            print()
        print_stats(result)


if __name__ == "__main__":
    main()
