"""Run a semantic search smoke test against Milvus chunk collections."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.core.schema import DATASETS


DEFAULT_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
COLLECTIONS = ("log_line",)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


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


def quote_expr(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_filter(dataset: str | None, level: str | None, component: str | None) -> str:
    clauses = []
    if dataset:
        clauses.append(f"dataset == {quote_expr(dataset)}")
    if level:
        clauses.append(f"level == {quote_expr(level)}")
    if component:
        clauses.append(f"component == {quote_expr(component)}")
    return " and ".join(clauses)


def encode_query(model: Any, query: str) -> list[float]:
    vector = model.encode(
        [f"query: {query}"],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]
    return vector.tolist()


def summarize_payload(payload: dict[str, Any]) -> str:
    raw_log = payload.get("raw_log")
    message = payload.get("message")
    template = payload.get("template")
    return str(raw_log or message or template or payload.get("embed_text") or "")[:300]


def print_hits(collection_name: str, hits: list[dict[str, Any]]) -> None:
    print(f"\n[{collection_name}]")
    if not hits:
        print("No hits.")
        return

    for index, hit in enumerate(hits, start=1):
        entity = hit.get("entity", {})
        payload = entity.get("payload", {})
        primary_id = entity.get("log_id") or entity.get("template_id")
        score = hit.get("distance")
        print(f"{index}. score={score:.4f} id={primary_id}")
        print(f"   dataset={entity.get('dataset')} level={entity.get('level')} component={entity.get('component')}")
        print(f"   text={summarize_payload(payload)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--dataset", choices=DATASETS)
    parser.add_argument("--level")
    parser.add_argument("--component")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--uri", default=DEFAULT_URI)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k must be positive")

    milvus_client, sentence_transformer = load_dependencies()
    client = milvus_client(uri=args.uri)
    model = sentence_transformer(args.model)
    query_vector = encode_query(model, args.query)
    expr = build_filter(args.dataset, args.level, args.component)

    print(f"Query: {args.query}")
    print(f"Filter: {expr or 'none'}")

    for collection_name in COLLECTIONS:
        output_fields = ["dataset", "level", "component", "payload"]
        output_fields.insert(0, "log_id")
        results = client.search(
            collection_name=collection_name,
            data=[query_vector],
            anns_field="vector",
            filter=expr,
            limit=args.top_k,
            output_fields=output_fields,
            search_params={"metric_type": "COSINE", "params": {}},
        )
        print_hits(collection_name, results[0] if results else [])


if __name__ == "__main__":
    main()
