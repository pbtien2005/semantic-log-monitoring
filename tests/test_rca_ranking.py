from __future__ import annotations

from src.rca import rank_rca_evidence


def log(
    log_id: str,
    timestamp_ms: int,
    *,
    service: str = "checkout",
    anomaly_score: float | None = None,
    template_id: str = "T1",
    request_id: str | None = "req-1",
) -> dict[str, object]:
    return {
        "log_id": log_id,
        "dataset": "demo",
        "timestamp_ms": timestamp_ms,
        "service": service,
        "template_id": template_id,
        "request_id": request_id,
        "anomaly_score": anomaly_score,
        "message": f"{service} {template_id}",
    }


def test_rank_rca_evidence_prefers_prior_anomalous_same_entity_candidates() -> None:
    incident = log("incident", 10_000, anomaly_score=0.9, template_id="T9")
    unrelated = log("old", 1_000, service="billing", anomaly_score=0.9, request_id="req-9")
    candidate = log("candidate", 9_500, anomaly_score=0.8, template_id="T2")
    normal_prior = log("normal", 9_700, anomaly_score=0.0, template_id="T1")

    evidence = rank_rca_evidence(
        [unrelated, candidate, normal_prior, incident],
        incident,
        lookback_ms=2_000,
        limit=3,
    )

    assert evidence.incident_log_id == "incident"
    by_id = {item.log_id: item for item in evidence.candidates}
    assert by_id["candidate"].rca_score > by_id["normal"].rca_score
    assert "candidate_has_high_anomaly_score" in by_id["candidate"].reasons
    assert "shared_entity_or_session" in by_id["candidate"].reasons
    assert all(item.log_id != "old" for item in evidence.candidates)


def test_rank_rca_evidence_weights_shared_entity_above_unrelated_anomaly() -> None:
    incident = log("incident", 10_000, anomaly_score=0.9, template_id="T9")
    same_entity = log("same-entity", 9_900, anomaly_score=0.0, template_id="T2")
    high_anomaly = log(
        "high-anomaly",
        9_500,
        anomaly_score=1.0,
        template_id="T3",
        request_id="req-9",
    )

    evidence = rank_rca_evidence(
        [same_entity, high_anomaly, incident],
        incident,
        lookback_ms=2_000,
        limit=2,
    )

    by_id = {item.log_id: item for item in evidence.candidates}
    assert by_id["same-entity"].rca_score > by_id["high-anomaly"].rca_score
    assert "shared_entity_or_session" in by_id["same-entity"].reasons


def test_rank_rca_evidence_returns_empty_without_incident_timestamp() -> None:
    evidence = rank_rca_evidence([log("candidate", 9_500)], {"log_id": "incident"})

    assert evidence.candidates == []
