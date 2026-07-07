"""Run retrieval and generate a Vietnamese RAG answer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.core.schema import DATASETS
from src.rag.answer import DEFAULT_RAG_BASE_URL, DEFAULT_RAG_MODEL, generate_answer
from src.retrieval.context_builder import build_retrieval_context, format_context_for_prompt
from src.retrieval.milvus_search import DEFAULT_MODEL, DEFAULT_URI, execute_plan
from src.retrieval.query_planner import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL, PlannerOptions, plan_query
from src.retrieval.template_registry import TemplateRegistry

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_dependencies() -> tuple[Any, Any]:
    from pymilvus import MilvusClient
    from sentence_transformers import SentenceTransformer

    return MilvusClient, SentenceTransformer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--dataset", choices=DATASETS)
    parser.add_argument("--level")
    parser.add_argument("--component")
    parser.add_argument("--top-k", type=int, default=24)
    parser.add_argument("--template-k", type=int, default=8)
    parser.add_argument("--use-planner-llm", action="store_true")
    parser.add_argument("--planner-model", default=DEFAULT_LLM_MODEL)
    parser.add_argument("--planner-base-url", default=DEFAULT_LLM_BASE_URL)
    parser.add_argument("--uri", default=DEFAULT_URI)
    parser.add_argument("--embedding-model", default=DEFAULT_MODEL)
    parser.add_argument("--answer-model", default=DEFAULT_RAG_MODEL)
    parser.add_argument("--answer-base-url", default=DEFAULT_RAG_BASE_URL)
    parser.add_argument("--print-context", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = plan_query(
        args.query,
        PlannerOptions(
            dataset=args.dataset,
            level=args.level,
            component=args.component,
            top_k=args.top_k,
            use_llm=args.use_planner_llm,
            llm_model=args.planner_model,
            llm_base_url=args.planner_base_url,
        ),
    )
    milvus_client, sentence_transformer = load_dependencies()
    client = milvus_client(uri=args.uri)
    model = sentence_transformer(args.embedding_model) if plan.use_vector_search else None
    registry = TemplateRegistry.load(Path.cwd()) if plan.use_vector_search else None
    response = execute_plan(
        client=client,
        model=model,
        plan=plan,
        template_k=args.template_k,
        template_registry=registry,
    )
    context = build_retrieval_context(
        query=args.query,
        plan=plan,
        response=response,
        include_templates=True,
    )
    if args.print_context:
        print(format_context_for_prompt(context))
        print("\n---\n")
    print(
        generate_answer(
            context,
            model=args.answer_model,
            base_url=args.answer_base_url,
        )
    )


if __name__ == "__main__":
    main()
