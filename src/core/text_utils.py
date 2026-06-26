"""Text normalization and lightweight log parsing helpers."""

from __future__ import annotations

import re
from hashlib import sha1
from pathlib import Path
from typing import Any

from src.core.schema import Category


LEVEL_PATTERN = re.compile(
    r"\b(DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|ERR|FATAL|TRACE|CRITICAL|AUDIT)\b",
    re.I,
)
TIMESTAMP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?"),
    re.compile(r"\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}(?: [+-]\d{4})?"),
    re.compile(r"\d{6}\s+\d{6}"),
)

CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    "timeout": ("timeout", "timed out", "deadline", "expired"),
    "connection": ("connection", "connect", "disconnect", "refused", "reset"),
    "latency": ("latency", "slow", "delay", "delayed", "took", "duration"),
    "database": ("database", "sql", "mysql", "postgres", "sqlite"),
    "permission": ("permission", "denied", "unauthorized", "forbidden", "auth"),
    "storage": (
        "disk",
        "volume",
        "block",
        "blockmap",
        "base file",
        "imagecache",
        "hdfs",
        "namenode",
        "datanode",
        "storage",
    ),
    "network": ("network", "socket", "tcp", "udp", "dns", "host", "port"),
    "service_unavailable": (
        "service unavailable",
        "unavailable",
        "error state",
        "exception while serving",
        "down",
        "no route",
    ),
    "unknown": (),
}


def normalize_whitespace(text: str) -> str:
    return " ".join(text.strip().split())


def normalize_message(text: str) -> str:
    return normalize_whitespace(text.replace("\t", " "))


def infer_level(text: str) -> str | None:
    match = LEVEL_PATTERN.search(text)
    if not match:
        return None
    level = match.group(1).upper()
    return "WARN" if level == "WARNING" else level


def infer_timestamp(text: str) -> str | None:
    for pattern in TIMESTAMP_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def infer_category(text: str) -> Category:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "unknown":
            continue
        if any(keyword in lowered for keyword in keywords):
            return category
    return "unknown"


def stable_log_id(
    dataset: str,
    source_file: str | Path,
    line_number: int,
    raw_log: str,
) -> str:
    source_key = Path(source_file).as_posix()
    payload = f"{dataset}\n{source_key}\n{line_number}\n{raw_log}"
    digest = sha1(payload.encode("utf-8")).hexdigest()[:20]
    return f"{dataset}:{digest}"


def first_present(row: dict[str, Any], candidates: tuple[str, ...]) -> str | None:
    for key in candidates:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def extract_structured_message(row: dict[str, Any]) -> str:
    return first_present(
        row,
        (
            "Content",
            "Message",
            "message",
            "log_message",
            "EventTemplate",
            "Template",
        ),
    ) or ""


def extract_timestamp(row: dict[str, Any], raw_log: str) -> str | None:
    date = first_present(row, ("Date", "date"))
    time = first_present(row, ("Time", "time"))
    if date and time:
        return f"{date} {time}"

    timestamp = first_present(
        row,
        ("Timestamp", "timestamp", "Time", "Date", "Datetime", "DateTime"),
    )
    return timestamp or infer_timestamp(raw_log)


def extract_component(row: dict[str, Any]) -> str | None:
    return first_present(
        row,
        ("Component", "component", "Logger", "logger", "Service", "service"),
    )


def extract_level(row: dict[str, Any], raw_log: str) -> str | None:
    level = first_present(row, ("Level", "level", "Severity", "severity"))
    return level.upper() if level else infer_level(raw_log)


def extract_event_id(row: dict[str, Any]) -> str | None:
    return first_present(row, ("EventId", "EventID", "event_id", "EventTemplateId"))
