"""File IO helpers for JSONL benchmark artifacts."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def read_jsonl(path: str | Path) -> Iterator[JsonDict]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {file_path} at line {line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(
                    f"Expected JSON object in {file_path} at line {line_number}"
                )
            yield value


def write_jsonl(
    path: str | Path,
    records: Iterable[JsonDict],
    *,
    overwrite: bool = True,
) -> int:
    file_path = Path(path)
    ensure_dir(file_path.parent)
    if file_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {file_path}")

    count = 0
    with file_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
            count += 1
    return count


def read_jsonl_list(path: str | Path) -> list[JsonDict]:
    return list(read_jsonl(path))


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def benchmark_dir(dataset: str, root: str | Path | None = None) -> Path:
    base = Path(root) if root is not None else project_root()
    return base / "data" / "benchmark" / dataset


def raw_dir(dataset: str, root: str | Path | None = None) -> Path:
    base = Path(root) if root is not None else project_root()
    return base / "data" / "raw" / dataset

