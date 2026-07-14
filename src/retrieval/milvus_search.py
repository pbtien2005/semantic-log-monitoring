"""Adaptive Milvus retrieval over template registry and log-line collection."""

from __future__ import annotations

import math
import os
from typing import Any

import numpy as np

from src.retrieval.milvus_filters import (
    STRONG_ENTITY_FILTERS as STRONG_ENTITY_FILTERS,
    build_candidate_filter,
    build_candidate_filters,
    build_entity_filter,
    build_filter,
    build_log_payload_filter as build_log_payload_filter,
    build_template_filter,
    build_time_filter,
    combine_filters,
    has_strong_entity_filter as has_strong_entity_filter,
    quote_expr as quote_expr,
    should_apply_template_filter as should_apply_template_filter,
)
from src.retrieval.milvus_models import (
    RetrievalConfig as RetrievalConfig,
    RetrievalResponse as RetrievalResponse,
    RetrievalResult as RetrievalResult,
)
from src.retrieval.milvus_ranking import (
    cap_logs_per_template as cap_logs_per_template,
    is_temporal_sort as is_temporal_sort,
    merge_results as merge_results,
    normalize_semantic_score as normalize_semantic_score,
    occurrence_bonus as occurrence_bonus,
    rerank_and_cap_lines as rerank_and_cap_lines,
    rerank_template_child_lines as rerank_template_child_lines,
    rerank_template_group as rerank_template_group,
    rerank_templates as rerank_templates,
    result_payload_template_id as result_payload_template_id,
    result_timestamp_ms as result_timestamp_ms,
    source_boost as source_boost,
    template_group_key as template_group_key,
    template_score_map as template_score_map,
)
from src.retrieval.query_plan import RetrievalPlan
from src.retrieval.pending_template_registry import (
    PendingTemplateHit,
    PendingTemplateRecord,
    PendingTemplateRegistry,
)
from src.retrieval.template_registry import TemplateHit, TemplateRegistry


DEFAULT_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
LOG_LINE_COLLECTION = "log_line"
SEARCH_PARAMS = {"metric_type": "COSINE", "params": {}}

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
            "regex": hit.metadata.get("regex"),
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


