"""Build line and template chunks from parsed log corpora."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.chunking.builders import build_line_chunk, build_template_chunks
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
    template_chunks: list[dict[str, Any]],
) -> dict[str, Path]:
    chunk_dir = ensure_dir(chunking_dir(dataset, root))
    line_path = chunk_dir / "log_lines.jsonl"
    template_path = chunk_dir / "templates.jsonl"
    write_jsonl(line_path, line_chunks)
    write_jsonl(template_path, template_chunks)
    return {"log_lines": line_path, "templates": template_path}


def build_dataset_chunks(dataset: str, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Path]]:
    logs = load_logs(dataset, root)
    line_chunks = [build_line_chunk(log) for log in logs]
    template_chunks = build_template_chunks(line_chunks)
    outputs = write_outputs(dataset, root, line_chunks, template_chunks)
    return line_chunks, template_chunks, outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args()


def print_stats(
    dataset: str,
    line_chunks: list[dict[str, Any]],
    template_chunks: list[dict[str, Any]],
    outputs: dict[str, Path],
) -> None:
    line_count = len(line_chunks)
    template_count = len(template_chunks)
    reduction = 1 - (template_count / line_count) if line_count else 0
    print(f"Dataset: {dataset}")
    print(f"Line chunks: {line_count}")
    print(f"Template chunks: {template_count}")
    print(f"Template reduction: {reduction:.1%}")
    print(f"log_lines: {outputs['log_lines']}")
    print(f"templates: {outputs['templates']}")


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for index, dataset in enumerate(datasets):
        if index:
            print()
        line_chunks, template_chunks, outputs = build_dataset_chunks(dataset, args.root)
        print_stats(dataset, line_chunks, template_chunks, outputs)


if __name__ == "__main__":
    main()
