"""Build line-level and template-level chunks from parsed log records."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from src.core.schema import validate_log_dataset
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
    sanitize_message_for_embedding,
    unique,
)
from src.chunking.template_matcher import TemplateMatcher


MAX_TEMPLATE_SAMPLES = 5
UNKNOWN_VALUES = {"", "none", "unknown", "null"}


@dataclass(frozen=True, slots=True)
class EventClassification:
    event_type: str | None = None
    event_family: str | None = None
    signals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SignalBundle:
    signals: list[str]
    weak_signals: list[str]


def meaningful_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in UNKNOWN_VALUES:
        return None
    return text


def embeddable_signals(signals: list[str]) -> list[str]:
    return [signal for signal in signals if meaningful_value(signal)]


def classify_event(dataset: str, template: str, message: str, component: str | None) -> EventClassification:
    text = f"{component or ''} {template} {message}".lower()

    if dataset == "apache":
        if "directory index forbidden" in text:
            return EventClassification(
                "directory_index_forbidden",
                "apache_access",
                ("directory_forbidden", "permission_denied"),
            )
        if "workerenv.init() ok" in text:
            return EventClassification(
                "worker_env_initialized",
                "apache_backend",
                ("worker_environment", "initialization_success", "config_loaded"),
            )
        if "workerenv in error state" in text:
            return EventClassification(
                "backend_worker_error",
                "apache_backend",
                ("worker_environment", "backend_worker_error", "backend_down", "worker_error"),
            )

    if dataset == "openstack":
        if "no valid host" in text:
            return EventClassification(
                "scheduler_failure",
                "compute_lifecycle",
                ("scheduler_failure", "no_valid_host", "compute_lifecycle"),
            )
        if "took <duration_" in text and "build instance" in text:
            return EventClassification(
                "instance_build_completed",
                "compute_lifecycle",
                ("instance_build", "instance_build_completed", "compute_lifecycle"),
            )
        if "sync_power_state" in text:
            return EventClassification(
                "sync_power_state",
                "compute_lifecycle",
                ("sync_power_state", "compute_lifecycle"),
            )
        if "libvirt" in text and ("error" in text or "exception" in text):
            return EventClassification(
                "libvirt_error",
                "compute_lifecycle",
                ("libvirt_error", "compute_lifecycle"),
            )

    if dataset == "hdfs":
        if "packetresponder" in text:
            return EventClassification(
                "packet_responder_block_lifecycle",
                "hdfs_block_lifecycle",
                ("hdfs_block_lifecycle", "datanode_storage"),
            )
        if "block" in text or "blk_" in text:
            return EventClassification(
                None,
                "hdfs_block_lifecycle",
                ("hdfs_block_lifecycle",),
            )

    return EventClassification()


def build_signal_bundle(
    dataset: str,
    log: dict[str, Any],
    template: str,
    entities: dict[str, list[str]],
    event: EventClassification,
) -> SignalBundle:
    signal_set: set[str] = set()
    weak_signal_set: set[str] = set()
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
    signal_set.update(event.signals)

    for category in CATEGORIES:
        scored = score_log(dataset, category, log)
        label = scored.label(scoring_profile(category))
        if category == "unknown" and label in {"positive", "uncertain"}:
            weak_signal_set.add(category)
        elif label == "positive":
            signal_set.add(category)
        elif label == "uncertain":
            weak_signal_set.add(category)

    return SignalBundle(sorted(signal_set), sorted(weak_signal_set - signal_set))


def build_signals(dataset: str, log: dict[str, Any], template: str, entities: dict[str, list[str]]) -> list[str]:
    event = classify_event(dataset, template, str(log.get("message") or ""), log.get("component"))
    return build_signal_bundle(dataset, log, template, entities, event).signals


def build_embed_text(
    *,
    dataset: str,
    component: str | None,
    level: str | None,
    template: str,
    signals: list[str],
    intent: list[str] | None = None,
    event_type: str | None = None,
    event_family: str | None = None,
    message: str | None = None,
    occurrences: int | None = None,
) -> str:
    fields = (
        ("dataset", dataset),
        ("component", component),
        ("level", level),
        ("event_type", event_type),
        ("event_family", event_family),
        ("template", template),
    )
    lines = [f"{name}: {text}" for name, value in fields if (text := meaningful_value(value))]
    filtered_signals = embeddable_signals(signals)
    if intent:
        lines.append("intent: " + " ".join(embeddable_signals(intent)))
    if filtered_signals:
        lines.append("signals: " + " ".join(filtered_signals))
    if message_text := meaningful_value(message):
        lines.append(f"message: {message_text}")
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
    event = classify_event(dataset, template, message, log.get("component"))
    signal_bundle = build_signal_bundle(dataset, log, template, entities, event)
    signals = signal_bundle.signals
    weak_signals = signal_bundle.weak_signals
    message_for_embedding = sanitize_message_for_embedding(message)
    template_id = (
        match.template_id
        if match and match.template_id
        else template_chunk_id(dataset, component, level, template)
    )
    intent = match.intent if match else []
    template_match_status = "matched" if match and match.matched else ("miss" if match else "dynamic")
    template_match_method = match.match_method if match else "dynamic_normalize"
    template_match_confidence = match.confidence if match else 1.0
    template_slots = match.slots if match else {}
    ambiguous_match_count = match.candidate_count if match and match.candidate_count > 1 else 0
    if match and match.matched:
        event = EventClassification(
            event_type=match.event_type or event.event_type,
            event_family=match.event_family or event.event_family,
            signals=tuple(match.signals or ()),
        )
        signals = sorted(set(signals).union(match.signals or ()))
        weak_signals = sorted(set(weak_signals).union(match.weak_signals or ()) - set(signals))

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
        "weak_signals": weak_signals,
        "event_type": event.event_type,
        "event_family": event.event_family,
        "template_id": template_id,
        "template_match_status": template_match_status,
        "template_match_method": template_match_method,
        "template_match_confidence": template_match_confidence,
        "template_slots": template_slots,
        "ambiguous_match_count": ambiguous_match_count,
        "intent": intent,
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
        "event_type": event.event_type,
        "event_family": event.event_family,
        "template_id": template_id,
        "embed_text": build_embed_text(
            dataset=dataset,
            component=component,
            level=level,
            event_type=event.event_type,
            event_family=event.event_family,
            template=template,
            signals=signals,
            intent=intent,
            message=message_for_embedding,
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
        weak_signals = sorted(
            {signal for chunk in chunks for signal in chunk["metadata"].get("weak_signals", [])}
            - set(signals)
        )
        event_type_counts = Counter(
            event_type
            for chunk in chunks
            if (event_type := chunk["metadata"].get("event_type"))
        )
        event_family_counts = Counter(
            event_family
            for chunk in chunks
            if (event_family := chunk["metadata"].get("event_family"))
        )
        event_type = event_type_counts.most_common(1)[0][0] if event_type_counts else None
        event_family = event_family_counts.most_common(1)[0][0] if event_family_counts else None
        sample_chunks = chunks[:MAX_TEMPLATE_SAMPLES]
        line_numbers = [chunk["metadata"]["line_number"] for chunk in chunks]
        entities = merge_entities(chunks)
        occurrence_count = len(chunks)
        metadata = {
            "component": component,
            "level": level,
            "template": template,
            "signals": signals,
            "weak_signals": weak_signals,
            "event_type": event_type,
            "event_family": event_family,
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
                "event_type": event_type,
                "event_family": event_family,
                "embed_text": build_embed_text(
                    dataset=dataset,
                    component=component,
                    level=level,
                    event_type=event_type,
                    event_family=event_family,
                    template=template,
                    signals=signals,
                    occurrences=occurrence_count,
                ),
                "metadata": metadata,
            }
        )
    return template_chunks
