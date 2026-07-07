"""Adaptive Milvus retrieval over template registry and log-line collection."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any

import numpy as np

from src.retrieval.query_entities import extract_query_entities
from src.retrieval.query_plan import RetrievalPlan
from src.retrieval.template_registry import TemplateHit, TemplateRegistry


DEFAULT_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
LOG_LINE_COLLECTION = "log_line"
SEARCH_PARAMS = {"metric_type": "COSINE", "params": {}}

@dataclass(slots=True)
class RetrievalResult:
    collection: str
    primary_id: str
    score: float
    semantic_score: float
    entity: dict[str, Any]
    source: str


@dataclass(slots=True)
class RetrievalResponse:
    mode: str
    filter_expr: str
    log_lines: list[RetrievalResult]
    templates: list[RetrievalResult]


@dataclass(slots=True)
class RetrievalConfig:
    template_k: int = 8
    candidate_per_template: int = 10
    logs_per_template: int = 3
    final_top_k: int = 24
    group_by_field: str | None = "template_id"
    strict_group_size: bool = False
    max_template_ids_for_filter: int = 20
    min_template_score: float | None = None
    min_template_score_gap: float = 0.0
    min_results_with_template_filter: int = 2
    vector_search_k: int = 50
    template_child_multiplier: int = 3
    template_first_direct_min: int = 2
    template_first_direct_ratio: float = 0.5
    child_line_weight: float = 0.65
    parent_template_weight: float = 0.35
    semantic_weight: float = 0.85
    recency_weight: float = 0.15
    enable_recency_rerank: bool = True
    per_template_search: bool = True
    temporal_query_limit: int = 10000


def quote_expr(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_filter(
    *,
    dataset: str | None = None,
    level: str | None = None,
    component: str | None = None,
    template_ids: list[str] | None = None,
) -> str:
    clauses = []
    if dataset:
        clauses.append(f"dataset == {quote_expr(dataset)}")
    if level:
        clauses.append(f"level == {quote_expr(level)}")
    if component:
        clauses.append(f"component == {quote_expr(component)}")
    if template_ids:
        quoted = ", ".join(quote_expr(template_id) for template_id in template_ids)
        clauses.append(f"template_id in [{quoted}]")
    return " and ".join(clauses)


def build_template_filter(template_ids: list[str]) -> str:
    return build_filter(template_ids=template_ids)


def build_log_payload_filter(query: str) -> str:
    return build_entity_filter(extract_query_entities(query).hard_filters)


def build_entity_filter(entity_filters: dict[str, str | int | float]) -> str:
    clauses = []
    for name, value in entity_filters.items():
        if isinstance(value, str):
            clauses.append(f"payload[\"{name}\"] == {quote_expr(value)}")
        else:
            clauses.append(f"payload[\"{name}\"] == {value}")
    return " and ".join(clauses)


def build_time_filter(start_ms: int | None, end_ms: int | None) -> str:
    clauses = []
    if start_ms is not None:
        clauses.append(f"timestamp_ms >= {start_ms}")
    if end_ms is not None:
        clauses.append(f"timestamp_ms <= {end_ms}")
    return " and ".join(clauses)


def combine_filters(*filters: str) -> str:
    return " and ".join(filter_expr for filter_expr in filters if filter_expr)


STRONG_ENTITY_FILTERS = {"request_id", "block_id", "instance_id", "uuid"}


def has_strong_entity_filter(entity_filters: dict[str, Any]) -> bool:
    return any(key in entity_filters for key in STRONG_ENTITY_FILTERS)


def should_apply_template_filter(
    template_hits: list[TemplateHit],
    *,
    min_score: float | None,
    min_gap: float,
    has_strong_entity: bool,
) -> bool:
    if not template_hits:
        return False
    top_score = template_hits[0].score
    if min_score is not None and top_score < min_score:
        return False
    second_score = template_hits[1].score if len(template_hits) > 1 else 0.0
    return top_score - second_score >= min_gap


def encode_query(model: Any, query: str) -> list[float]:
    vector = model.encode(
        [f"query: {query}"],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]
    return vector.tolist()


def search_collection(
    client: Any,
    collection_name: str,
    query_vector: list[float],
    *,
    filter_expr: str,
    top_k: int,
    group_by_field: str | None = None,
    group_size: int | None = None,
    strict_group_size: bool = False,
) -> list[dict[str, Any]]:
    output_fields = ["dataset", "level", "component", "payload"]
    if collection_name != LOG_LINE_COLLECTION:
        raise ValueError(f"Unsupported Milvus collection: {collection_name}")
    output_fields[:0] = ["log_id", "template_id", "timestamp_ms"]

    search_kwargs = {
        "collection_name": collection_name,
        "data": [query_vector],
        "anns_field": "vector",
        "filter": filter_expr,
        "limit": top_k,
        "output_fields": output_fields,
        "search_params": SEARCH_PARAMS,
    }
    if group_by_field and group_size and group_size > 0:
        search_kwargs.update(
            {
                "group_by_field": group_by_field,
                "group_size": group_size,
                "strict_group_size": strict_group_size,
            }
        )
    results = client.search(**search_kwargs)
    return results[0] if results else []


def query_log_lines(
    client: Any,
    *,
    filter_expr: str,
    limit: int,
) -> list[dict[str, Any]]:
    rows = client.query(
        collection_name=LOG_LINE_COLLECTION,
        filter=filter_expr,
        output_fields=[
            "log_id",
            "dataset",
            "template_id",
            "level",
            "component",
            "timestamp_ms",
            "payload",
        ],
        limit=limit,
    )
    return [dict(row) for row in rows]


def to_result(collection_name: str, hit: dict[str, Any], *, source: str, score: float | None = None) -> RetrievalResult:
    entity = hit.get("entity", {})
    primary_id = entity.get("log_id") or entity.get("template_id") or ""
    semantic_score = float(hit.get("distance", 0.0))
    return RetrievalResult(
        collection=collection_name,
        primary_id=str(primary_id),
        score=semantic_score if score is None else score,
        semantic_score=semantic_score,
        entity=entity,
        source=source,
    )


def template_hit_to_result(hit: TemplateHit, *, query: str) -> RetrievalResult:
    entity = {
        "template_id": hit.template_id,
        "dataset": hit.dataset,
        "level": hit.level,
        "component": hit.component,
        "occurrences": hit.occurrences,
        "payload": {
            "template": hit.template,
            "embed_text": hit.search_text,
            "signals": hit.signals,
            "intent": hit.metadata.get("intent"),
            "regex": hit.metadata.get("regex"),
            "event_type": hit.metadata.get("event_type"),
            "event_family": hit.metadata.get("event_family"),
            "sample_messages": hit.sample_messages,
            "filter_mode": hit.filter_mode,
        },
    }
    result = RetrievalResult(
        collection="template",
        primary_id=hit.template_id,
        score=hit.score,
        semantic_score=hit.score,
        entity=entity,
        source="template_registry",
    )
    return rerank_templates([result], query)[0]


def template_record_to_result(record: Any) -> RetrievalResult:
    entity = {
        "template_id": record.template_id,
        "dataset": record.dataset,
        "level": record.level,
        "component": record.component,
        "occurrences": record.occurrences,
        "payload": {
            "template": record.template,
            "embed_text": record.search_text,
            "signals": record.signals,
            "sample_messages": record.sample_messages,
            **record.metadata,
        },
    }
    return RetrievalResult(
        collection="template",
        primary_id=record.template_id,
        score=0.0,
        semantic_score=0.0,
        entity=entity,
        source="template_lookup",
    )


def row_to_result(collection_name: str, row: dict[str, Any], *, source: str) -> RetrievalResult:
    primary_id = row.get("log_id") or row.get("template_id") or ""
    return RetrievalResult(
        collection=collection_name,
        primary_id=str(primary_id),
        score=0.0,
        semantic_score=0.0,
        entity=row,
        source=source,
    )


def occurrence_bonus(template_result: RetrievalResult, query: str) -> float:
    occurrences = int(template_result.entity.get("occurrences") or 0)
    if occurrences <= 0:
        return 0.0
    scaled = min(math.log1p(occurrences) / 10.0, 0.08)
    lowered = query.lower()
    if any(term in lowered for term in ("hiếm", "bất thường", "rare", "anomaly", "outlier")):
        return -scaled
    return scaled


def rerank_templates(templates: list[RetrievalResult], query: str) -> list[RetrievalResult]:
    reranked = []
    for template in templates:
        bonus = occurrence_bonus(template, query)
        reranked.append(
            RetrievalResult(
                collection=template.collection,
                primary_id=template.primary_id,
                score=template.semantic_score + bonus,
                semantic_score=template.semantic_score,
                entity=template.entity,
                source=template.source,
            )
        )
    return sorted(reranked, key=lambda item: item.score, reverse=True)


def template_score_map(templates: list[RetrievalResult]) -> dict[str, float]:
    return {template.primary_id: template.score for template in templates}


def rerank_template_child_lines(
    lines: list[RetrievalResult],
    templates: list[RetrievalResult],
    *,
    line_weight: float = 0.65,
    template_weight: float = 0.35,
) -> list[RetrievalResult]:
    scores = template_score_map(templates)
    reranked = []
    for line in lines:
        template_id = str(line.entity.get("template_id") or "")
        parent_score = scores.get(template_id, line.semantic_score)
        final_score = line_weight * line.semantic_score + template_weight * parent_score
        reranked.append(
            RetrievalResult(
                collection=line.collection,
                primary_id=line.primary_id,
                score=final_score,
                semantic_score=line.semantic_score,
                entity=line.entity,
                source=line.source,
            )
        )
    return sorted(reranked, key=lambda item: item.score, reverse=True)


def merge_results(*groups: list[RetrievalResult], limit: int) -> list[RetrievalResult]:
    merged: dict[str, RetrievalResult] = {}
    for group in groups:
        for item in group:
            current = merged.get(item.primary_id)
            if current is None or item.score > current.score:
                merged[item.primary_id] = item
    return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:limit]


def cap_logs_per_template(
    lines: list[RetrievalResult],
    *,
    logs_per_template: int,
    limit: int,
) -> list[RetrievalResult]:
    if logs_per_template < 1:
        return lines[:limit]
    counts: dict[str, int] = {}
    capped: list[RetrievalResult] = []
    for line in lines:
        template_id = str(line.entity.get("template_id") or result_payload_template_id(line) or "")
        group_key = template_id or line.primary_id
        current = counts.get(group_key, 0)
        if current >= logs_per_template:
            continue
        counts[group_key] = current + 1
        capped.append(line)
        if len(capped) >= limit:
            break
    return capped


def result_timestamp_ms(result: RetrievalResult) -> int | None:
    value = result.entity.get("timestamp_ms")
    if value is None:
        payload = result.entity.get("payload")
        if isinstance(payload, dict):
            value = payload.get("timestamp_ms")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_semantic_score(score: float) -> float:
    if math.isnan(score):
        return 0.0
    return max(0.0, min(1.0, score))


def template_group_key(line: RetrievalResult) -> str:
    return str(line.entity.get("template_id") or result_payload_template_id(line) or line.primary_id)


def is_temporal_sort(plan: RetrievalPlan) -> bool:
    return plan.sort is not None and plan.sort.field == "timestamp_ms"


def rerank_template_group(
    lines: list[RetrievalResult],
    *,
    plan: RetrievalPlan,
    config: RetrievalConfig,
) -> list[RetrievalResult]:
    if not lines:
        return []

    if is_temporal_sort(plan):
        reverse = plan.sort is None or plan.sort.order == "desc"
        return sorted(
            lines,
            key=lambda line: result_timestamp_ms(line) if result_timestamp_ms(line) is not None else -1,
            reverse=reverse,
        )

    if not config.enable_recency_rerank or config.recency_weight <= 0:
        return sorted(lines, key=lambda line: line.score, reverse=True)

    timestamps = [timestamp for line in lines if (timestamp := result_timestamp_ms(line)) is not None]
    min_timestamp = min(timestamps) if timestamps else None
    max_timestamp = max(timestamps) if timestamps else None
    timestamp_span = (
        max_timestamp - min_timestamp
        if min_timestamp is not None and max_timestamp is not None
        else 0
    )

    weighted: list[RetrievalResult] = []
    total_weight = config.semantic_weight + config.recency_weight
    semantic_weight = config.semantic_weight / total_weight if total_weight > 0 else 1.0
    recency_weight = config.recency_weight / total_weight if total_weight > 0 else 0.0
    for line in lines:
        semantic_score = normalize_semantic_score(line.semantic_score)
        timestamp = result_timestamp_ms(line)
        recency_score = (
            (timestamp - min_timestamp) / timestamp_span
            if timestamp is not None
            and min_timestamp is not None
            and timestamp_span > 0
            else 0.0
        )
        final_score = semantic_weight * semantic_score + recency_weight * recency_score
        weighted.append(
            RetrievalResult(
                collection=line.collection,
                primary_id=line.primary_id,
                score=final_score,
                semantic_score=line.semantic_score,
                entity=line.entity,
                source=line.source,
            )
        )
    return sorted(
        weighted,
        key=lambda line: (
            line.score,
            result_timestamp_ms(line) if result_timestamp_ms(line) is not None else -1,
            line.semantic_score,
        ),
        reverse=True,
    )


def rerank_and_cap_lines(
    lines: list[RetrievalResult],
    *,
    plan: RetrievalPlan,
    config: RetrievalConfig,
    limit: int,
) -> list[RetrievalResult]:
    grouped: dict[str, list[RetrievalResult]] = {}
    for line in lines:
        grouped.setdefault(template_group_key(line), []).append(line)

    selected: list[RetrievalResult] = []
    for group in grouped.values():
        selected.extend(
            rerank_template_group(group, plan=plan, config=config)[: config.logs_per_template]
        )

    if is_temporal_sort(plan):
        reverse = plan.sort is None or plan.sort.order == "desc"
        selected.sort(
            key=lambda line: result_timestamp_ms(line) if result_timestamp_ms(line) is not None else -1,
            reverse=reverse,
        )
    else:
        selected.sort(key=lambda line: line.score, reverse=True)
    return selected[:limit]


def filter_from_plan(plan: RetrievalPlan, *, include_entities: bool = True) -> str:
    time_filter = ""
    if plan.time_range is not None:
        time_filter = build_time_filter(plan.time_range.start_ms, plan.time_range.end_ms)
    return combine_filters(
        build_filter(dataset=plan.dataset, level=plan.level, component=plan.component),
        build_entity_filter(plan.entity_filters) if include_entities else "",
        time_filter,
    )


def search_vector_lines(
    client: Any,
    query_vector: list[float],
    *,
    filter_expr: str,
    top_k: int,
    source: str,
    group_by_field: str | None = None,
    group_size: int | None = None,
    strict_group_size: bool = False,
) -> list[RetrievalResult]:
    hits = search_collection(
        client,
        LOG_LINE_COLLECTION,
        query_vector,
        filter_expr=filter_expr,
        top_k=top_k,
        group_by_field=group_by_field,
        group_size=group_size,
        strict_group_size=strict_group_size,
    )
    return [to_result(LOG_LINE_COLLECTION, hit, source=source) for hit in hits]


def search_template_candidate_lines(
    client: Any,
    query_vector: list[float],
    *,
    base_filter: str,
    template_ids: list[str],
    config: RetrievalConfig,
) -> list[RetrievalResult]:
    lines: list[RetrievalResult] = []
    for template_id in template_ids:
        lines.extend(
            search_vector_lines(
                client,
                query_vector,
                filter_expr=combine_filters(base_filter, build_template_filter([template_id])),
                top_k=config.candidate_per_template,
                source="template_filtered",
                group_by_field=None,
                group_size=None,
                strict_group_size=config.strict_group_size,
            )
        )
    return lines


def attach_template_candidates(
    plan: RetrievalPlan,
    template_registry: TemplateRegistry | None,
    query_vector: list[float],
    config: RetrievalConfig,
) -> list[RetrievalResult]:
    if template_registry is None:
        plan.candidate_template_ids = []
        plan.template_candidates = []
        return []

    template_hits = template_registry.search(
        np.asarray(query_vector, dtype=np.float32),
        top_k=config.template_k,
        dataset=plan.dataset,
        level=plan.level,
        component=plan.component,
    )
    templates = [template_hit_to_result(hit, query=plan.semantic_query) for hit in template_hits]
    plan.template_candidates = [
        {
            "template_id": hit.template_id,
            "score": hit.score,
            "dataset": hit.dataset,
            "level": hit.level,
            "component": hit.component,
            "filter_mode": hit.filter_mode,
        }
        for hit in template_hits
    ]
    eligible_hits = [
        hit
        for hit in template_hits
        if config.min_template_score is None or hit.score >= config.min_template_score
    ]
    plan.candidate_template_ids = [
        hit.template_id
        for hit in eligible_hits[: min(plan.max_template_ids_for_filter, config.max_template_ids_for_filter)]
    ]
    plan.applied_template_filter = should_apply_template_filter(
        template_hits,
        min_score=config.min_template_score,
        min_gap=config.min_template_score_gap,
        has_strong_entity=has_strong_entity_filter(plan.entity_filters),
    )
    return templates


def enrich_templates_from_lines(
    lines: list[RetrievalResult],
    template_registry: TemplateRegistry | None,
    existing: list[RetrievalResult],
) -> list[RetrievalResult]:
    by_id = {template.primary_id: template for template in existing}
    if template_registry is None:
        return list(by_id.values())
    template_ids = []
    for line in lines:
        template_id = str(line.entity.get("template_id") or result_payload_template_id(line) or "")
        if template_id and template_id not in by_id and template_id not in template_ids:
            template_ids.append(template_id)
    for record in template_registry.get_many(template_ids):
        by_id[record.template_id] = template_record_to_result(record)
    return list(by_id.values())


def result_payload_template_id(result: RetrievalResult) -> str | None:
    payload = result.entity.get("payload")
    if isinstance(payload, dict):
        value = payload.get("template_id")
        return str(value) if value else None
    return None


def execute_plan(
    *,
    client: Any,
    model: Any | None,
    plan: RetrievalPlan,
    template_k: int = 8,
    config: RetrievalConfig | None = None,
    template_registry: TemplateRegistry | None = None,
) -> RetrievalResponse:
    retrieval_config = config or RetrievalConfig(template_k=template_k)
    final_limit = min(plan.top_k, retrieval_config.final_top_k)
    if not plan.use_vector_search:
        filter_expr = filter_from_plan(plan)
        rows = query_log_lines(
            client,
            filter_expr=filter_expr,
            limit=retrieval_config.temporal_query_limit,
        )
        reverse = plan.sort is None or plan.sort.order == "desc"
        sort_field = plan.sort.field if plan.sort else "timestamp_ms"
        rows.sort(key=lambda row: row.get(sort_field) or -1, reverse=reverse)
        lines = [
            row_to_result(LOG_LINE_COLLECTION, row, source="temporal")
            for row in rows[:final_limit]
        ]
        templates = enrich_templates_from_lines(lines, template_registry, [])
        return RetrievalResponse("filtered_temporal", filter_expr, lines, templates)

    if model is None:
        raise ValueError("A sentence embedding model is required for vector retrieval plans.")

    query_vector = encode_query(model, plan.semantic_query)
    base_filter = filter_from_plan(plan)
    templates = attach_template_candidates(plan, template_registry, query_vector, retrieval_config)

    template_filter = (
        build_template_filter(plan.candidate_template_ids)
        if plan.applied_template_filter and plan.candidate_template_ids
        else ""
    )
    filter_expr = combine_filters(base_filter, template_filter)
    search_k = max(final_limit, plan.vector_search_k or retrieval_config.vector_search_k)
    candidate_group_size = max(retrieval_config.candidate_per_template, retrieval_config.logs_per_template)
    grouped_search_k = (
        max(1, math.ceil(final_limit / retrieval_config.logs_per_template))
        if retrieval_config.group_by_field and candidate_group_size > 0
        else search_k
    )
    if template_filter and retrieval_config.per_template_search:
        primary_candidates = search_template_candidate_lines(
            client,
            query_vector,
            base_filter=base_filter,
            template_ids=plan.candidate_template_ids,
            config=retrieval_config,
        )
    else:
        primary_candidates = search_vector_lines(
            client,
            query_vector,
            filter_expr=filter_expr,
            top_k=grouped_search_k,
            source="template_filtered" if template_filter else "vector",
            group_by_field=retrieval_config.group_by_field,
            group_size=candidate_group_size,
            strict_group_size=retrieval_config.strict_group_size,
        )
    lines = rerank_and_cap_lines(
        primary_candidates,
        plan=plan,
        config=retrieval_config,
        limit=final_limit,
    )

    if template_filter and len(lines) < retrieval_config.min_results_with_template_filter:
        plan.fallback_used = True
        fallback_lines = search_vector_lines(
            client,
            query_vector,
            filter_expr=base_filter,
            top_k=grouped_search_k,
            source="vector_fallback",
            group_by_field=retrieval_config.group_by_field,
            group_size=candidate_group_size,
            strict_group_size=retrieval_config.strict_group_size,
        )
        merged = merge_results(primary_candidates, fallback_lines, limit=search_k)
        lines = rerank_and_cap_lines(
            merged,
            plan=plan,
            config=retrieval_config,
            limit=final_limit,
        )
    else:
        plan.fallback_used = False

    templates = enrich_templates_from_lines(lines, template_registry, templates)
    return RetrievalResponse("filtered_vector", filter_expr, lines, templates)
