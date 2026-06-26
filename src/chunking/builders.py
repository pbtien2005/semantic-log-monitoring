"""Build line-level and template-level chunks from parsed log records."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from src.core.schema import validate_dataset
from src.rules.category_rules import CATEGORIES, score_log, scoring_profile
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
    unique,
)


MAX_TEMPLATE_SAMPLES = 5


def build_signals(dataset: str, log: dict[str, Any], template: str, entities: dict[str, list[str]]) -> list[str]:
    signal_set: set[str] = set()
    component = str(log.get("component") or "").lower()
    level = str(log.get("level") or "").lower()
    text = f"{component} {level} {template}".lower()

    if component:
        signal_set.update(part for part in component.split(".") if part and part != "nova")
    if level in {"warn", "warning", "error", "notice"}:
        signal_set.add(f"level_{level}")
    if entities["request_id"]:
        signal_set.add("has_request_id")
    if entities["instance_id"]:
        signal_set.add("has_instance_id")
    if entities["block_id"]:
        signal_set.add("has_block_id")
    if entities["ip"]:
        signal_set.add("has_ip")
    if "instance" in text or "vm " in text:
        signal_set.add("instance_state")
    if "sync_power_state" in text:
        signal_set.add("sync_power_state")
    if "imagecache" in text or "image cache" in text or "base file" in text:
        signal_set.add("image_cache")
    if "packetresponder" in text or "blockmap" in text or "fsdataset" in text:
        signal_set.add("hdfs_storage")
    if "status:" in text or "http/" in text:
        signal_set.add("http_request")

    for category in CATEGORIES:
        scored = score_log(dataset, category, log)
        if scored.label(scoring_profile(category)) in {"positive", "uncertain"}:
            signal_set.add(category)

    return sorted(signal_set)


def build_embed_text(
    *,
    dataset: str,
    component: str | None,
    level: str | None,
    template: str,
    signals: list[str],
    occurrences: int | None = None,
) -> str:
    lines = [
        f"dataset: {dataset}",
        f"component: {component or 'none'}",
        f"level: {level or 'none'}",
        f"template: {template}",
    ]
    if signals:
        lines.append("signals: " + " ".join(signals))
    if occurrences is not None:
        lines.append(f"occurrences: {occurrences}")
    return "\n".join(lines)


def build_line_chunk(log: dict[str, Any]) -> dict[str, Any]:
    dataset = validate_dataset(str(log["dataset"]))
    raw_log = str(log["raw_log"])
    message = str(log["message"])
    entities = extract_entities(log)
    template = normalize_template(message)
    timestamp = log.get("timestamp")
    timestamp_ms = parse_timestamp_ms(str(timestamp) if timestamp else None, dataset)
    http = parse_http(message)
    http_status = parse_int(HTTP_STATUS_RE, message, "status")
    response_len = parse_int(RESPONSE_LEN_RE, message, "length")
    duration_ms = parse_duration_ms(message)
    task_state = infer_task_state(message)
    module = infer_apache_module(message) if dataset == "apache" else None
    signals = build_signals(dataset, log, template, entities)
    component = log.get("component")
    level = log.get("level")

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
        "signals": signals,
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
        "embed_text": build_embed_text(
            dataset=dataset,
            component=component,
            level=level,
            template=template,
            signals=signals,
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
        signals = sorted({signal for chunk in chunks for signal in chunk["metadata"].get("signals", [])})
        sample_chunks = chunks[:MAX_TEMPLATE_SAMPLES]
        line_numbers = [chunk["metadata"]["line_number"] for chunk in chunks]
        entities = merge_entities(chunks)
        occurrence_count = len(chunks)
        metadata = {
            "component": component,
            "level": level,
            "template": template,
            "signals": signals,
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
                    signals=signals,
                    occurrences=occurrence_count,
                ),
                "metadata": metadata,
            }
        )
    return template_chunks