def pending_hit_to_result(hit: PendingTemplateHit, *, query: str) -> RetrievalResult:
    result = RetrievalResult(
        collection="template",
        primary_id=hit.candidate_id,
        score=hit.score,
        semantic_score=hit.score,
        entity={
            "template_id": hit.candidate_id,
            "candidate_id": hit.candidate_id,
            "dataset": hit.dataset,
            "occurrences": hit.occurrences,
            "payload": {
                "template": hit.template,
                "draft_regex": hit.draft_regex,
                "status": hit.status,
                "searchable": hit.searchable,
                "source": "pending",
            },
        },
        source="pending_template_registry",
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


def pending_record_to_result(record: PendingTemplateRecord) -> RetrievalResult:
    return RetrievalResult(
        collection="template",
        primary_id=record.candidate_id,
        score=0.0,
        semantic_score=0.0,
        entity={
            "template_id": record.candidate_id,
            "candidate_id": record.candidate_id,
            "dataset": record.dataset,
            "occurrences": record.occurrences,
            "payload": {
                "template": record.template,
                "draft_regex": record.draft_regex,
                "status": record.status,
                "searchable": record.searchable,
                "source": "pending",
            },
        },
        source="pending_template_lookup",
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
    candidates: list[RetrievalResult],
    config: RetrievalConfig,
) -> list[RetrievalResult]:
    lines: list[RetrievalResult] = []
    for candidate in candidates:
        candidate_filter = (
            build_candidate_filter(candidate.primary_id)
            if candidate.source == "pending_template_registry"
            else build_template_filter([candidate.primary_id])
        )
        lines.extend(
            search_vector_lines(
                client,
                query_vector,
                filter_expr=combine_filters(base_filter, candidate_filter),
                top_k=config.candidate_per_template,
                source="candidate_filtered" if candidate.source == "pending_template_registry" else "template_filtered",
                group_by_field=None,
                group_size=None,
                strict_group_size=config.strict_group_size,
            )
        )
    return lines


def attach_template_candidates(
    plan: RetrievalPlan,
    template_registry: TemplateRegistry | None,
    pending_template_registry: PendingTemplateRegistry | None,
    query_vector: list[float],
    config: RetrievalConfig,
) -> list[RetrievalResult]:
    if template_registry is None and pending_template_registry is None:
        plan.candidate_template_ids = []
        plan.template_candidates = []
        return []

    template_hits = (
        template_registry.search(
            np.asarray(query_vector, dtype=np.float32),
            top_k=config.template_k,
            dataset=plan.dataset,
            level=plan.level,
            component=plan.component,
        )
        if template_registry is not None
        else []
    )
    pending_hits = (
        pending_template_registry.search(
            plan.semantic_query,
            top_k=config.template_k,
            dataset=plan.dataset,
            min_score=config.min_template_score,
        )
        if pending_template_registry is not None
        else []
    )
    templates = sorted(
        [
            *(template_hit_to_result(hit, query=plan.semantic_query) for hit in template_hits),
            *(pending_hit_to_result(hit, query=plan.semantic_query) for hit in pending_hits),
        ],
        key=lambda result: result.score,
        reverse=True,
    )[: config.template_k]
    plan.template_candidates = [
        {
            "template_id": template.primary_id,
            "score": template.score,
            "dataset": template.entity.get("dataset"),
            "level": template.entity.get("level"),
            "component": template.entity.get("component"),
            "source": template.source,
            "status": result_payload_status(template),
        }
        for template in templates
    ]
    eligible_templates = [
        template
        for template in templates
        if config.min_template_score is None or template.score >= config.min_template_score
    ]
    plan.candidate_template_ids = [
        template.primary_id
        for template in eligible_templates[: min(plan.max_template_ids_for_filter, config.max_template_ids_for_filter)]
    ]
    plan.applied_template_filter = should_apply_result_template_filter(
        templates,
        min_score=config.min_template_score,
        min_gap=config.min_template_score_gap,
    )
    return templates


def result_payload_status(result: RetrievalResult) -> str | None:
    payload = result.entity.get("payload")
    if isinstance(payload, dict):
        value = payload.get("status")
        return str(value) if value else None
    return None


def should_apply_result_template_filter(
    templates: list[RetrievalResult],
    *,
    min_score: float | None,
    min_gap: float,
) -> bool:
    if not templates:
        return False
    top_score = templates[0].score
    if min_score is not None and top_score < min_score:
        return False
    second_score = templates[1].score if len(templates) > 1 else 0.0
    return top_score - second_score >= min_gap


def enrich_templates_from_lines(
    lines: list[RetrievalResult],
    template_registry: TemplateRegistry | None,
    pending_template_registry: PendingTemplateRegistry | None,
    existing: list[RetrievalResult],
) -> list[RetrievalResult]:
    by_id = {template.primary_id: template for template in existing}
    template_ids = []
    candidate_ids = []
    for line in lines:
        template_id = str(line.entity.get("template_id") or result_payload_template_id(line) or "")
        candidate_id = str(result_payload_candidate_id(line) or "")
        if candidate_id and candidate_id not in by_id and candidate_id not in candidate_ids:
            candidate_ids.append(candidate_id)
        elif template_id and template_id not in by_id and template_id not in template_ids:
            template_ids.append(template_id)
    if template_registry is not None:
        for record in template_registry.get_many(template_ids):
            by_id[record.template_id] = template_record_to_result(record)
    if pending_template_registry is not None:
        for record in pending_template_registry.get_many(candidate_ids):
            by_id[record.candidate_id] = pending_record_to_result(record)
    return list(by_id.values())


def result_payload_candidate_id(result: RetrievalResult) -> str | None:
    payload = result.entity.get("payload")
    if isinstance(payload, dict):
        value = payload.get("candidate_id")
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
    pending_template_registry: PendingTemplateRegistry | None = None,
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
        templates = enrich_templates_from_lines(lines, template_registry, pending_template_registry, [])
        return RetrievalResponse("filtered_temporal", filter_expr, lines, templates)

    if model is None:
        raise ValueError("A sentence embedding model is required for vector retrieval plans.")

    query_vector = encode_query(model, plan.semantic_query)
    base_filter = filter_from_plan(plan)
    pending_template_registry = pending_template_registry.reload_if_changed() if pending_template_registry else None
    templates = attach_template_candidates(
        plan,
        template_registry,
        pending_template_registry,
        query_vector,
        retrieval_config,
    )

    selected_template_candidates: list[RetrievalResult] = []
    if plan.applied_template_filter and plan.candidate_template_ids:
        candidate_template_ids = set(plan.candidate_template_ids)
        selected_template_candidates = [
            template
            for template in templates
            if template.primary_id in candidate_template_ids
        ]
    template_filter = build_candidate_filters(selected_template_candidates)
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
            candidates=selected_template_candidates,
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

    templates = enrich_templates_from_lines(lines, template_registry, pending_template_registry, templates)
    return RetrievalResponse("filtered_vector", filter_expr, lines, templates)
