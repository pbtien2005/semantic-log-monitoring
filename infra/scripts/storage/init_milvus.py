"""Initialize Milvus collections for chunk storage."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))


DEFAULT_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
DEFAULT_DIM = 768
COLLECTION_NAMES = ("log_line",)


def load_pymilvus() -> tuple[Any, Any]:
    try:
        from pymilvus import DataType, MilvusClient
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency: pymilvus. Install requirements first:\n"
            "  pip install -r requirements.txt"
        ) from exc
    return DataType, MilvusClient


def add_varchar_field(
    schema: Any,
    data_type: Any,
    name: str,
    max_length: int,
    *,
    nullable: bool = False,
    is_primary: bool = False,
    is_partition_key: bool = False,
) -> None:
    schema.add_field(
        field_name=name,
        datatype=data_type.VARCHAR,
        max_length=max_length,
        nullable=nullable,
        is_primary=is_primary,
        is_partition_key=is_partition_key,
    )


def build_log_line_schema(data_type: Any, milvus_client: Any, dim: int) -> Any:
    schema = milvus_client.create_schema(auto_id=False, enable_dynamic_field=False)

    add_varchar_field(schema, data_type, "log_id", 256, is_primary=True)
    add_varchar_field(schema, data_type, "dataset", 64, is_partition_key=True)
    add_varchar_field(schema, data_type, "template_id", 256, nullable=True)
    add_varchar_field(schema, data_type, "level", 32, nullable=True)
    add_varchar_field(schema, data_type, "component", 512, nullable=True)
    schema.add_field("timestamp_ms", data_type.INT64, nullable=True)
    schema.add_field("payload", data_type.JSON)
    schema.add_field("vector", data_type.FLOAT_VECTOR, dim=dim)

    return schema


def build_collection_schema(
    collection_name: str,
    data_type: Any,
    milvus_client: Any,
    dim: int,
) -> Any:
    if collection_name == "log_line":
        return build_log_line_schema(data_type, milvus_client, dim)
    raise ValueError(f"Unsupported collection: {collection_name}")


def build_index_params(milvus_client: Any, metric_type: str, index_type: str) -> Any:
    index_params = milvus_client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_name="vector_index",
        index_type=index_type,
        metric_type=metric_type,
        params={},
    )
    return index_params


def create_collection(
    client: Any,
    data_type: Any,
    milvus_client: Any,
    collection_name: str,
    *,
    dim: int,
    metric_type: str,
    index_type: str,
    reset: bool,
) -> str:
    exists = client.has_collection(collection_name)
    if exists and not reset:
        return "exists"

    if exists and reset:
        client.drop_collection(collection_name)

    schema = build_collection_schema(collection_name, data_type, milvus_client, dim)
    index_params = build_index_params(milvus_client, metric_type, index_type)
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params,
    )
    client.load_collection(collection_name)
    return "created"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", default=DEFAULT_URI, help="Milvus URI.")
    parser.add_argument(
        "--dim",
        type=int,
        default=DEFAULT_DIM,
        help="Embedding vector dimension. Must match the embedding model.",
    )
    parser.add_argument(
        "--metric-type",
        default="COSINE",
        choices=("COSINE", "IP", "L2"),
        help="Vector similarity metric.",
    )
    parser.add_argument(
        "--index-type",
        default="FLAT",
        help="Milvus vector index type. FLAT is fine for local benchmark data.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate existing collections.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dim <= 1:
        raise SystemExit("--dim must be greater than 1")

    data_type, milvus_client = load_pymilvus()
    client = milvus_client(uri=args.uri)

    print(f"Milvus URI: {args.uri}")
    print(f"Vector dim: {args.dim}")
    print(f"Metric/index: {args.metric_type}/{args.index_type}")
    print()

    for collection_name in COLLECTION_NAMES:
        status = create_collection(
            client,
            data_type,
            milvus_client,
            collection_name,
            dim=args.dim,
            metric_type=args.metric_type,
            index_type=args.index_type,
            reset=args.reset,
        )
        print(f"{collection_name}: {status}")

    print()
    print("Collections:", ", ".join(client.list_collections()))


if __name__ == "__main__":
    main()
