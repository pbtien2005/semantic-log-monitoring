"""Structured retrieval request schema."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.schema import DATASETS


SortField = Literal["timestamp_ms", "occurrences"]
SortOrder = Literal["asc", "desc"]
AnswerMode = Literal["root_cause", "search_log", "anomaly", "stats", "timeline", "general"]
FilterValue = str | int | float | bool | list[str] | list[int] | list[float]


class TimeRange(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start_ms: int | None = Field(default=None)
    end_ms: int | None = Field(default=None)


class SortSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: SortField
    order: SortOrder = "desc"


class RetrievalPlan(BaseModel):
    """A single fixed retrieval pipeline request.

    The plan deliberately has no routing strategy. Execution is determined by
    deterministic flags such as use_vector_search and sort.
    """

    model_config = ConfigDict(extra="ignore")

    raw_query: str = ""
    normalized_query: str = ""
    semantic_query: str = ""
    answer_mode: AnswerMode = "general"

    dataset: str | None = None
    level: str | None = None
    component: str | None = None
    entity_filters: dict[str, FilterValue] = Field(default_factory=dict)
    exact_phrases: list[str] = Field(default_factory=list)

    time_range: TimeRange | None = None
    sort: SortSpec | None = None

    candidate_template_ids: list[str] = Field(default_factory=list)
    template_candidates: list[dict[str, Any]] = Field(default_factory=list)

    top_k: int = Field(default=24, ge=1, le=50)
    vector_search_k: int = Field(default=50, ge=1, le=500)
    template_top_k: int = Field(default=8, ge=1, le=100)
    max_template_ids_for_filter: int = Field(default=20, ge=1, le=50)

    use_vector_search: bool = True
    applied_template_filter: bool = False
    fallback_used: bool = False

    @field_validator("dataset")
    @classmethod
    def validate_dataset_or_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        normalized = stripped.lower()
        return normalized if normalized in DATASETS else stripped

    @field_validator("level")
    @classmethod
    def normalize_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if normalized not in {"INFO", "WARN", "WARNING", "ERROR", "NOTICE", "DEBUG", "CRITICAL"}:
            raise ValueError("level must be a known log level or null")
        return "WARN" if normalized == "WARNING" else normalized

    @field_validator("component")
    @classmethod
    def clean_component(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("semantic_query", "raw_query", "normalized_query")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()
