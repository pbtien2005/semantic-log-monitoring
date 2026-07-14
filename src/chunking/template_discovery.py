"""Pending template discovery artifacts for catalog misses."""

from __future__ import annotations

from hashlib import sha1
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


def candidate_id_for_template(dataset: str, template: str) -> str:
    digest = sha1(f"{dataset}\n{template}".encode("utf-8")).hexdigest()[:16]
    return f"template::{dataset}::{digest}"


def _candidate_from_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    template = str(metadata.get("template") or "")
    dataset = str(chunk.get("dataset") or "")
    candidate_id = str(
        metadata.get("candidate_id")
        or chunk.get("candidate_id")
        or candidate_id_for_template(dataset, template)
    )
    return _compact(
        {
            "candidate_id": candidate_id,
            "dataset": dataset,
            "template": template,
            "draft_regex": regex_from_template(template) if template else None,
            "status": "pending",
            "searchable": True,
            "occurrences": 1,
        }
    )


def _merge_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    merged["occurrences"] = int(merged.get("occurrences") or 0) + int(incoming.get("occurrences") or 1)
    merged.setdefault("status", incoming.get("status") or "pending")
    merged.setdefault("searchable", incoming.get("searchable", True))
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

    by_key: dict[str, dict[str, Any]] = {}
    if path.exists():
        for record in read_jsonl(path):
            candidate_id = str(record.get("candidate_id") or "")
            if not candidate_id and record.get("dataset") and record.get("template"):
                candidate_id = candidate_id_for_template(str(record["dataset"]), str(record["template"]))
                record = {
                    "candidate_id": candidate_id,
                    "dataset": record.get("dataset"),
                    "template": record.get("template"),
                    "draft_regex": record.get("draft_regex") or record.get("regex"),
                    "occurrences": int(record.get("occurrences") or 0),
                    "status": record.get("status") or "pending",
                    "searchable": record.get("searchable", True),
                }
            if candidate_id:
                by_key[candidate_id] = record

    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        grouped.setdefault(str(candidate["candidate_id"]), []).append(candidate)

    for key, values in grouped.items():
        record = by_key.get(key)
        for value in values:
            record = value if record is None else _merge_candidate(record, value)
        if record is not None:
            by_key[key] = record

    write_jsonl(path, [by_key[key] for key in sorted(by_key)])
    return len(grouped)
