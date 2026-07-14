"""Explainable anomaly scoring using template, transition, and window context."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import mean
from typing import Any, Iterable

from src.anomaly.schema import (
    AnomalyBaseline,
    AnomalyConfig,
    AnomalyDecision,
    AnomalyLevel,
    AnomalyScore,
    BaselineMetadata,
    BaselineStatus,
    WindowProfile,
)
from src.anomaly.scoring_math import (
    ERROR_LEVELS as ERROR_LEVELS,
    NORMAL_LEVELS,
    WARN_LEVELS as WARN_LEVELS,
    anomaly_decision_for_score,
    anomaly_level_for_score,
    clamp01,
    dedupe,
    is_low_confidence_sequence,
    level,
    log_level_score,
    make_windows,
    percentile,
    record_sort_key,
    safe_int as safe_int,
    service_key,
    string_or_none,
    template_key,
    template_probability,
    template_surprise_raw,
    transition_probability,
    transition_surprise_raw,
    vector_distance,
    window_vector,
)
from src.anomaly.state import OnlineAnomalyState, StreamKey, stream_key_for


def build_baseline(
    records: Iterable[dict[str, Any]],
    *,
    config: AnomalyConfig | None = None,
) -> AnomalyBaseline:
    active_config = config or AnomalyConfig()
    rows = sorted(list(records), key=record_sort_key)
    training_rows = select_training_rows(rows, active_config)

    service_template_counts: dict[str, Counter[str]] = defaultdict(Counter)
    service_totals: Counter[str] = Counter()
    transition_counts: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    previous_template_totals: dict[str, Counter[str]] = defaultdict(Counter)

    for row in training_rows:
        service = service_key(row)
        template = template_key(row)
        service_template_counts[service][template] += 1
        service_totals[service] += 1

    previous_by_stream: dict[str, str] = {}
    for row in training_rows:
        service = service_key(row)
        current = template_key(row)
        stream_key = stream_key_for(row)
        if stream_key.key in previous_by_stream:
            previous = previous_by_stream[stream_key.key]
            transition_counts[service][previous][current] += 1
            previous_template_totals[service][previous] += 1
        previous_by_stream[stream_key.key] = current

    template_p99 = {
        service: percentile(
            [
                template_surprise_raw(
                    service=service,
                    template_id=template,
                    template_counts=service_template_counts,
                    service_totals=service_totals,
                    alpha=active_config.alpha,
                )
                for template in counts
            ],
            99,
        )
        for service, counts in service_template_counts.items()
    }
    transition_p99 = {
        service: percentile(
            [
                transition_surprise_raw(
                    service=service,
                    previous_template=previous,
                    current_template=current,
                    transition_counts=transition_counts,
                    previous_template_totals=previous_template_totals,
                    template_vocab_size=len(service_template_counts.get(service, {})),
                    alpha=active_config.alpha,
                )
                for previous, next_counts in transitions.items()
                for current in next_counts
            ],
            99,
        )
        for service, transitions in transition_counts.items()
    }
    window_profiles = build_window_profiles(training_rows, active_config)

    return AnomalyBaseline(
        service_template_counts={service: dict(counts) for service, counts in service_template_counts.items()},
        service_totals=dict(service_totals),
        transition_counts={
            service: {previous: dict(next_counts) for previous, next_counts in previous_map.items()}
            for service, previous_map in transition_counts.items()
        },
        previous_template_totals={
            service: dict(counts) for service, counts in previous_template_totals.items()
        },
        service_template_vocab={
            service: sorted(counts) for service, counts in service_template_counts.items()
        },
        template_p99_surprise=template_p99,
        transition_p99_surprise=transition_p99,
        window_profiles=window_profiles,
        config=active_config,
        metadata=metadata_for_config(active_config),
    )


def score_log_sequence(
    records: Iterable[dict[str, Any]],
    baseline: AnomalyBaseline,
    *,
    config: AnomalyConfig | None = None,
) -> list[AnomalyScore]:
    active_config = config or baseline.config
    rows = sorted(list(records), key=record_sort_key)
    state = OnlineAnomalyState(window_size=active_config.window_size)
    return [
        score_log_record(row, baseline, state=state, config=active_config)
        for row in rows
    ]


def score_log_record(
    row: dict[str, Any],
    baseline: AnomalyBaseline,
    *,
    state: OnlineAnomalyState,
    config: AnomalyConfig | None = None,
) -> AnomalyScore:
    active_config = config or baseline.config
    service = service_key(row)
    template = template_key(row)
    stream_key = stream_key_for(row)
    template_score, template_evidence, template_reasons = score_template(
        service=service,
        template_id=template,
        baseline=baseline,
        config=active_config,
    )
    transition_score, transition_evidence, transition_reasons = score_transition(
        service=service,
        previous_template=state.get_prev_template(stream_key),
        current_template=template,
        baseline=baseline,
        config=active_config,
        row=row,
        stream_key=stream_key,
    )
    state.update(row, template_id=template, stream_key=stream_key, service=service)
    window_score, window_evidence, window_reasons = score_window(
        service=service,
        window=state.get_recent_window(service),
        baseline=baseline,
        config=active_config,
    )
    severity_hint = log_level_score(row)
    reasons = [*template_reasons, *transition_reasons, *window_reasons]
    if severity_hint >= 1.0:
        reasons.append("error_severity_hint")
    elif severity_hint >= 0.7:
        reasons.append("warn_severity_hint")

    weights = scoring_weights(active_config, stream_key)
    raw_final = weighted_score(
        template_score=template_score,
        transition_score=transition_score,
        window_score=window_score,
        severity_hint=severity_hint,
        weights=weights,
    )
    baseline_status: BaselineStatus = "ready"
    decision: AnomalyDecision = "normal"
    service_total = baseline.service_totals.get(service, 0)
    if service_total < active_config.min_logs_per_service:
        baseline_status = "insufficient_history"
        decision = "warming_up"
        reasons.append("insufficient_service_history")

    final_score: float | None = clamp01(raw_final)
    anomaly_level: AnomalyLevel = anomaly_level_for_score(final_score, active_config)
    if decision == "warming_up":
        anomaly_level = "unknown"
        final_score = None

    evidence = {
        **template_evidence,
        **transition_evidence,
        **window_evidence,
        "service_total": service_total,
        "severity_hint": severity_hint,
        "weights": weights,
        "stream_key": stream_key.key,
    }
    if decision != "warming_up":
        decision = anomaly_decision_for_score(final_score or 0.0, active_config)
    return AnomalyScore(
        log_id=string_or_none(row.get("log_id")),
        dataset=str(row.get("dataset") or "unknown"),
        service=service,
        template_id=template,
        template_score=round(template_score, 6),
        transition_score=round(transition_score, 6),
        window_score=round(window_score, 6),
        severity_hint=round(severity_hint, 6),
        final_anomaly_score=round(final_score, 6) if final_score is not None else None,
        anomaly_level=anomaly_level,
        decision=decision,
        baseline_status=baseline_status,
        reasons=dedupe(reasons),
        evidence=evidence,
        transition_scope=stream_key.scope,
        transition_confidence=stream_key.confidence,
    )


def select_training_rows(records: list[dict[str, Any]], config: AnomalyConfig) -> list[dict[str, Any]]:
    if config.baseline_mode == "normal_only":
        return [row for row in records if level(row) in NORMAL_LEVELS]
    return records


def metadata_for_config(config: AnomalyConfig) -> BaselineMetadata:
    return BaselineMetadata(
        mode=config.baseline_mode,
        min_service_events=config.min_logs_per_service,
        min_windows_per_service=config.min_windows_per_service,
        smoothing_alpha=config.alpha,
        thresholds={
            "low": config.low_threshold,
            "medium": config.medium_threshold,
            "high": config.high_threshold,
        },
        scoring_weights={
            "template": config.template_weight,
            "transition": config.transition_weight,
            "window": config.window_weight,
            "service_fallback_transition": config.service_fallback_transition_weight,
            "service_fallback_window": config.service_fallback_window_weight,
            "severity_hint": config.log_level_weight,
        },
    )


def scoring_weights(config: AnomalyConfig, stream_key: StreamKey) -> dict[str, float]:
    transition_weight = (
        config.service_fallback_transition_weight
        if stream_key.is_service_fallback
        else config.transition_weight
    )
    window_weight = (
        config.service_fallback_window_weight
        if stream_key.is_service_fallback
        else config.window_weight
    )
    return {
        "template": config.template_weight,
        "transition": transition_weight,
        "window": window_weight,
        "severity_hint": config.log_level_weight,
    }


def weighted_score(
    *,
    template_score: float,
    transition_score: float,
    window_score: float,
    severity_hint: float,
    weights: dict[str, float],
) -> float:
    weighted_sum = (
        weights["template"] * template_score
        + weights["transition"] * transition_score
        + weights["window"] * window_score
        + weights["severity_hint"] * severity_hint
    )
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return 0.0
    return weighted_sum / total_weight


def score_template(
    *,
    service: str,
    template_id: str,
    baseline: AnomalyBaseline,
    config: AnomalyConfig,
) -> tuple[float, dict[str, Any], list[str]]:
    counts = baseline.service_template_counts.get(service, {})
    count = counts.get(template_id, 0)
    probability = template_probability(
        service=service,
        template_id=template_id,
        baseline=baseline,
        config=config,
    )
    surprise = -math.log(max(probability, config.epsilon))
    max_probability = max(
        (
            template_probability(
                service=service,
                template_id=known_template,
                baseline=baseline,
                config=config,
            )
            for known_template in counts
        ),
        default=probability,
    )
    score = clamp01((max_probability - probability) / max(max_probability, config.epsilon))
    reasons: list[str] = []
    if count == 0:
        reasons.append("new_template_for_service")
    elif score >= 0.8:
        reasons.append("rare_template_for_service")
    return (
        score,
        {
            "template_count": count,
            "template_probability": round(probability, 10),
            "template_max_probability": round(max_probability, 10),
            "template_surprise": round(surprise, 6),
        },
        reasons,
    )


def score_transition(
    *,
    service: str,
    previous_template: str | None,
    current_template: str,
    baseline: AnomalyBaseline,
    config: AnomalyConfig,
    row: dict[str, Any],
    stream_key: StreamKey,
) -> tuple[float, dict[str, Any], list[str]]:
    if previous_template is None:
        return (
            0.0,
            {
                "transition_probability": None,
                "transition_surprise": 0.0,
                "transition_scope": stream_key.scope,
                "transition_confidence": stream_key.confidence,
            },
            ["service_level_transition_fallback"] if stream_key.is_service_fallback else [],
        )

    previous_total = baseline.previous_template_totals.get(service, {}).get(previous_template, 0)
    if previous_total == 0:
        return (
            1.0,
            {
                "previous_template_id": previous_template,
                "transition_count": 0,
                "transition_probability": 0.0,
                "transition_surprise": None,
                "transition_scope": stream_key.scope,
                "transition_confidence": stream_key.confidence,
            },
            ["new_previous_template_for_transition", "new_template_transition"],
        )

    probability = transition_probability(
        service=service,
        previous_template=previous_template,
        current_template=current_template,
        baseline=baseline,
        config=config,
    )
    surprise = -math.log(max(probability, config.epsilon))
    next_counts = baseline.transition_counts.get(service, {}).get(previous_template, {})
    max_probability = max(
        (
            transition_probability(
                service=service,
                previous_template=previous_template,
                current_template=known_next,
                baseline=baseline,
                config=config,
            )
            for known_next in next_counts
        ),
        default=probability,
    )
    score = clamp01((max_probability - probability) / max(max_probability, config.epsilon))
    transition_count = (
        baseline.transition_counts.get(service, {})
        .get(previous_template, {})
        .get(current_template, 0)
    )
    reasons: list[str] = []
    if transition_count == 0:
        reasons.append("new_template_transition")
    elif score >= 0.8:
        reasons.append("rare_template_transition")
    if stream_key.is_service_fallback:
        reasons.append("service_level_transition_fallback")
    elif is_low_confidence_sequence(row):
        reasons.append("low_confidence_sequence_fallback")
    return (
        score,
        {
            "previous_template_id": previous_template,
            "transition_count": transition_count,
            "transition_probability": round(probability, 10),
            "transition_max_probability": round(max_probability, 10),
            "transition_surprise": round(surprise, 6),
            "transition_scope": stream_key.scope,
            "transition_confidence": stream_key.confidence,
        },
        reasons,
    )


def score_window(
    *,
    service: str,
    window: list[dict[str, Any]],
    baseline: AnomalyBaseline,
    config: AnomalyConfig,
) -> tuple[float, dict[str, Any], list[str]]:
    profile = baseline.window_profiles.get(service)
    if profile is None or profile.window_count < config.min_windows_per_service:
        return (
            0.0,
            {
                "window_count": 0 if profile is None else profile.window_count,
                "window_distance": 0.0,
            },
            ["insufficient_window_history"],
        )
    if len(window) < config.window_size:
        return (
            0.0,
            {"window_count": profile.window_count, "window_distance": 0.0},
            ["window_not_full"],
        )

    vector = window_vector(window, list(profile.template_mean))
    distance = vector_distance(vector, profile)
    denominator = max(profile.p99_distance, config.epsilon)
    score = clamp01(distance / denominator)
    reasons: list[str] = []
    if score >= 0.7:
        reasons.append("window_template_distribution_shift")
    if vector["error_ratio"] > max(profile.error_ratio_mean * 2, 0.1):
        reasons.append("window_error_ratio_spike")
    if vector["warn_ratio"] > max(profile.warn_ratio_mean * 2, 0.1):
        reasons.append("window_warn_ratio_spike")
    return (
        score,
        {
            "window_count": profile.window_count,
            "window_distance": round(distance, 6),
            "window_outlier_percentile_proxy": round(score, 6),
        },
        reasons,
    )


def build_window_profiles(records: list[dict[str, Any]], config: AnomalyConfig) -> dict[str, WindowProfile]:
    by_service: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_service[service_key(row)].append(row)

    profiles: dict[str, WindowProfile] = {}
    for service, rows in by_service.items():
        windows = make_windows(rows, config.window_size, config.window_step)
        if not windows:
            profiles[service] = WindowProfile(window_count=0)
            continue
        templates = sorted({template_key(row) for row in rows})
        vectors = [window_vector(window, templates) for window in windows]
        template_mean = {
            template: mean(vector["templates"].get(template, 0.0) for vector in vectors)
            for template in templates
        }
        profile_without_p99 = WindowProfile(
            template_mean=template_mean,
            error_ratio_mean=mean(vector["error_ratio"] for vector in vectors),
            warn_ratio_mean=mean(vector["warn_ratio"] for vector in vectors),
            unique_template_ratio_mean=mean(vector["unique_template_ratio"] for vector in vectors),
            p99_distance=0.0,
            window_count=len(windows),
        )
        distances = [vector_distance(vector, profile_without_p99) for vector in vectors]
        profiles[service] = WindowProfile(
            template_mean=template_mean,
            error_ratio_mean=profile_without_p99.error_ratio_mean,
            warn_ratio_mean=profile_without_p99.warn_ratio_mean,
            unique_template_ratio_mean=profile_without_p99.unique_template_ratio_mean,
            p99_distance=percentile(distances, 99),
            window_count=len(windows),
        )
    return profiles
