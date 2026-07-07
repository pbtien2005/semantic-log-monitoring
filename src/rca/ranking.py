"""Rank probable earlier evidence for anomalous logs."""

from __future__ import annotations

from typing import Any

from src.rca.schema import RcaCandidate, RcaEvidenceSet


DEFAULT_LOOKBACK_MS = 10 * 60 * 1000
ENTITY_KEYS = ("trace_id", "request_id", "session_id", "block_id", "instance_id", "host")


def rank_rca_evidence(
    logs: list[dict[str, Any]],
    incident_log: dict[str, Any],
    *,
    lookback_ms: int = DEFAULT_LOOKBACK_MS,
    limit: int = 10,
) -> RcaEvidenceSet:
    candidates = build_investigation_window(logs, incident_log, lookback_ms=lookback_ms)
    scored = score_rca_candidates(candidates, incident_log, lookback_ms=lookback_ms)
    ranked = sorted(scored, key=lambda item: item.rca_score, reverse=True)[:limit]
    chronological = sorted(
        ranked,
        key=lambda item: (item.timestamp_ms if item.timestamp_ms is not None else 10**30, item.log_id or ""),
    )
    return RcaEvidenceSet(
        incident_log_id=text_value(incident_log, "log_id"),
        incident_timestamp_ms=timestamp_ms(incident_log),
        candidates=chronological,
    )


def build_investigation_window(
    logs: list[dict[str, Any]],
    incident_log: dict[str, Any],
    *,
    lookback_ms: int,
) -> list[dict[str, Any]]:
    incident_time = timestamp_ms(incident_log)
    if incident_time is None:
        return []
    start = incident_time - lookback_ms
    incident_id = text_value(incident_log, "log_id")
    incident_dataset = text_value(incident_log, "dataset")
    return [
        log
        for log in logs
        if text_value(log, "log_id") != incident_id
        and (incident_dataset is None or text_value(log, "dataset") == incident_dataset)
        and (timestamp_ms(log) is not None and start <= timestamp_ms(log) <= incident_time)
    ]


def score_rca_candidates(
    candidates: list[dict[str, Any]],
    incident_log: dict[str, Any],
    *,
    lookback_ms: int,
) -> list[RcaCandidate]:
    return [
        candidate
        for candidate in (
            score_candidate(candidate, incident_log, lookback_ms=lookback_ms)
            for candidate in candidates
        )
        if candidate.rca_score > 0
    ]


def score_candidate(
    candidate: dict[str, Any],
    incident_log: dict[str, Any],
    *,
    lookback_ms: int,
) -> RcaCandidate:
    anomaly = anomaly_score(candidate)
    temporal = temporal_prior_score(candidate, incident_log, lookback_ms=lookback_ms)
    service = service_or_component_score(candidate, incident_log)
    template = template_relatedness(candidate, incident_log)
    entity = entity_match_score(candidate, incident_log)
    score = 0.25 * anomaly + 0.20 * temporal + 0.15 * service + 0.15 * template + 0.25 * entity
    reasons = []
    if anomaly >= 0.6:
        reasons.append("candidate_has_high_anomaly_score")
    if temporal > 0:
        reasons.append("candidate_precedes_incident")
    if service >= 1.0:
        reasons.append("same_service_or_component")
    if template >= 1.0:
        reasons.append("same_template")
    if entity > 0:
        reasons.append("shared_entity_or_session")
    if not entity and service > 0:
        reasons.append("service_window_fallback")
    return RcaCandidate(
        log_id=text_value(candidate, "log_id"),
        timestamp_ms=timestamp_ms(candidate),
        service=service_value(candidate),
        template_id=text_value(candidate, "template_id"),
        rca_score=round(score, 6),
        reasons=reasons,
        log=candidate,
        components={
            "anomaly_score": round(anomaly, 6),
            "temporal_prior_score": round(temporal, 6),
            "service_or_component_score": round(service, 6),
            "template_relatedness": round(template, 6),
            "entity_match_score": round(entity, 6),
        },
    )


def anomaly_score(log: dict[str, Any]) -> float:
    value = nested_value(log, "anomaly_score")
    if value is None:
        anomaly = nested_value(log, "anomaly")
        if isinstance(anomaly, dict):
            value = anomaly.get("score")
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def temporal_prior_score(
    candidate: dict[str, Any],
    incident_log: dict[str, Any],
    *,
    lookback_ms: int,
) -> float:
    candidate_time = timestamp_ms(candidate)
    incident_time = timestamp_ms(incident_log)
    if candidate_time is None or incident_time is None or candidate_time > incident_time:
        return 0.0
    delta = incident_time - candidate_time
    if delta > lookback_ms:
        return 0.0
    return max(0.0, 1.0 - (delta / max(1, lookback_ms)))


def service_or_component_score(candidate: dict[str, Any], incident_log: dict[str, Any]) -> float:
    if service_value(candidate) == service_value(incident_log):
        return 1.0
    if text_value(candidate, "dataset") == text_value(incident_log, "dataset"):
        return 0.25
    return 0.0


def template_relatedness(candidate: dict[str, Any], incident_log: dict[str, Any]) -> float:
    candidate_template = text_value(candidate, "template_id") or text_value(candidate, "template")
    incident_template = text_value(incident_log, "template_id") or text_value(incident_log, "template")
    if candidate_template and candidate_template == incident_template:
        return 1.0
    candidate_family = text_value(candidate, "event_family")
    incident_family = text_value(incident_log, "event_family")
    if candidate_family and candidate_family == incident_family:
        return 0.5
    return 0.0


def entity_match_score(candidate: dict[str, Any], incident_log: dict[str, Any]) -> float:
    for key in ENTITY_KEYS:
        left = text_value(candidate, key)
        right = text_value(incident_log, key)
        if left and right and left == right:
            return 1.0
    return 0.0


def timestamp_ms(log: dict[str, Any]) -> int | None:
    for key in ("timestamp_ms", "parsedMs", "parsed_timestamp_ms"):
        value = nested_value(log, key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def service_value(log: dict[str, Any]) -> str:
    return (
        text_value(log, "service")
        or text_value(log, "component")
        or text_value(log, "logger")
        or f"{text_value(log, 'dataset') or 'unknown'}-service"
    )


def text_value(log: dict[str, Any], key: str) -> str | None:
    value = nested_value(log, key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def nested_value(log: dict[str, Any], key: str) -> Any:
    if key in log:
        return log[key]
    for container_name in ("metadata", "payload"):
        container = log.get(container_name)
        if isinstance(container, dict) and key in container:
            return container[key]
    return None
