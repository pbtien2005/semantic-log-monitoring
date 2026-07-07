"""Helpers for attaching anomaly scores to records and chunks."""

from __future__ import annotations

from typing import Any

from src.anomaly.schema import AnomalyScore


def flattened_anomaly_fields(score: AnomalyScore) -> dict[str, Any]:
    payload = score.to_payload()
    return {
        "anomaly": payload,
        "anomaly_score": payload["score"],
        "anomaly_level": payload["level"],
        "anomaly_decision": payload["decision"],
        "anomaly_baseline_status": payload["baseline_status"],
        "anomaly_reasons": payload["reasons"],
        "anomaly_components": payload["components"],
    }


def attach_anomaly(record: dict[str, Any], score: AnomalyScore) -> dict[str, Any]:
    fields = flattened_anomaly_fields(score)
    updated = {**record, **fields}
    metadata = updated.get("metadata")
    if isinstance(metadata, dict):
        updated["metadata"] = {**metadata, **fields}
    return updated


def missing_baseline_fields(reason: str = "missing_baseline") -> dict[str, Any]:
    payload = {
        "score": None,
        "level": "unknown",
        "decision": "warming_up",
        "baseline_status": "missing_baseline",
        "reasons": [reason],
        "components": {
            "template_score": None,
            "transition_score": None,
            "window_score": None,
            "severity_hint": 0.0,
        },
        "evidence": {},
        "transition_scope": "service",
        "transition_confidence": 0.0,
    }
    return {
        "anomaly": payload,
        "anomaly_score": None,
        "anomaly_level": "unknown",
        "anomaly_decision": "warming_up",
        "anomaly_baseline_status": "missing_baseline",
        "anomaly_reasons": payload["reasons"],
        "anomaly_components": payload["components"],
    }


def attach_missing_baseline(record: dict[str, Any], reason: str = "missing_baseline") -> dict[str, Any]:
    fields = missing_baseline_fields(reason)
    updated = {**record, **fields}
    metadata = updated.get("metadata")
    if isinstance(metadata, dict):
        updated["metadata"] = {**metadata, **fields}
    return updated
