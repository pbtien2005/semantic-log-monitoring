"""Schema definitions and validation helpers for benchmark artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, TypeAlias


DatasetName: TypeAlias = Literal["apache", "openstack", "hdfs"]
LogDatasetName: TypeAlias = Literal["apache", "openstack", "hdfs", "online"]
Language: TypeAlias = Literal["vi", "en"]
QueryLevel: TypeAlias = Literal["easy", "medium", "hard"]
Category: TypeAlias = Literal[
    "timeout",
    "connection",
    "latency",
    "database",
    "permission",
    "storage",
    "network",
    "service_unavailable",
    "unknown",
]
Intent: TypeAlias = Literal[
    "log_retrieval",
    "incident_investigation",
    "status_overview",
]
LabelSource: TypeAlias = Literal[
    "keyword_rule",
    "template_rule",
    "manual_seed",
    "auto_candidate",
    "silver_auto_v2",
]

DATASETS: tuple[str, ...] = ("apache", "openstack", "hdfs")
LOG_DATASETS: tuple[str, ...] = (*DATASETS, "online")
LANGUAGES: tuple[str, ...] = ("vi", "en")
QUERY_LEVELS: tuple[str, ...] = ("easy", "medium", "hard")
CATEGORIES: tuple[str, ...] = (
    "timeout",
    "connection",
    "latency",
    "database",
    "permission",
    "storage",
    "network",
    "service_unavailable",
    "unknown",
)
INTENTS: tuple[str, ...] = (
    "log_retrieval",
    "incident_investigation",
    "status_overview",
)
LABEL_SOURCES: tuple[str, ...] = (
    "keyword_rule",
    "template_rule",
    "manual_seed",
    "auto_candidate",
    "silver_auto_v2",
)


@dataclass(slots=True)
class LogRecord:
    log_id: str
    dataset: DatasetName
    raw_log: str
    message: str
    timestamp: str | None
    component: str | None
    level: str | None
    event_id: str | None
    source_file: str
    line_number: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QueryFilters:
    component: str | None = None
    level: str | None = None
    time_range: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QueryRecord:
    query_id: str
    dataset: DatasetName
    query: str
    language: Language
    query_level: QueryLevel
    category: Category
    intent: Intent
    filters: QueryFilters = field(default_factory=QueryFilters)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["filters"] = self.filters.to_dict()
        return data


@dataclass(slots=True)
class QrelRecord:
    query_id: str
    positive_log_ids: list[str]
    hard_negative_log_ids: list[str]
    label_source: LabelSource
    needs_review: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PairRecord:
    query_id: str
    query: str
    positive_log: str
    negative_log: str
    positive_log_id: str
    negative_log_id: str
    dataset: DatasetName
    category: Category
    query_level: QueryLevel
    label_quality: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SchemaValidationError(ValueError):
    """Raised when a benchmark JSONL row violates the expected schema."""


def validate_dataset(dataset: str) -> DatasetName:
    if dataset not in DATASETS:
        raise SchemaValidationError(
            f"Unknown dataset '{dataset}'. Expected one of: {', '.join(DATASETS)}"
        )
    return dataset  # type: ignore[return-value]


def validate_log_dataset(dataset: str) -> LogDatasetName:
    cleaned = dataset.strip()
    if not cleaned:
        raise SchemaValidationError("dataset is required")
    return cleaned  # type: ignore[return-value]


def _require_keys(record: dict[str, Any], required_keys: set[str], name: str) -> None:
    missing = required_keys - set(record)
    if missing:
        raise SchemaValidationError(f"{name} is missing keys: {sorted(missing)}")


def _ensure_string_or_none(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise SchemaValidationError(f"{field_name} must be a string or null")


def validate_log_record(record: dict[str, Any]) -> None:
    _require_keys(
        record,
        {
            "log_id",
            "dataset",
            "raw_log",
            "message",
            "timestamp",
            "component",
            "level",
            "event_id",
            "source_file",
            "line_number",
        },
        "logs.jsonl row",
    )
    validate_dataset(str(record["dataset"]))
    for key in ("log_id", "raw_log", "message", "source_file"):
        if not isinstance(record[key], str) or not record[key]:
            raise SchemaValidationError(f"{key} must be a non-empty string")
    for key in ("timestamp", "component", "level", "event_id"):
        _ensure_string_or_none(record[key], key)
    if not isinstance(record["line_number"], int) or record["line_number"] < 1:
        raise SchemaValidationError("line_number must be a positive integer")


def validate_query_record(record: dict[str, Any]) -> None:
    _require_keys(
        record,
        {
            "query_id",
            "dataset",
            "query",
            "language",
            "query_level",
            "category",
            "intent",
            "filters",
        },
        "queries.jsonl row",
    )
    validate_dataset(str(record["dataset"]))
    if record["language"] not in LANGUAGES:
        raise SchemaValidationError("language must be 'vi' or 'en'")
    if record["query_level"] not in QUERY_LEVELS:
        raise SchemaValidationError("query_level must be easy, medium, or hard")
    if record["category"] not in CATEGORIES:
        raise SchemaValidationError(f"category must be one of {CATEGORIES}")
    if record["intent"] not in INTENTS:
        raise SchemaValidationError(f"intent must be one of {INTENTS}")
    if not isinstance(record["query_id"], str) or not record["query_id"]:
        raise SchemaValidationError("query_id must be a non-empty string")
    if not isinstance(record["query"], str) or not record["query"].strip():
        raise SchemaValidationError("query must be a non-empty string")
    filters = record["filters"]
    if not isinstance(filters, dict):
        raise SchemaValidationError("filters must be an object")
    _require_keys(filters, {"component", "level", "time_range"}, "filters")
    for key in ("component", "level", "time_range"):
        _ensure_string_or_none(filters[key], f"filters.{key}")


def validate_qrel_record(record: dict[str, Any]) -> None:
    _require_keys(
        record,
        {
            "query_id",
            "positive_log_ids",
            "hard_negative_log_ids",
            "label_source",
            "needs_review",
        },
        "qrels.jsonl row",
    )
    if not isinstance(record["query_id"], str) or not record["query_id"]:
        raise SchemaValidationError("query_id must be a non-empty string")
    for key in ("positive_log_ids", "hard_negative_log_ids"):
        if not isinstance(record[key], list) or not all(
            isinstance(item, str) and item for item in record[key]
        ):
            raise SchemaValidationError(f"{key} must be a list of non-empty strings")
    if record["label_source"] not in LABEL_SOURCES:
        raise SchemaValidationError(f"label_source must be one of {LABEL_SOURCES}")
    if not isinstance(record["needs_review"], bool):
        raise SchemaValidationError("needs_review must be a boolean")


def validate_pair_record(record: dict[str, Any]) -> None:
    _require_keys(
        record,
        {
            "query_id",
            "query",
            "positive_log",
            "negative_log",
            "positive_log_id",
            "negative_log_id",
            "dataset",
            "category",
            "query_level",
            "label_quality",
        },
        "pairs.jsonl row",
    )
    validate_dataset(str(record["dataset"]))
    if record["category"] not in CATEGORIES:
        raise SchemaValidationError(f"category must be one of {CATEGORIES}")
    if record["query_level"] not in QUERY_LEVELS:
        raise SchemaValidationError("query_level must be easy, medium, or hard")
    if record["label_quality"] != "silver":
        raise SchemaValidationError("label_quality must be 'silver'")
    for key in (
        "query_id",
        "query",
        "positive_log",
        "negative_log",
        "positive_log_id",
        "negative_log_id",
    ):
        if not isinstance(record[key], str) or not record[key]:
            raise SchemaValidationError(f"{key} must be a non-empty string")
