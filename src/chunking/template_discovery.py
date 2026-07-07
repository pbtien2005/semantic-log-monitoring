"""Pending template discovery artifacts for catalog misses."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.chunking.template_matcher import regex_from_template
from src.core.io_utils import read_jsonl, write_jsonl


def _compact(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if item is not None and item != [] and item != {}
    }


def _candidate_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(record.get("dataset") or ""),
        str(record.get("component") or ""),
        str(record.get("level") or ""),
        str(record.get("template") or ""),
    )


def _first_seen_value(metadata: dict[str, Any]) -> str:
    return str(
        metadata.get("ingested_at")
        or metadata.get("timestamp")
        or datetime.now(UTC).isoformat()
    )


def _candidate_from_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    template = str(metadata.get("template") or "")
    return _compact(
        {
            "template_id": metadata.get("template_id") or chunk.get("template_id"),
            "dataset": chunk.get("dataset"),
            "component": metadata.get("component"),
            "level": metadata.get("level"),
            "template": template,
            "regex": regex_from_template(template) if template else None,
            "intent": [],
            "priority": 10,
            "active": False,
            "status": "pending",
            "occurrences": 1,
            "first_seen": _first_seen_value(metadata),
            "last_seen": _first_seen_value(metadata),
            "sample_log_ids": [chunk.get("log_id")],
            "sample_messages": [metadata.get("message")],
            "source_ids": [metadata.get("source_id")],
            "template_match_status": metadata.get("template_match_status"),
        }
    )


def _merge_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    merged["occurrences"] = int(merged.get("occurrences") or 0) + int(incoming.get("occurrences") or 1)
    merged["last_seen"] = incoming.get("last_seen") or merged.get("last_seen")
    for key in ("sample_log_ids", "sample_messages", "source_ids"):
        values = list(merged.get(key) or [])
        for value in incoming.get(key) or []:
            if value and value not in values:
                values.append(value)
        merged[key] = values[:5]
    return merged


def upsert_pending_template_candidates(
    chunks: list[dict[str, Any]],
    path: Path,
) -> int:
    candidates = [
        _candidate_from_chunk(chunk)
        for chunk in chunks
        if (chunk.get("metadata") or {}).get("template_match_status") in {"miss", "dynamic"}
    ]
    if not candidates:
        return 0

    by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    if path.exists():
        for record in read_jsonl(path):
            by_key[_candidate_key(record)] = record

    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[_candidate_key(candidate)].append(candidate)

    for key, values in grouped.items():
        record = by_key.get(key)
        for value in values:
            record = value if record is None else _merge_candidate(record, value)
        if record is not None:
            by_key[key] = record

    write_jsonl(path, [by_key[key] for key in sorted(by_key)])
    return len(grouped)
