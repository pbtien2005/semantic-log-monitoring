from __future__ import annotations

from src.anomaly.scoring import (
    AnomalyConfig,
    build_baseline,
    score_log_sequence,
)


def log(
    line: int,
    template_id: str,
    *,
    component: str = "payment-service",
    level: str = "INFO",
    timestamp_ms: int | None = None,
    request_id: str | None = None,
) -> dict[str, object]:
    return {
        "line_number": line,
        "log_id": f"log-{line}",
        "dataset": "demo",
        "component": component,
        "template_id": template_id,
        "level": level,
        "timestamp_ms": timestamp_ms if timestamp_ms is not None else line * 1000,
        "raw_log": f"{component} {level} {template_id}",
        "request_id": request_id,
    }


def test_scores_new_template_and_transition_with_explainable_reasons() -> None:
    baseline_logs = [
        log(1, "T1"),
        log(2, "T2"),
        log(3, "T1"),
        log(4, "T2"),
        log(5, "T1"),
        log(6, "T2"),
    ]
    config = AnomalyConfig(min_logs_per_service=3, min_windows_per_service=100)
    baseline = build_baseline(baseline_logs, config=config)

    scores = score_log_sequence(
        [
            log(7, "T1"),
            log(8, "T99", level="ERROR"),
        ],
        baseline,
        config=config,
    )

    first, second = scores
    assert first.anomaly_level == "normal"
    assert first.decision == "normal"
    assert second.final_anomaly_score > first.final_anomaly_score
    assert second.final_anomaly_score is not None
    assert second.final_anomaly_score >= config.low_threshold
    assert second.anomaly_level in {"low", "medium", "high"}
    assert second.decision == "watch"
    assert second.baseline_status == "ready"
    assert "new_template_for_service" in second.reasons
    assert "new_template_transition" in second.reasons
    assert second.evidence["template_probability"] < first.evidence["template_probability"]


def test_warming_up_suppresses_strong_alerts_for_undertrained_service() -> None:
    baseline = build_baseline(
        [log(1, "T1", component="new-service"), log(2, "T2", component="new-service")],
        config=AnomalyConfig(min_logs_per_service=10),
    )

    [score] = score_log_sequence(
        [log(3, "T99", component="new-service", level="ERROR")],
        baseline,
        config=AnomalyConfig(min_logs_per_service=10),
    )

    assert score.decision == "warming_up"
    assert score.baseline_status == "insufficient_history"
    assert score.anomaly_level == "unknown"
    assert score.final_anomaly_score is None
    assert "insufficient_service_history" in score.reasons


def test_window_score_is_skipped_until_enough_windows_exist() -> None:
    baseline_logs = [log(i, "T1" if i % 2 else "T2") for i in range(1, 12)]
    config = AnomalyConfig(
        min_logs_per_service=3,
        min_windows_per_service=50,
        window_size=4,
        window_step=2,
    )
    baseline = build_baseline(baseline_logs, config=config)

    scores = score_log_sequence(
        [log(12, "T1"), log(13, "T2"), log(14, "T99"), log(15, "T99")],
        baseline,
        config=config,
    )

    assert all(score.window_score == 0.0 for score in scores)
    assert all("insufficient_window_history" in score.reasons for score in scores)


def test_p99_normalization_uses_epsilon_for_degenerate_baselines() -> None:
    baseline_logs = [log(i, "T1") for i in range(1, 8)]
    config = AnomalyConfig(min_logs_per_service=3, epsilon=1e-6)
    baseline = build_baseline(baseline_logs, config=config)

    [score] = score_log_sequence([log(8, "T1")], baseline, config=config)

    assert 0.0 <= score.template_score <= 1.0
    assert 0.0 <= score.transition_score <= 1.0
    assert score.final_anomaly_score is not None
    assert 0.0 <= score.final_anomaly_score <= 1.0


def test_error_level_alone_is_only_a_severity_hint_not_an_anomaly_rule() -> None:
    baseline_logs = [log(i, "T1", level="INFO") for i in range(1, 20)]
    config = AnomalyConfig(min_logs_per_service=3, min_windows_per_service=100)
    baseline = build_baseline(baseline_logs, config=config)

    [score] = score_log_sequence([log(20, "T1", level="ERROR")], baseline, config=config)

    assert score.severity_hint == 1.0
    assert "error_severity_hint" in score.reasons
    assert score.final_anomaly_score is not None
    assert score.final_anomaly_score < config.low_threshold
    assert score.decision == "normal"


def test_scoped_transition_prefers_request_context_over_service_fallback() -> None:
    baseline_logs = [
        log(1, "T1", request_id="req-a"),
        log(2, "T2", request_id="req-a"),
        log(3, "T1", request_id="req-b"),
        log(4, "T2", request_id="req-b"),
        log(5, "T1", request_id="req-c"),
        log(6, "T2", request_id="req-c"),
    ]
    config = AnomalyConfig(min_logs_per_service=3, min_windows_per_service=100)
    baseline = build_baseline(baseline_logs, config=config)

    scores = score_log_sequence(
        [
            log(7, "T1", request_id="req-x"),
            log(8, "T99", request_id="req-x"),
        ],
        baseline,
        config=config,
    )

    assert scores[-1].transition_scope == "request"
    assert scores[-1].transition_confidence == 1.0
    assert "service_level_transition_fallback" not in scores[-1].reasons


def test_demo_new_log_list_flags_error_burst() -> None:
    baseline_logs = []
    for i in range(1, 81):
        baseline_logs.append(log(i, "T_LOGIN_START", component="auth-service"))
        baseline_logs.append(log(i + 1000, "T_LOGIN_OK", component="auth-service"))

    config = AnomalyConfig(
        min_logs_per_service=20,
        min_windows_per_service=2,
        window_size=4,
        window_step=2,
    )
    baseline = build_baseline(baseline_logs, config=config)

    new_logs = [
        log(2001, "T_LOGIN_START", component="auth-service"),
        log(2002, "T_LOGIN_OK", component="auth-service"),
        log(2003, "T_DB_TIMEOUT", component="auth-service", level="ERROR"),
        log(2004, "T_DB_TIMEOUT", component="auth-service", level="ERROR"),
    ]
    scores = score_log_sequence(new_logs, baseline, config=config)

    assert scores[0].anomaly_level == "normal"
    assert scores[-1].final_anomaly_score >= 0.6
    assert scores[-1].anomaly_level in {"medium", "high"}
    assert "new_template_for_service" in scores[-1].reasons
    assert "window_template_distribution_shift" in scores[-1].reasons
