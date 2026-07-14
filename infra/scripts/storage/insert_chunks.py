"""Embed chunk artifacts and upsert them into Milvus."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.core.io_utils import chunking_dir, read_jsonl
from src.core.schema import DATASETS, validate_dataset


DEFAULT_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
LOG_LINE_COLLECTION = "log_line"
REQUIRED_UPSERT_FIELDS = (
    "log_id",
    "dataset",
    "template_id",
    "level",
    "component",
    "timestamp_ms",
    "payload",
    "vector",
)
REQUIRED_PAYLOAD_FIELDS = ("chunk_id", "raw_log", "message", "embed_text")


def load_dependencies() -> tuple[Any, Any]:
    try:
        from pymilvus import MilvusClient
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency. Install requirements first:\n"
            "  pip install -r requirements.txt"
        ) from exc
    return MilvusClient, SentenceTransformer


def compact_json(value: Any) -> Any:
    if isinstance(value, dict):
        compacted = {
            key: compact_json(item)
            for key, item in value.items()
            if item is not None
        }
        return {
            key: item
            for key, item in compacted.items()
            if item is not None and item != [] and item != {}
        }
    if isinstance(value, list):
        return [compact_json(item) for item in value if item is not None]
    return value


def prefixed_passage(text: str) -> str:
    return f"passage: {text}"


def batched(records: list[dict[str, Any]], batch_size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(records), batch_size):
        yield records[start : start + batch_size]


def load_chunk_records(path: Path, limit: int | None) -> list[dict[str, Any]]:
    records = list(read_jsonl(path))
    if limit is not None:
        return records[:limit]
    return records


def log_line_payload(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = chunk["metadata"]
    template = metadata["template"]
    current_template_id = chunk.get("template_id") or metadata.get("template_id")

    def field(name: str) -> Any:
        return metadata[name] if name in metadata else chunk.get(name)

    payload = {
        "chunk_id": chunk["chunk_id"],
        "raw_log": metadata.get("raw_log"),
        "message": metadata.get("message"),
        "template_id": current_template_id,
        "candidate_id": metadata.get("candidate_id"),
        "template": template,
        "template_match_status": metadata.get("template_match_status"),
        "template_match_method": metadata.get("template_match_method"),
        "template_match_confidence": metadata.get("template_match_confidence"),
        "template_slots": metadata.get("template_slots"),
        "embed_text": chunk["embed_text"],
        "line_number": metadata.get("line_number"),
        "source_file": metadata.get("source_file"),
        "source_log": metadata.get("source_log"),
        "timestamp": metadata.get("timestamp"),
        "request_id": metadata.get("request_id"),
        "instance_id": metadata.get("instance_id"),
        "block_id": metadata.get("block_id"),
        "ip": metadata.get("ip"),
        "ip_port": metadata.get("ip_port"),
        "http_status": metadata.get("http_status"),
        "http_method": metadata.get("http_method"),
        "api_route": metadata.get("api_route"),
        "http_version": metadata.get("http_version"),
        "response_len": metadata.get("response_len"),
        "duration_ms": metadata.get("duration_ms"),
        "task_state": metadata.get("task_state"),
        "module": metadata.get("module"),
        "path": metadata.get("path"),
        "source_id": metadata.get("source_id"),
        "source": metadata.get("source"),
        "service": metadata.get("service"),
        "host": metadata.get("host"),
        "environment": metadata.get("environment"),
        "ingested_at": metadata.get("ingested_at"),
        "schema_version": metadata.get("schema_version"),
        "parser_version": metadata.get("parser_version"),
        "trace_id": metadata.get("trace_id"),
        "kafka_topic": metadata.get("kafka_topic"),
        "kafka_partition": metadata.get("kafka_partition"),
        "kafka_offset": metadata.get("kafka_offset"),
        "anomaly": field("anomaly"),
        "anomaly_score": field("anomaly_score"),
        "anomaly_level": field("anomaly_level"),
        "anomaly_decision": field("anomaly_decision"),
        "anomaly_baseline_status": field("anomaly_baseline_status"),
        "anomaly_reasons": field("anomaly_reasons"),
        "anomaly_components": field("anomaly_components"),
    }
    return compact_json(payload)


def build_log_line_rows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for chunk in chunks:
        current_template_id = chunk.get("template_id") or chunk["metadata"].get("template_id")
        rows.append(
            {
                "log_id": chunk["log_id"],
                "dataset": chunk["dataset"],
                "template_id": current_template_id,
                "level": chunk.get("level"),
                "component": chunk.get("component"),
                "timestamp_ms": chunk.get("timestamp_ms"),
                "payload": log_line_payload(chunk),
                "_embed_text": chunk["embed_text"],
            }
        )
    return rows


def dedupe_rows_by_primary_key(
    rows: list[dict[str, Any]],
    *,
    primary_key: str = "log_id",
) -> list[dict[str, Any]]:
    seen: set[Any] = set()
    deduped_reversed: list[dict[str, Any]] = []
    for row in reversed(rows):
        value = row.get(primary_key)
        if value in seen:
            continue
        seen.add(value)
        deduped_reversed.append(row)
    return list(reversed(deduped_reversed))


def build_upsert_rows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return dedupe_rows_by_primary_key(build_log_line_rows(chunks))


def embed_rows(rows: list[dict[str, Any]], model: Any, batch_size: int) -> None:
    for batch in batched(rows, batch_size):
        texts = [prefixed_passage(row.pop("_embed_text")) for row in batch]
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        for row, vector in zip(batch, vectors, strict=True):
            row["vector"] = vector.tolist()


def validate_upsert_row(row: dict[str, Any]) -> None:
    missing_fields = [field for field in REQUIRED_UPSERT_FIELDS if field not in row]
    if missing_fields:
        raise ValueError(
            f"Milvus upsert row {row.get('log_id', '<unknown>')} "
            f"is missing required fields: {', '.join(missing_fields)}"
        )

    payload = row["payload"]
    if not isinstance(payload, dict):
        raise ValueError(f"Milvus upsert row {row['log_id']} payload must be an object")

    missing_payload_fields = [
        field for field in REQUIRED_PAYLOAD_FIELDS if field not in payload
    ]
    if missing_payload_fields:
        raise ValueError(
            f"Milvus upsert row {row['log_id']} payload is missing required fields: "
            f"{', '.join(missing_payload_fields)}"
        )


def validate_upsert_rows(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        validate_upsert_row(row)


def upsert_rows(
    client: Any,
    collection_name: str,
    rows: list[dict[str, Any]],
    batch_size: int,
) -> int:
    total = 0
    for batch in batched(rows, batch_size):
        validate_upsert_rows(batch)
        result = client.upsert(collection_name=collection_name, data=batch)
        total += int(result.get("upsert_count", result.get("insert_count", len(batch))))
    if rows:
        client.flush(collection_name)
    return total


def embedding_dimension(model: Any) -> int:
    if hasattr(model, "get_embedding_dimension"):
        return int(model.get_embedding_dimension())
    return int(model.get_sentence_embedding_dimension())


def insert_dataset(
    *,
    dataset: str,
    root: Path,
    client: Any,
    model: Any,
    limit: int | None,
    batch_size: int,
) -> int:
    dataset = validate_dataset(dataset)
    chunk_dir = chunking_dir(dataset, root)
    line_chunks = load_chunk_records(chunk_dir / "log_lines.jsonl", limit)

    line_rows = build_upsert_rows(line_chunks)

    embed_rows(line_rows, model, batch_size)

    line_count = upsert_rows(client, LOG_LINE_COLLECTION, line_rows, batch_size)
    return line_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--uri", default=DEFAULT_URI, help="Milvus URI.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="SentenceTransformer model name.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit rows per artifact file. Useful for smoke tests.",
    )
    parser.add_argument("--batch-size", type=int, default=32)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be positive")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive")

    milvus_client, sentence_transformer = load_dependencies()
    client = milvus_client(uri=args.uri)
    model = sentence_transformer(args.model)

    expected_dim = 768
    model_dim = embedding_dimension(model)
    if model_dim != expected_dim:
        raise SystemExit(
            f"Model dimension mismatch: collection expects {expected_dim}, "
            f"but {args.model} outputs {model_dim}."
        )

    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    print(f"Milvus URI: {args.uri}")
    print(f"Embedding model: {args.model} ({model_dim} dims)")
    print()

    total_lines = 0
    for dataset in datasets:
        line_count = insert_dataset(
            dataset=dataset,
            root=args.root,
            client=client,
            model=model,
            limit=args.limit,
            batch_size=args.batch_size,
        )
        total_lines += line_count
        print(f"{dataset}: log_line={line_count}")

    print()
    print(f"Inserted log_line rows: {total_lines}")


if __name__ == "__main__":
    main()
