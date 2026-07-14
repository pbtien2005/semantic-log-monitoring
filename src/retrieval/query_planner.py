"""Rule-first query normalization for retrieval planning."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.core.schema import DATASETS
from src.retrieval.query_entities import extract_query_entities
from src.retrieval.query_normalizer import NormalizedQuery, normalize_query
from src.retrieval.query_plan import AnswerMode, RetrievalPlan, SortSpec


LATEST_TERMS = (
    "mới nhất",
    "gần đây",
    "vừa xảy ra",
    "latest",
    "recent",
    "newest",
    "last logs",
)

LATEST_SEARCH_STOPWORDS = {
    "cho",
    "toi",
    "cac",
    "co",
    "day",
    "debug",
    "error",
    "errors",
    "gan",
    "gio",
    "hour",
    "hours",
    "info",
    "last",
    "latest",
    "liet",
    "log",
    "logs",
    "loi",
    "moi",
    "nhat",
    "recent",
    "show",
    "tim",
    "tieng",
    "trong",
    "warn",
    "warning",
}

SUMMARY_TERMS = (
    "summary",
    "summarize",
    "summarise",
    "overview",
    "recap",
    "tong hop",
    "tom tat",
)

ROOT_CAUSE_TERMS = (
    "root cause",
    "rca",
    "why",
    "debug",
    "diagnose",
    "diagnostic",
    "explain cause",
    "giai thich",
    "nguyen nhan",
    "vi sao",
    "tai sao",
)

SEARCH_LOG_TERMS = (
    "find",
    "search",
    "show",
    "list",
    "trace",
    "tim",
    "liet ke",
    "truy van",
)


@dataclass(slots=True)
class PlannerOptions:
    dataset: str | None = None
    level: str | None = None
    component: str | None = None
    top_k: int = 24
    # Backward-compatible no-op: query rewrite by LLM has been removed.
    use_llm: bool = False


def extract_dataset(query: NormalizedQuery, explicit_dataset: str | None) -> str | None:
    if explicit_dataset:
        return explicit_dataset
    for dataset in DATASETS:
        if dataset in query.lower_text:
            return dataset
    return None


def extract_level(query: NormalizedQuery, explicit_level: str | None) -> str | None:
    if explicit_level:
        return explicit_level
    upper = query.clean_text.upper()
    for level in ("CRITICAL", "ERROR", "WARN", "WARNING", "INFO", "NOTICE", "DEBUG"):
        if re.search(rf"\b{level}\b", upper):
            return "WARN" if level == "WARNING" else level
    return None


def extract_entities(query: NormalizedQuery) -> dict[str, str | int | float]:
    return dict(extract_query_entities(query).hard_filters)


def is_latest_query(query: str | NormalizedQuery) -> bool:
    normalized = normalize_query(query) if isinstance(query, str) else query
    latest_terms = (
        "moi nhat",
        "gan day",
        "vua xay ra",
        "latest",
        "recent",
        "newest",
        "last logs",
    )
    raw_lower = normalized.raw_text.casefold()
    return any(term in normalized.accentless_text for term in latest_terms) or any(
        term in raw_lower for term in LATEST_TERMS
    )


def is_summary_query(query: str | NormalizedQuery) -> bool:
    normalized = normalize_query(query) if isinstance(query, str) else query
    raw_lower = normalized.raw_text.casefold()
    return any(term in normalized.accentless_text for term in SUMMARY_TERMS) or any(
        term in raw_lower for term in SUMMARY_TERMS
    )


def has_any_query_term(query: NormalizedQuery, terms: tuple[str, ...]) -> bool:
    raw_lower = query.raw_text.casefold()
    return any(term in query.accentless_text for term in terms) or any(
        term in raw_lower for term in terms
    )


def infer_rule_answer_mode(query: NormalizedQuery, fallback: AnswerMode = "general") -> AnswerMode:
    if is_summary_query(query):
        return "summary"
    if has_any_query_term(query, ROOT_CAUSE_TERMS):
        return "root_cause"
    if has_any_query_term(query, SEARCH_LOG_TERMS):
        return "search_log"
    return fallback


def rule_time_spec(query: NormalizedQuery) -> dict[str, Any] | None:
    if is_latest_query(query):
        return {"type": "mode", "value": "latest"}
    return None


def has_diagnostic_search_terms(query: NormalizedQuery) -> bool:
    ignored = LATEST_SEARCH_STOPWORDS | set(DATASETS)
    ignored.update({"critical", "debug", "notice", "warning"})
    for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_.$-]*", query.accentless_text):
        lowered = token.lower()
        if len(lowered) < 3 or lowered in ignored:
            continue
        return True
    return False


def build_retrieval_plan(
    query: NormalizedQuery,
    options: PlannerOptions,
    *,
    semantic_query: str | None = None,
    answer_mode: AnswerMode = "general",
) -> RetrievalPlan:
    entities = extract_query_entities(query).hard_filters
    latest = is_latest_query(query)
    use_vector_search = not (latest and not entities and not has_diagnostic_search_terms(query))
    clean_semantic_query = semantic_query or query.clean_text
    rule_answer_mode = infer_rule_answer_mode(query, answer_mode)

    return RetrievalPlan(
        raw_query=query.raw_text,
        normalized_query=query.clean_text,
        semantic_query=clean_semantic_query,
        answer_mode=rule_answer_mode,
        dataset=extract_dataset(query, options.dataset),
        level=extract_level(query, options.level),
        component=options.component,
        entity_filters=entities,
        sort=SortSpec(field="timestamp_ms", order="desc") if latest else None,
        top_k=options.top_k,
        use_vector_search=use_vector_search,
    )


def fallback_semantic_plan(query: str, options: PlannerOptions) -> RetrievalPlan:
    normalized = normalize_query(query)
    return build_retrieval_plan(normalized, options, semantic_query=normalized.clean_text)


def plan_query(query: str, options: PlannerOptions) -> RetrievalPlan:
    normalized = normalize_query(query)
    return fallback_semantic_plan(normalized.clean_text, options)
