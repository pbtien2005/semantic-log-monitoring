"""Shared data models for Milvus retrieval and ranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
