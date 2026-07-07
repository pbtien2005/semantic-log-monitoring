"""Kafka message contract for online log ingestion."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha1
from typing import Any

from src.core.schema import validate_log_dataset
from src.core.text_utils import infer_level, infer_timestamp, normalize_message


DEFAULT_RAW_TOPIC = "logs.raw"
DEFAULT_FAILED_TOPIC = "logs.failed"
DEFAULT_CONSUMER_GROUP = "semantic-ingestion"
MAX_RAW_LOG_LENGTH = 20000
SCHEMA_VERSION = 1
PARSER_VERSION = 1

APACHE_BRACKET_RE = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+\[(?P<level>[^\]]+)\]\s*(?P<message>.*)$"
)
OPENSTACK_RE = re.compile(
    r"^(?:(?P<source_file>\S+\.log(?:\.\S+)?)\s+)?"
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)"
    r"\s+(?P<pid>\d+)\s+(?P<level>[A-Z]+)\s+"
    r"(?P<component>[A-Za-z0-9_.$-]+)\s*(?P<message>.*)$"
)
HDFS_RE = re.compile(
    r"^(?P<timestamp>\d{6}\s+\d{6})\s+(?P<pid>\d+)\s+"
    r"(?P<level>[A-Z]+)\s+(?P<component>[^:\s]+):\s*(?P<message>.*)$"
)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_raw_log(payload: dict[str, Any]) -> str:
    raw_log = _optional_text(payload.get("raw_log") or payload.get("message") or payload.get("log"))
    if not raw_log:
        raise ValueError("raw_log is required")
    normalized = normalize_message(raw_log)
    if len(normalized) > MAX_RAW_LOG_LENGTH:
        raise ValueError(f"raw_log must be at most {MAX_RAW_LOG_LENGTH} characters")
    return normalized


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = _optional_text(payload.get(key))
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _clean_level(level: str | None) -> str | None:
    if level is None:
        return None
    cleaned = level.strip().strip("[]").upper()
    return "WARN" if cleaned == "WARNING" else cleaned or None


def _parse_raw_log(dataset: str, raw_log: str) -> dict[str, str | None]:
    if dataset == "apache":
        match = APACHE_BRACKET_RE.match(raw_log)
        if match:
            return {
                "message": normalize_message(match.group("message") or raw_log),
                "timestamp": _optional_text(match.group("timestamp")),
                "level": _clean_level(match.group("level")),
                "component": None,
                "source_file": None,
            }
    elif dataset == "openstack":
        match = OPENSTACK_RE.match(raw_log)
        if match:
            return {
                "message": normalize_message(match.group("message") or raw_log),
                "timestamp": _optional_text(match.group("timestamp")),
                "level": _clean_level(match.group("level")),
                "component": _optional_text(match.group("component")),
                "source_file": _optional_text(match.group("source_file")),
            }
    elif dataset == "hdfs":
        match = HDFS_RE.match(raw_log)
        if match:
            return {
                "message": normalize_message(match.group("message") or raw_log),
                "timestamp": _optional_text(match.group("timestamp")),
                "level": _clean_level(match.group("level")),
                "component": _optional_text(match.group("component")),
                "source_file": None,
            }

    return {
        "message": raw_log,
        "timestamp": infer_timestamp(raw_log),
        "level": infer_level(raw_log),
        "component": None,
        "source_file": None,
    }


def partition_key_for_log(payload: dict[str, Any]) -> str:
    for key in ("trace_id", "request_id", "component", "service", "source_id", "source"):
        value = _optional_text(payload.get(key))
        if value:
            return value
    return "unknown"


def stable_ingest_log_id(payload: dict[str, Any]) -> str:
    dataset = validate_log_dataset(_required_text(payload, "dataset"))
    source_id = _required_text(payload, "source_id")
    raw_log = _required_raw_log(payload)
    parts = (
        dataset,
        source_id,
        _optional_text(payload.get("source")) or "",
        _optional_text(payload.get("service")) or "",
        _optional_text(payload.get("component")) or "",
        _optional_text(payload.get("timestamp")) or "",
        raw_log,
    )
    digest = sha1("\n".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{dataset}:{digest}"


def normalize_raw_log_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_log = _required_raw_log(payload)
    dataset = validate_log_dataset(_required_text(payload, "dataset"))
    source_id = _required_text(payload, "source_id")
    parsed = _parse_raw_log(dataset, raw_log)
    source = _optional_text(payload.get("source")) or "api"
    component = _optional_text(payload.get("component")) or parsed["component"]
    service = _optional_text(payload.get("service")) or component
    timestamp = _optional_text(payload.get("timestamp")) or parsed["timestamp"]
    level = _clean_level(_optional_text(payload.get("level"))) or parsed["level"]
    message = normalize_message(_optional_text(payload.get("message")) or parsed["message"] or raw_log)
    line_number = int(payload.get("line_number") or 1)
    if line_number < 1:
        raise ValueError("line_number must be positive")

    normalized = {
        "log_id": _optional_text(payload.get("log_id")) or stable_ingest_log_id({**payload, "raw_log": raw_log}),
        "dataset": dataset,
        "raw_log": raw_log,
        "message": message,
        "timestamp": timestamp,
        "component": component,
        "level": level,
        "event_id": _optional_text(payload.get("event_id")),
        "source_file": _optional_text(payload.get("source_file")) or parsed["source_file"] or source_id,
        "line_number": line_number,
        "source_id": source_id,
        "source": source,
        "service": service,
        "host": _optional_text(payload.get("host")),
        "environment": _optional_text(payload.get("environment")),
        "trace_id": _optional_text(payload.get("trace_id")),
        "request_id": _optional_text(payload.get("request_id")),
        "ingested_at": _optional_text(payload.get("ingested_at")) or datetime.now(UTC).isoformat(),
        "schema_version": int(payload.get("schema_version") or SCHEMA_VERSION),
        "parser_version": int(payload.get("parser_version") or PARSER_VERSION),
        "kafka_topic": _optional_text(payload.get("kafka_topic")),
        "kafka_partition": payload.get("kafka_partition"),
        "kafka_offset": payload.get("kafka_offset"),
    }
    return normalized


def build_failed_message(
    *,
    raw_payload: dict[str, Any],
    error_reason: str,
    topic: str,
    partition: int,
    offset: int,
) -> dict[str, Any]:
    return {
        "raw_payload": raw_payload,
        "error_reason": error_reason,
        "failed_at": datetime.now(UTC).isoformat(),
        "topic": topic,
        "partition": partition,
        "offset": offset,
    }
