"""Build line-level and template-level chunks from parsed log records."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from src.core.schema import validate_log_dataset
from src.chunking.parsing import (
    HTTP_STATUS_RE,
    RESPONSE_LEN_RE,
    extract_entities,
    first,
    infer_apache_module,
    infer_task_state,
    normalize_template,
    parse_duration_ms,
    parse_http,
    parse_int,
    parse_source_log,
    parse_timestamp_ms,
    sanitize_message_for_embedding,
    unique,
)
from src.chunking.template_matcher import TemplateMatcher
from src.chunking.template_discovery import candidate_id_for_template


MAX_TEMPLATE_SAMPLES = 5
UNKNOWN_VALUES = {"", "none", "unknown", "null"}


def meaningful_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in UNKNOWN_VALUES:
        return None
    return text


def build_embed_text(
    *,
    dataset: str,
    component: str | None,
    level: str | None,
    template: str,
    message: str | None = None,
    candidate_id: str | None = None,
    occurrences: int | None = None,
) -> str:
    fields = (
        ("dataset", dataset),
        ("component", component),
        ("level", level),
        ("template", template),
    )
    lines = [f"{name}: {text}" for name, value in fields if (text := meaningful_value(value))]
    if message_text := meaningful_value(message):
        lines.append(f"message: {message_text}")
    if candidate_text := meaningful_value(candidate_id):
        lines.append(f"candidate_id: {candidate_text}")
    if occurrences is not None:
        lines.append(f"occurrences: {occurrences}")
    return "\n".join(lines)


def merge_slot_entities(entities: dict[str, list[str]], slots: dict[str, str]) -> dict[str, list[str]]:
    merged = {name: list(values) for name, values in entities.items()}
    for name, value in slots.items():
        merged.setdefault(name, [])
        if value not in merged[name]:
            merged[name].append(value)
    return merged


def build_line_chunk(log: dict[str, Any], *, template_matcher: TemplateMatcher | None = None) -> dict[str, Any]:
    dataset = validate_log_dataset(str(log["dataset"]))
    raw_log = str(log["raw_log"])
    message = str(log["message"])
    entities = extract_entities(log)
    component = log.get("component")
    level = log.get("level")
    match = (
        template_matcher.match(
            dataset=dataset,
            message=message,
            component=component,
            level=level,
        )
        if template_matcher
        else None
    )
    template = match.template if match else normalize_template(message)
    if match:
        entities = merge_slot_entities(entities, match.slots)
    timestamp = log.get("timestamp")
    timestamp_ms = parse_timestamp_ms(str(timestamp) if timestamp else None, dataset)
    http = parse_http(message)
    http_status = parse_int(HTTP_STATUS_RE, message, "status")
    response_len = parse_int(RESPONSE_LEN_RE, message, "length")
    duration_ms = parse_duration_ms(message)
    task_state = infer_task_state(message)
    module = infer_apache_module(message) if dataset == "apache" else None
    message_for_embedding = sanitize_message_for_embedding(message)
    candidate_id = None
    if match and match.template_id:
        template_id = match.template_id
    else:
        candidate_id = candidate_id_for_template(dataset, template)
        template_id = candidate_id
    template_match_status = "matched" if match and match.matched else ("miss" if match else "dynamic")
    template_match_method = match.match_method if match else "dynamic_normalize"
    template_match_confidence = match.confidence if match else 1.0
    template_slots = match.slots if match else {}
    ambiguous_match_count = match.candidate_count if match and match.candidate_count > 1 else 0

    metadata = {
        "timestamp": timestamp,
        "timestamp_ms": timestamp_ms,
        "component": component,
        "level": level,
        "line_number": log.get("line_number"),
        "source_file": log.get("source_file"),
        "source_log": parse_source_log(raw_log),
        "raw_log": raw_log,
        "message": message,
        "template": template,
        "template_id": template_id,
        "candidate_id": candidate_id,
        "template_match_status": template_match_status,
        "template_match_method": template_match_method,
        "template_match_confidence": template_match_confidence,
        "template_slots": template_slots,
        "ambiguous_match_count": ambiguous_match_count,
        "message_for_embedding": message_for_embedding,
        "entities": entities,
        "request_id": first(entities["request_id"]),
        "instance_id": first(entities["instance_id"]),
        "block_id": first(entities["block_id"]),
        "ip": first(entities["ip"]),
        "ip_port": first(entities["ip_port"]),
        "http_status": http_status,
        "http_method": http["http_method"],
        "api_route": http["api_route"],
        "http_version": http["http_version"],
        "response_len": response_len,
        "duration_ms": duration_ms,
        "task_state": task_state,
        "module": module,
        "path": first(entities["path"]),
        "source_id": log.get("source_id"),
        "source": log.get("source"),
        "service": log.get("service"),
        "host": log.get("host"),
        "environment": log.get("environment"),
        "ingested_at": log.get("ingested_at"),
        "schema_version": log.get("schema_version"),
        "parser_version": log.get("parser_version"),
        "trace_id": log.get("trace_id"),
        "kafka_topic": log.get("kafka_topic"),
        "kafka_partition": log.get("kafka_partition"),
        "kafka_offset": log.get("kafka_offset"),
    }

    return {
        "chunk_id": f"line::{log['log_id']}",
        "chunk_type": "log_line",
        "dataset": dataset,
        "log_id": log["log_id"],
        "component": component,
        "level": level,
        "timestamp_ms": timestamp_ms,
        "request_id": metadata["request_id"],
        "instance_id": metadata["instance_id"],
        "block_id": metadata["block_id"],
        "ip": metadata["ip"],
        "http_status": http_status,
        "duration_ms": duration_ms,
        "template_id": template_id,
        "embed_text": build_embed_text(
            dataset=dataset,
            component=component,
            level=level,
            template=template,
            message=message_for_embedding,
            candidate_id=candidate_id,
        ),
        "metadata": metadata,
    }


def template_chunk_id(dataset: str, component: str | None, level: str | None, template: str) -> str:
    key = "\x1f".join((dataset, component or "", level or "", template))
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return f"template::{dataset}::{digest}"


def merge_entities(chunks: list[dict[str, Any]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        entities = chunk["metadata"]["entities"]
        for name, values in entities.items():
            merged[name].extend(values)
    return {name: unique(values) for name, values in sorted(merged.items())}


def build_template_chunks(line_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str | None, str | None, str], list[dict[str, Any]]] = defaultdict(list)
    for chunk in line_chunks:
        metadata = chunk["metadata"]
        key = (
            chunk["dataset"],
            metadata.get("component"),
            metadata.get("level"),
            metadata["template"],
        )
        groups[key].append(chunk)

    template_chunks: list[dict[str, Any]] = []
    for (dataset, component, level, template), chunks in sorted(groups.items()):
        sample_chunks = chunks[:MAX_TEMPLATE_SAMPLES]
        line_numbers = [chunk["metadata"]["line_number"] for chunk in chunks]
        entities = merge_entities(chunks)
        occurrence_count = len(chunks)
        metadata = {
            "component": component,
            "level": level,
            "template": template,
            "occurrence_count": occurrence_count,
            "log_ids": [chunk["log_id"] for chunk in chunks],
            "sample_log_ids": [chunk["log_id"] for chunk in sample_chunks],
            "sample_messages": [chunk["metadata"]["message"] for chunk in sample_chunks],
            "line_numbers": line_numbers,
            "first_line_number": min(line_numbers),
            "last_line_number": max(line_numbers),
            "first_timestamp_ms": min(
                (value for value in (chunk["metadata"]["timestamp_ms"] for chunk in chunks) if value is not None),
                default=None,
            ),
            "last_timestamp_ms": max(
                (value for value in (chunk["metadata"]["timestamp_ms"] for chunk in chunks) if value is not None),
                default=None,
            ),
            "entities": entities,
        }
        template_chunks.append(
            {
                "chunk_id": template_chunk_id(dataset, component, level, template),
                "chunk_type": "template_group",
                "dataset": dataset,
                "component": component,
                "level": level,
                "timestamp_ms": metadata["first_timestamp_ms"],
                "request_id": first(entities.get("request_id", [])),
                "instance_id": first(entities.get("instance_id", [])),
                "block_id": first(entities.get("block_id", [])),
                "ip": first(entities.get("ip", [])),
                "http_status": None,
                "duration_ms": None,
                "embed_text": build_embed_text(
                    dataset=dataset,
                    component=component,
                    level=level,
                    template=template,
                    occurrences=occurrence_count,
                ),
                "metadata": metadata,
            }
        )
    return template_chunks
