"""Run evaluation queries against live production retrieval paths."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evaluation.io import JsonObject, read_jsonl, write_jsonl
from src.retrieval.milvus_models import RetrievalConfig, RetrievalResponse
from src.retrieval.milvus_search import DEFAULT_MODEL, DEFAULT_URI, execute_plan
from src.retrieval.query_planner import PlannerOptions, plan_query


@dataclass(frozen=True)
class LiveRetrievalOptions:
    queries_path: Path
    output_path: Path
    mode: str = "direct"
    experiment: str | None = None
    top_k: int = 24
    template_k: int = 8
    limit: int | None = None
    dataset: str | None = None
    level: str | None = None
    component: str | None = None
    base_url: str = "http://localhost:8000"
    endpoint: str = "/api/chat"
    timeout_seconds: float = 30.0
    milvus_uri: str = DEFAULT_URI
    embedding_model: str = DEFAULT_MODEL


@dataclass(frozen=True)
class DirectRetrievalDependencies:
    client: Any
    model: Any | None
    template_registry: Any | None
    pending_template_registry: Any | None
    plan_query_fn: Callable[[str, PlannerOptions], Any] = plan_query
    execute_plan_fn: Callable[..., RetrievalResponse] = execute_plan


def run_live_retrieval_evaluation(
    options: LiveRetrievalOptions,
    *,
    direct_dependencies: DirectRetrievalDependencies | None = None,
) -> int:
    validate_options(options)
    queries = list(read_jsonl(options.queries_path))
    if options.limit is not None:
        queries = queries[: options.limit]

    if options.mode == "direct":
        retriever: LiveRetriever = ProductionDirectRetriever(
            options,
            dependencies=direct_dependencies,
        )
    elif options.mode == "api":
        retriever = ProductionApiRetriever(options)
    else:
        raise ValueError(f"Unsupported live retrieval mode: {options.mode}")

    rows = [retriever.search(query) for query in queries]
    return write_jsonl(options.output_path, rows)


class LiveRetriever:
    def search(self, query: JsonObject) -> JsonObject:
        raise NotImplementedError


class ProductionDirectRetriever(LiveRetriever):
    def __init__(
        self,
        options: LiveRetrievalOptions,
        *,
        dependencies: DirectRetrievalDependencies | None = None,
    ) -> None:
        self.options = options
        self.dependencies = dependencies

    def search(self, query: JsonObject) -> JsonObject:
        deps = self.dependencies or load_direct_dependencies(self.options)
        query_text = query_text_from_row(query)
        started = time.perf_counter()
        plan = deps.plan_query_fn(
            query_text,
            PlannerOptions(
                dataset=filter_value(query, "dataset", self.options.dataset),
                level=filter_value(query, "level", self.options.level),
                component=filter_value(query, "component", self.options.component),
                top_k=self.options.top_k,
            ),
        )
        config = RetrievalConfig(
            template_k=self.options.template_k,
            final_top_k=self.options.top_k,
        )
        response = deps.execute_plan_fn(
            client=deps.client,
            model=deps.model if plan.use_vector_search else None,
            plan=plan,
            template_k=self.options.template_k,
            config=config,
            template_registry=deps.template_registry if plan.use_vector_search else None,
            pending_template_registry=(
                deps.pending_template_registry if plan.use_vector_search else None
            ),
        )
        latency_ms = (time.perf_counter() - started) * 1000
        return row_from_retrieval_response(
            query=query,
            experiment=self.options.experiment or "production_direct_v1",
            response=response,
            latency_ms=latency_ms,
            semantic_query=str(getattr(plan, "semantic_query", "")),
            vector_search=bool(getattr(plan, "use_vector_search", False)),
            template_filter_applied=bool(getattr(plan, "applied_template_filter", False)),
            fallback_used=bool(getattr(plan, "fallback_used", False)),
        )


class ProductionApiRetriever(LiveRetriever):
    def __init__(self, options: LiveRetrievalOptions) -> None:
        self.options = options

    def search(self, query: JsonObject) -> JsonObject:
        query_text = query_text_from_row(query)
        payload = {
            "query": query_text,
            "dataset": filter_value(query, "dataset", self.options.dataset),
            "service": filter_value(query, "service", self.options.component),
            "component": filter_value(query, "component", self.options.component),
            "level": filter_value(query, "level", self.options.level),
            "top_k": self.options.top_k,
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        started = time.perf_counter()
        response = send_json(
            build_url(self.options.base_url, self.options.endpoint),
            payload,
            timeout_seconds=self.options.timeout_seconds,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        records = extract_log_records(response)[: self.options.top_k]
        return row_from_log_records(
            query=query,
            experiment=self.options.experiment or "production_api_v1",
            records=records,
            latency_ms=latency_ms,
            raw_response_source=str(response.get("source") or ""),
        )


def load_direct_dependencies(options: LiveRetrievalOptions) -> DirectRetrievalDependencies:
    from app.chat_service import (
        get_embedding_model,
        get_milvus_client,
        get_pending_template_registry,
        get_template_registry,
    )

    return DirectRetrievalDependencies(
        client=get_milvus_client(options.milvus_uri),
        model=get_embedding_model(options.embedding_model),
        template_registry=get_template_registry(),
        pending_template_registry=get_pending_template_registry(),
    )


def row_from_retrieval_response(
    *,
    query: JsonObject,
    experiment: str,
    response: RetrievalResponse,
    latency_ms: float,
    semantic_query: str,
    vector_search: bool,
    template_filter_applied: bool,
    fallback_used: bool,
) -> JsonObject:
    records = [
        {
            "log_id": result.primary_id,
            "template_id": result.entity.get("template_id")
            or payload_value(result.entity, "template_id"),
            "score": result.score,
            "source": result.source,
        }
        for result in response.log_lines
    ]
    row = row_from_log_records(
        query=query,
        experiment=experiment,
        records=records,
        latency_ms=latency_ms,
    )
    row.update(
        {
            "retrieval_mode": response.mode,
            "filter_expr": response.filter_expr,
            "semantic_query": semantic_query,
            "vector_search": vector_search,
            "template_filter_applied": template_filter_applied,
            "fallback_used": fallback_used,
        }
    )
    return row


def row_from_log_records(
    *,
    query: JsonObject,
    experiment: str,
    records: Sequence[JsonObject],
    latency_ms: float,
    raw_response_source: str = "",
) -> JsonObject:
    template_ids = [str(record.get("template_id") or "") for record in records]
    retrieved_count = len(records)
    unique_template_count = len({template_id for template_id in template_ids if template_id})
    duplicate_template_ratio = (
        0.0 if retrieved_count == 0 else 1 - unique_template_count / retrieved_count
    )
    row: JsonObject = {
        "query_id": query.get("query_id"),
        "experiment": experiment,
        "retrieved_log_ids": [record.get("log_id") for record in records],
        "retrieved_template_ids": template_ids,
        "scores": [float(record.get("score") or 0.0) for record in records],
        "latency_ms": round(latency_ms, 3),
        "timings": {"live_retrieval_ms": round(latency_ms, 3)},
        "unique_template_count": unique_template_count,
        "duplicate_template_ratio": round(duplicate_template_ratio, 6),
    }
    if raw_response_source:
        row["raw_response_source"] = raw_response_source
    return row


def extract_log_records(payload: Any) -> list[JsonObject]:
    records: list[JsonObject] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return

        log_id = first_text(value, "log_id", "logId", "id", "primary_id")
        if log_id:
            records.append(
                {
                    "log_id": log_id,
                    "template_id": first_text(value, "template_id", "templateId"),
                    "score": first_number(value, "score", "semantic_score", "distance"),
                }
            )
            return

        for key, item in value.items():
            if key in {"logs", "log_lines", "results", "retrieved", "context", "data"}:
                visit(item)

    visit(payload)
    return records


def send_json(url: str, payload: JsonObject, *, timeout_seconds: float) -> JsonObject:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            value = json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc)) from exc
    if not isinstance(value, dict):
        raise RuntimeError("retrieval API response must be a JSON object")
    return value


def validate_options(options: LiveRetrievalOptions) -> None:
    if options.top_k < 1:
        raise ValueError("top_k must be positive")
    if options.template_k < 1:
        raise ValueError("template_k must be positive")
    if options.limit is not None and options.limit < 1:
        raise ValueError("limit must be positive when provided")
    if options.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")


def build_url(base_url: str, endpoint: str) -> str:
    return f"{base_url.rstrip('/')}/{endpoint.strip('/')}"


def query_text_from_row(query: JsonObject) -> str:
    text = str(query.get("query") or "").strip()
    if not text:
        raise ValueError(f"query text is required for query_id={query.get('query_id')}")
    return text


def filter_value(query: JsonObject, key: str, fallback: str | None) -> str | None:
    value = query.get(key)
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def payload_value(entity: JsonObject, key: str) -> Any:
    payload = entity.get("payload")
    if isinstance(payload, dict):
        return payload.get(key)
    return None


def first_text(value: JsonObject, *keys: str) -> str | None:
    for key in keys:
        raw = value.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            return text
    return None


def first_number(value: JsonObject, *keys: str) -> float:
    for key in keys:
        raw = value.get(key)
        if isinstance(raw, bool):
            continue
        if isinstance(raw, (int, float)):
            return float(raw)
    return 0.0
