"""Build line and template chunks from parsed log corpora."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.chunking.builders import build_line_chunk
from src.chunking.template_matcher import DEFAULT_TEMPLATE_DIR, TemplateMatcher
from src.core.io_utils import benchmark_dir, chunking_dir, ensure_dir, read_jsonl, write_jsonl
from src.core.schema import DATASETS, validate_dataset, validate_log_record


def load_logs(dataset: str, root: Path) -> list[dict[str, Any]]:
    dataset = validate_dataset(dataset)
    logs_path = benchmark_dir(dataset, root) / "logs.jsonl"
    logs = list(read_jsonl(logs_path))
    for log in logs:
        validate_log_record(log)
        if log["dataset"] != dataset:
            raise ValueError(f"{logs_path} contains mixed dataset row: {log['dataset']}")
    return logs


def write_outputs(
    dataset: str,
    root: Path,
    line_chunks: list[dict[str, Any]],
) -> dict[str, Path]:
    chunk_dir = ensure_dir(chunking_dir(dataset, root))
    line_path = chunk_dir / "log_lines.jsonl"
    write_jsonl(line_path, line_chunks)
    return {"log_lines": line_path}


def build_dataset_chunks(
    dataset: str,
    root: Path,
    template_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Path]]:
    logs = load_logs(dataset, root)
    matcher = TemplateMatcher.load(root, dataset, template_dir=template_dir)
    line_chunks = [build_line_chunk(log, template_matcher=matcher) for log in logs]
    outputs = write_outputs(dataset, root, line_chunks)
    return line_chunks, outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR)
    return parser.parse_args()


def print_stats(
    dataset: str,
    line_chunks: list[dict[str, Any]],
    outputs: dict[str, Path],
) -> None:
    line_count = len(line_chunks)
    matched = sum(1 for chunk in line_chunks if chunk["metadata"].get("template_match_status") == "matched")
    unmatched = line_count - matched
    unmatched_rate = unmatched / line_count if line_count else 0
    print(f"Dataset: {dataset}")
    print(f"Line chunks: {line_count}")
    print(f"Matched templates: {matched}")
    print(f"Unmatched templates: {unmatched} ({unmatched_rate:.1%})")
    print(f"log_lines: {outputs['log_lines']}")


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for index, dataset in enumerate(datasets):
        if index:
            print()
        line_chunks, outputs = build_dataset_chunks(dataset, args.root, args.template_dir)
        print_stats(dataset, line_chunks, outputs)


if __name__ == "__main__":
    main()
