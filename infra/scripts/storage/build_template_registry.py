"""Build retrieval-ready in-memory template registry artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.core.io_utils import ensure_dir, read_jsonl, write_jsonl
from src.core.schema import DATASETS, validate_dataset
from src.chunking.builders import meaningful_value
from src.chunking.template_matcher import DEFAULT_TEMPLATE_DIR
from src.retrieval.template_registry import META_FILE, REGISTRY_FILE, VECTORS_FILE


DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
DEFAULT_OUTPUT = Path("data") / "retrieval" / "template_registry"


def load_dependencies() -> Any:
    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency: sentence-transformers. Install requirements first:\n"
            "  pip install -r requirements.txt"
        ) from exc
    return SentenceTransformer


def prefixed_passage(text: str) -> str:
    return f"passage: {text}"


def build_search_text(record: dict[str, Any]) -> str:
    template = record.get("template") or ""
    fields = (
        ("dataset", record.get("dataset")),
        ("component", record.get("component")),
        ("level", record.get("level")),
        ("template", template),
    )
    return "\n".join(
        f"{name}: {text}"
        for name, value in fields
        if (text := meaningful_value(value))
    )


def registry_record(catalog_record: dict[str, Any], vector_index: int) -> dict[str, Any]:
    record = {
        "vector_index": vector_index,
        "template_id": catalog_record["template_id"],
        "dataset": catalog_record["dataset"],
        "template": catalog_record.get("template"),
        "regex": catalog_record.get("regex"),
        "search_text": build_search_text(catalog_record),
        "occurrences": 0,
        "priority": int(catalog_record.get("priority") or 0),
    }
    for optional_key in (
        "component",
        "level",
        "active",
    ):
        if optional_key in catalog_record:
            record[optional_key] = catalog_record.get(optional_key)
    return record


def build_dataset_registry(
    *,
    dataset: str,
    root: Path,
    template_dir: Path,
    output_root: Path,
    model: Any,
    batch_size: int,
    limit: int | None,
) -> int:
    dataset = validate_dataset(dataset)
    template_base = root / template_dir if not template_dir.is_absolute() else template_dir
    template_path = template_base / f"{dataset}_templates.jsonl"
    catalog_records = [
        record
        for record in read_jsonl(template_path)
        if bool(record.get("active", True))
    ]
    if limit is not None:
        catalog_records = catalog_records[:limit]
    records = [registry_record(record, index) for index, record in enumerate(catalog_records)]

    output_dir = ensure_dir(output_root / dataset)
    write_jsonl(output_dir / REGISTRY_FILE, records)

    texts = [prefixed_passage(str(record["search_text"])) for record in records]
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    np.save(output_dir / VECTORS_FILE, np.asarray(vectors, dtype=np.float32))
    return len(records)


def embedding_dimension(model: Any) -> int:
    if hasattr(model, "get_embedding_dimension"):
        return int(model.get_embedding_dimension())
    return int(model.get_sentence_embedding_dimension())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be positive")

    sentence_transformer = load_dependencies()
    model = sentence_transformer(args.model)
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    output_root = args.root / args.output_root if not args.output_root.is_absolute() else args.output_root
    ensure_dir(output_root)

    counts: dict[str, int] = {}
    for dataset in datasets:
        counts[dataset] = build_dataset_registry(
            dataset=dataset,
            root=args.root,
            template_dir=args.template_dir,
            output_root=output_root,
            model=model,
            batch_size=args.batch_size,
            limit=args.limit,
        )
        print(f"{dataset}: templates={counts[dataset]}")

    meta = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": args.model,
        "embedding_dim": embedding_dimension(model),
        "normalized": True,
        "datasets": list(datasets),
        "template_count": sum(counts.values()),
        "dataset_counts": counts,
    }
    (output_root / META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"registry_meta: {output_root / META_FILE}")


if __name__ == "__main__":
    main()
