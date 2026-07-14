"""Normalize, load, filter, and rank logs used by dashboard chat."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from app.chat_query_utils import (
    extract_log_id,
    extract_query_level as extract_query_level,
    extract_query_terms,
    extract_rca_lookback_ms as extract_rca_lookback_ms,
    extract_recent_window_hours as extract_recent_window_hours,
    is_rca_query as is_rca_query,
    is_recent_log_query as is_recent_log_query,
    normalize_filter as normalize_filter,
    normalize_query_text as normalize_query_text,
    single_level as single_level,
)
from src.chunking.builders import build_line_chunk
from src.chunking.parsing import parse_timestamp_ms
from src.ingestion.kafka_contract import normalize_raw_log_payload
from src.ingestion.raw_log_store import OpenSearchRawLogStore, RawLogStoreError


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_ROOT = PROJECT_ROOT / "data" / "benchmark"
BLOCK_ID_RE = re.compile(r"\bblk_-?\d+\b")
IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b")


def normalize_context_logs(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_log_payload(record) for record in records if isinstance(record, dict)]


def load_online_rca_logs(
    query: str,
    *,
    dataset: str | None,
    limit: int = 500,
    store: OpenSearchRawLogStore | None = None,
) -> list[dict[str, Any]]:
    active_store = store or OpenSearchRawLogStore()
    incident_id = extract_log_id(query)
    try:
        incident = active_store.get_log(incident_id) if incident_id else None
        if incident:
            rows = active_store.search_logs(
                dataset=dataset or text_value(incident, "dataset"),
                source_id=text_value(incident, "source_id"),
                limit=limit,
            )
            rows = upsert_log_by_identity(rows, incident)
        else:
            rows = active_store.search_logs(dataset=dataset, limit=limit)
    except RawLogStoreError as exc:
        logger.warning("Falling back from online RCA logs for dataset=%s: %s", dataset, exc)
        return []
    return [row for row in (online_raw_log_to_rca_log(record) for record in rows) if row]


def online_raw_log_to_rca_log(record: dict[str, Any]) -> dict[str, Any] | None:
    try:
        normalized = normalize_raw_log_payload(record)
        chunk = build_line_chunk(normalized)
    except Exception as exc:
        logger.warning(
            "Unable to normalize online RCA log log_id=%s: %s",
            record.get("log_id"),
            exc,
        )
        return normalize_log_payload(record)

    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    return {
        "dataset": chunk.get("dataset"),
        "timestamp": metadata.get("timestamp"),
        "timestamp_ms": chunk.get("timestamp_ms"),
        "parsed_timestamp": (
            datetime.fromtimestamp(chunk["timestamp_ms"] / 1000)
            if chunk.get("timestamp_ms") is not None
            else None
        ),
        "level": chunk.get("level"),
        "service": metadata.get("service") or chunk.get("component"),
        "component": chunk.get("component"),
        "message": metadata.get("message") or metadata.get("raw_log"),
        "raw_log": metadata.get("raw_log") or metadata.get("message"),
        "log_id": chunk.get("log_id"),
        "template_id": chunk.get("template_id"),
        "request_id": chunk.get("request_id"),
        "trace_id": metadata.get("trace_id"),
        "host": metadata.get("host"),
        "block_id": chunk.get("block_id"),
        "ip": chunk.get("ip"),
        "anomaly_score": record.get("anomaly_score"),
    }


def normalize_log_payload(record: dict[str, Any]) -> dict[str, Any]:
    timestamp = str(record.get("timestamp") or "")
    timestamp_ms = coerce_timestamp_ms(
        record.get("timestamp_ms") or record.get("parsedMs") or record.get("parsed_timestamp_ms")
    )
    if timestamp_ms is None:
        timestamp_ms = parse_timestamp_ms(timestamp, str(record.get("dataset") or ""))
    if timestamp_ms is None:
        timestamp_ms = timestamp_to_ms(timestamp)
    message = str(record.get("message") or record.get("rawLog") or record.get("raw_log") or "")
    raw_log = str(record.get("rawLog") or record.get("raw_log") or message)
    service = record.get("service") or record.get("component") or record.get("logger")
    normalized = {
        "dataset": record.get("dataset") or "unknown",
        "timestamp": timestamp,
        "timestamp_ms": timestamp_ms,
        "parsed_timestamp": datetime.fromtimestamp(timestamp_ms / 1000) if timestamp_ms is not None else None,
        "level": str(record.get("level") or "UNKNOWN").upper(),
        "service": service or f"{record.get('dataset') or 'unknown'}-service",
        "component": record.get("component") or service,
        "message": message or raw_log,
        "raw_log": raw_log,
        "log_id": record.get("log_id") or record.get("logId"),
        "template_id": record.get("template_id") or record.get("templateId"),
        "anomaly_score": (
            record.get("anomaly_score")
            if record.get("anomaly_score") is not None
            else record.get("anomalyScore")
        ),
        "request_id": record.get("request_id") or record.get("requestId"),
        "trace_id": record.get("trace_id") or record.get("traceId"),
        "host": record.get("host"),
    }
    text = f"{normalized['message']} {raw_log}"
    block_match = BLOCK_ID_RE.search(text)
    if block_match:
        normalized["block_id"] = block_match.group(0)
    ip_match = IP_RE.search(text)
    if ip_match:
        normalized["ip"] = ip_match.group(0)
    return normalized


def coerce_timestamp_ms(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def timestamp_to_ms(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(pd.Timestamp(value).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def upsert_log_by_identity(logs: list[dict[str, Any]], log: dict[str, Any]) -> list[dict[str, Any]]:
    log_id = text_value(log, "log_id")
    if not log_id:
        return [*logs, log]
    return [row for row in logs if text_value(row, "log_id") != log_id] + [log]


def find_incident_log(query: str, logs: list[dict[str, Any]]) -> dict[str, Any] | None:
    log_id = extract_log_id(query)
    if log_id:
        for log in logs:
            if text_value(log, "log_id") == log_id:
                return log

    terms = extract_query_terms(query)
    ranked = rank_local_logs(logs, terms)
    for log in ranked:
        if str(log.get("level")).upper() in {"ERROR", "CRITICAL"} or float_or_zero(
            log.get("anomaly_score")
        ) >= 0.6:
            return log
    return None


def filter_rca_scope(
    logs: list[dict[str, Any]],
    *,
    dataset: str | None,
    component: str | None,
    levels: Sequence[str] | None,
) -> list[dict[str, Any]]:
    filtered = logs
    if dataset:
        filtered = [log for log in filtered if log.get("dataset") == dataset]
    if component:
        filtered = [
            log
            for log in filtered
            if log.get("service") == component or log.get("component") == component
        ]
    selected_levels = {
        "WARN" if str(level_name).upper() == "WARNING" else str(level_name).upper()
        for level_name in levels or []
        if level_name
    }
    if selected_levels:
        filtered = [
            log
            for log in filtered
            if str(log.get("level") or "UNKNOWN").upper() in selected_levels
        ]
    return filtered


def text_value(log: dict[str, Any], key: str) -> str | None:
    value = log.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def rank_local_logs(
    logs: list[dict[str, Any]],
    query_terms: Sequence[str],
) -> list[dict[str, Any]]:
    if not query_terms:
        return []

    scored: list[tuple[int, datetime, dict[str, Any]]] = []
    for log in logs:
        haystack_service = str(log["service"]).lower()
        haystack_message = str(log["message"]).lower()
        score = 0
        for term in query_terms:
            if term in haystack_service:
                score += 3
            if term in haystack_message:
                score += 2
        if score > 0:
            scored.append((score, log["parsed_timestamp"] or datetime.min, log))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in scored]


def sort_logs_newest(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        logs,
        key=lambda item: item["parsed_timestamp"] or datetime.min,
        reverse=True,
    )


def load_local_logs() -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    for path in sorted(LOGS_ROOT.glob("*/logs.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                logs.append(
                    normalize_log_payload(
                        {**record, "dataset": record.get("dataset") or path.parent.name}
                    )
                )
    return logs


def fallback_answer(query: str) -> str:
    return (
        "Mình đã nhận câu hỏi nhưng chưa có câu trả lời RAG khả dụng. "
        f"Câu hỏi: {query}. Hãy kiểm tra trạng thái Milvus và CLIProxyAPI nếu bạn muốn câu trả lời theo ngữ cảnh truy hồi."
    )


def summarize_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": context.get("query"),
        "dataset": context.get("plan", {}).get("dataset") if isinstance(context.get("plan"), dict) else None,
        "line_count": len(context.get("log_lines", [])) if isinstance(context.get("log_lines"), list) else None,
        "template_count": len(context.get("templates", [])) if isinstance(context.get("templates"), list) else None,
    }


def truncate(value: str, max_length: int) -> str:
    return value if len(value) <= max_length else f"{value[: max_length - 3]}..."
