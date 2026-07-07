"""Bootstrap fixed template catalog files from existing template artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.chunking.template_matcher import DEFAULT_TEMPLATE_DIR, regex_from_template
from src.core.io_utils import chunking_dir, ensure_dir, read_jsonl, write_jsonl
from src.core.schema import DATASETS, validate_dataset


def intent_from_template(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for value in (metadata.get("event_type"), metadata.get("event_family")):
        if value and value not in values:
            values.append(str(value))
    for signal in metadata.get("signals") or []:
        signal = str(signal)
        if signal.startswith("level_") or signal.startswith("has_"):
            continue
        if signal not in values:
            values.append(signal)
    return values


def catalog_record(template_chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = template_chunk.get("metadata") if isinstance(template_chunk.get("metadata"), dict) else {}
    template = str(metadata.get("template") or template_chunk.get("template") or "")
    if not template:
        raise ValueError(f"Template chunk is missing template: {template_chunk}")
    return {
        "template_id": template_chunk["chunk_id"],
        "dataset": template_chunk["dataset"],
        "component": template_chunk.get("component"),
        "level": template_chunk.get("level"),
        "template": template,
        "regex": regex_from_template(template),
        "intent": intent_from_template(metadata),
        "event_type": metadata.get("event_type") or template_chunk.get("event_type"),
        "event_family": metadata.get("event_family") or template_chunk.get("event_family"),
        "signals": metadata.get("signals") or [],
        "weak_signals": metadata.get("weak_signals") or [],
        "priority": 100,
        "active": True,
    }


def build_dataset_catalog(*, dataset: str, root: Path, output_dir: Path) -> int:
    dataset = validate_dataset(dataset)
    template_path = chunking_dir(dataset, root) / "templates.jsonl"
    records = [catalog_record(record) for record in read_jsonl(template_path)]
    output_path = ensure_dir(output_dir) / f"{dataset}_templates.jsonl"
    write_jsonl(output_path, records)
    return len(records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_TEMPLATE_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    output_dir = args.root / args.output_dir if not args.output_dir.is_absolute() else args.output_dir
    for dataset in datasets:
        count = build_dataset_catalog(dataset=dataset, root=args.root, output_dir=output_dir)
        print(f"{dataset}: catalog_templates={count}")


if __name__ == "__main__":
    main()
