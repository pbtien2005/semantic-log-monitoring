"""Pure probability, window, threshold, and normalization helpers for anomaly scoring."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable

from src.anomaly.schema import (
    AnomalyBaseline,
    AnomalyConfig,
    AnomalyDecision,
    AnomalyLevel,
    WindowProfile,
)
from src.anomaly.state import service_key_for


NORMAL_LEVELS = {"INFO", "NOTICE", "DEBUG"}
WARN_LEVELS = {"WARN", "WARNING"}
ERROR_LEVELS = {"ERROR", "CRITICAL", "FATAL", "ALERT", "EMERG"}


def make_windows(records: list[dict[str, Any]], size: int, step: int) -> list[list[dict[str, Any]]]:
    if size <= 0 or step <= 0 or len(records) < size:
        return []
    return [records[start : start + size] for start in range(0, len(records) - size + 1, step)]


def window_vector(window: list[dict[str, Any]], templates: list[str]) -> dict[str, Any]:
    total = max(1, len(window))
    counts = Counter(template_key(row) for row in window)
    levels = Counter(level(row) for row in window)
    return {
        "templates": {template: counts.get(template, 0) / total for template in templates},
        "error_ratio": sum(levels.get(name, 0) for name in ERROR_LEVELS) / total,
        "warn_ratio": sum(levels.get(name, 0) for name in WARN_LEVELS) / total,
        "unique_template_ratio": len(counts) / total,
    }


def vector_distance(vector: dict[str, Any], profile: WindowProfile) -> float:
    template_distance = sum(
        abs(vector["templates"].get(template, 0.0) - expected)
        for template, expected in profile.template_mean.items()
    )
    return (
        template_distance
        + abs(vector["error_ratio"] - profile.error_ratio_mean)
        + abs(vector["warn_ratio"] - profile.warn_ratio_mean)
        + abs(vector["unique_template_ratio"] - profile.unique_template_ratio_mean)
    )


def template_probability(
    *,
    service: str,
    template_id: str,
    baseline: AnomalyBaseline,
    config: AnomalyConfig,
) -> float:
    counts = baseline.service_template_counts.get(service, {})
    total = baseline.service_totals.get(service, 0)
    vocab_size = max(1, len(counts) + (0 if template_id in counts else 1))
    return (counts.get(template_id, 0) + config.alpha) / (
        total + config.alpha * vocab_size
    )


def transition_probability(
    *,
    service: str,
    previous_template: str,
    current_template: str,
    baseline: AnomalyBaseline,
    config: AnomalyConfig,
) -> float:
    next_counts = baseline.transition_counts.get(service, {}).get(previous_template, {})
    total = baseline.previous_template_totals.get(service, {}).get(previous_template, 0)
    vocab_size = max(1, len(baseline.service_template_vocab.get(service, [])))
    if current_template not in baseline.service_template_vocab.get(service, []):
        vocab_size += 1
    return (next_counts.get(current_template, 0) + config.alpha) / (
        total + config.alpha * vocab_size
    )


def template_surprise_raw(
    *,
    service: str,
    template_id: str,
    template_counts: dict[str, Counter[str]],
    service_totals: Counter[str],
    alpha: float,
) -> float:
    counts = template_counts.get(service, Counter())
    vocab_size = max(1, len(counts))
    probability = (counts.get(template_id, 0) + alpha) / (
        service_totals.get(service, 0) + alpha * vocab_size
    )
    return -math.log(probability)


def transition_surprise_raw(
    *,
    service: str,
    previous_template: str,
    current_template: str,
    transition_counts: dict[str, dict[str, Counter[str]]],
    previous_template_totals: dict[str, Counter[str]],
    template_vocab_size: int,
    alpha: float,
) -> float:
    probability = (
        transition_counts.get(service, {}).get(previous_template, {}).get(current_template, 0)
        + alpha
    ) / (
        previous_template_totals.get(service, {}).get(previous_template, 0)
        + alpha * max(1, template_vocab_size)
    )
    return -math.log(probability)


def log_level_score(row: dict[str, Any]) -> float:
    row_level = level(row)
    if row_level in ERROR_LEVELS:
        return 1.0
    if row_level in WARN_LEVELS:
        return 0.7
    if row_level == "NOTICE":
        return 0.2
    return 0.0


def anomaly_level_for_score(score: float, config: AnomalyConfig) -> AnomalyLevel:
    if score >= config.high_threshold:
        return "high"
    if score >= config.medium_threshold:
        return "medium"
    if score >= config.low_threshold:
        return "low"
    return "normal"


def anomaly_decision_for_score(score: float, config: AnomalyConfig) -> AnomalyDecision:
    if score >= config.high_threshold:
        return "anomalous"
    if score >= config.low_threshold:
        return "watch"
    return "normal"


def service_key(row: dict[str, Any]) -> str:
    return service_key_for(row)


def template_key(row: dict[str, Any]) -> str:
    value = row.get("template_id") or row.get("event_id") or row.get("template")
    text = str(value or "").strip()
    if text:
        return text
    raw = str(row.get("message") or row.get("raw_log") or "").strip()
    return raw or "unknown-template"


def level(row: dict[str, Any]) -> str:
    return str(row.get("level") or "UNKNOWN").upper()


def record_sort_key(row: dict[str, Any]) -> tuple[int, int]:
    timestamp = row.get("timestamp_ms")
    line_number = row.get("line_number")
    return (safe_int(timestamp), safe_int(line_number))


def is_low_confidence_sequence(row: dict[str, Any]) -> bool:
    dataset = str(row.get("dataset") or "").lower()
    if dataset != "apache":
        return False
    return not (row.get("request_id") or row.get("trace_id") or row.get("session_id"))


def percentile(values: Iterable[float], q: float) -> float:
    sorted_values = sorted(float(value) for value in values)
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * q / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[int(position)]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def clamp01(value: float) -> float:
    if math.isnan(value) or value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result
