"""Search logs with the adaptive retrieval layer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.core.schema import DATASETS
from src.retrieval.milvus_search import (
    DEFAULT_MODEL,
    DEFAULT_URI,
    RetrievalResult,
    execute_plan,
)
from src.retrieval.query_planner import PlannerOptions, plan_query
from src.retrieval.template_registry import TemplateRegistry

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


def summarize_result(result: RetrievalResult) -> str:
    payload = result.entity.get("payload", {})
    if result.collection == "template":
        return str(payload.get("template") or payload.get("embed_text") or "")[:350]
    return str(
        payload.get("raw_log")
        or payload.get("message")
        or payload.get("template")
        or payload.get("embed_text")
        or ""
    )[:350]


def print_result(index: int, result: RetrievalResult) -> None:
    entity = result.entity
    print(
        f"{index}. score={result.score:.4f} semantic={result.semantic_score:.4f} "
        f"id={result.primary_id} source={result.source}"
    )
    print(
        "   "
        f"dataset={entity.get('dataset')} level={entity.get('level')} "
        f"component={entity.get('component')}"
    )
    if result.collection == "log_line":
        print(
            "   "
            f"template_id={entity.get('template_id')} "
            f"timestamp_ms={entity.get('timestamp_ms')}"
        )
    else:
        print(f"   occurrences={entity.get('occurrences')}")
    print(f"   text={summarize_result(result)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--dataset", choices=DATASETS)
    parser.add_argument("--level")
    parser.add_argument("--component")
    parser.add_argument("--top-k", type=int, default=24)
    parser.add_argument("--template-k", type=int, default=8)
    parser.add_argument("--uri", default=DEFAULT_URI)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k must be positive")
    if args.template_k < 1:
        raise SystemExit("--template-k must be positive")

    planner_options = PlannerOptions(
        dataset=args.dataset,
        level=args.level,
        component=args.component,
        top_k=args.top_k,
    )
    plan = plan_query(args.query, planner_options)

    milvus_client, sentence_transformer = load_dependencies()
    client = milvus_client(uri=args.uri)
    model = sentence_transformer(args.model) if plan.use_vector_search else None
    registry = TemplateRegistry.load(Path.cwd()) if plan.use_vector_search else None
    response = execute_plan(
        client=client,
        model=model,
        plan=plan,
        template_k=args.template_k,
        template_registry=registry,
    )

    print(f"Query: {args.query}")
    print(f"Semantic query: {plan.semantic_query}")
    print(f"Vector search: {plan.use_vector_search}")
    print(f"Template filter applied: {plan.applied_template_filter}")
    print(f"Fallback used: {plan.fallback_used}")
    print(f"Filter: {response.filter_expr or 'none'}")

    print("\n[log_line evidence]")
    if not response.log_lines:
        print("No log_line hits.")
    for index, result in enumerate(response.log_lines, start=1):
        print_result(index, result)

    print("\n[template patterns]")
    if not response.templates:
        print("No template hits.")
    for index, result in enumerate(response.templates, start=1):
        print_result(index, result)


if __name__ == "__main__":
    main()
