"""Build escaped Milvus filter expressions for retrieval plans."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from src.retrieval.query_entities import extract_query_entities
from src.retrieval.template_registry import TemplateHit


STRONG_ENTITY_FILTERS = {"request_id", "block_id", "instance_id", "uuid"}


class FilterCandidate(Protocol):
    primary_id: str
    source: str


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


def build_candidate_filter(candidate_id: str) -> str:
    return f"payload[\"candidate_id\"] == {quote_expr(candidate_id)}"


def build_candidate_filters(candidates: Sequence[FilterCandidate]) -> str:
    template_ids = [
        candidate.primary_id
        for candidate in candidates
        if candidate.source != "pending_template_registry"
    ]
    clauses = []
    if template_ids:
        clauses.append(build_template_filter(template_ids))
    clauses.extend(
        build_candidate_filter(candidate.primary_id)
        for candidate in candidates
        if candidate.source == "pending_template_registry"
    )
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0]
    return "(" + " or ".join(clauses) + ")"


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


def has_strong_entity_filter(entity_filters: dict[str, Any]) -> bool:
    return any(key in entity_filters for key in STRONG_ENTITY_FILTERS)


def should_apply_template_filter(
    template_hits: list[TemplateHit],
    *,
    min_score: float | None,
    min_gap: float,
    has_strong_entity: bool,
) -> bool:
    # Retained for the legacy API; strong entity filters never changed this score gate.
    _ = has_strong_entity
    if not template_hits:
        return False
    top_score = template_hits[0].score
    if min_score is not None and top_score < min_score:
        return False
    second_score = template_hits[1].score if len(template_hits) > 1 else 0.0
    return top_score - second_score >= min_gap
