"""Schemas for explainable, non-rule-based anomaly scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


AnomalyLevel = Literal["normal", "low", "medium", "high", "unknown"]
AnomalyDecision = Literal["normal", "watch", "anomalous", "warming_up", "not_scored"]
BaselineStatus = Literal[
    "ready",
    "insufficient_history",
    "missing_baseline",
    "disabled",
    "error",
]
BaselineMode = Literal["all", "normal_only"]
TransitionScope = Literal[
    "trace",
    "request",
    "session",
    "block",
    "instance",
    "entity",
    "host",
    "source",
    "service",
]


@dataclass(frozen=True, slots=True)
class AnomalyConfig:
    alpha: float = 0.5
    epsilon: float = 1e-6
    min_logs_per_service: int = 1000
    min_windows_per_service: int = 50
    window_size: int = 50
    window_step: int = 25
    template_weight: float = 0.40
    transition_weight: float = 0.35
    window_weight: float = 0.25
    service_fallback_transition_weight: float = 0.20
    service_fallback_window_weight: float = 0.40
    log_level_weight: float = 0.0
    low_threshold: float = 0.40
    medium_threshold: float = 0.60
    high_threshold: float = 0.80
    baseline_mode: BaselineMode = "all"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BaselineMetadata:
    baseline_version: int = 1
    trained_at: str | None = None
    dataset: str | None = None
    mode: BaselineMode = "all"
    min_service_events: int = 1000
    min_windows_per_service: int = 50
    smoothing_alpha: float = 0.5
    thresholds: dict[str, float] = field(default_factory=dict)
    scoring_weights: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WindowProfile:
    template_mean: dict[str, float] = field(default_factory=dict)
    error_ratio_mean: float = 0.0
    warn_ratio_mean: float = 0.0
    unique_template_ratio_mean: float = 0.0
    p99_distance: float = 0.0
    window_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AnomalyBaseline:
    service_template_counts: dict[str, dict[str, int]]
    service_totals: dict[str, int]
    transition_counts: dict[str, dict[str, dict[str, int]]]
    previous_template_totals: dict[str, dict[str, int]]
    service_template_vocab: dict[str, list[str]]
    template_p99_surprise: dict[str, float]
    transition_p99_surprise: dict[str, float]
    window_profiles: dict[str, WindowProfile]
    config: AnomalyConfig
    metadata: BaselineMetadata = field(default_factory=BaselineMetadata)


@dataclass(frozen=True, slots=True)
class AnomalyComponents:
    template_score: float | None
    transition_score: float | None
    window_score: float | None
    severity_hint: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AnomalyScore:
    log_id: str | None
    dataset: str
    service: str
    template_id: str
    template_score: float
    transition_score: float
    window_score: float
    severity_hint: float
    final_anomaly_score: float | None
    anomaly_level: AnomalyLevel
    decision: AnomalyDecision
    baseline_status: BaselineStatus
    reasons: list[str]
    evidence: dict[str, Any]
    transition_scope: TransitionScope
    transition_confidence: float

    @property
    def score_value(self) -> float:
        return 0.0 if self.final_anomaly_score is None else self.final_anomaly_score

    def components(self) -> AnomalyComponents:
        if self.final_anomaly_score is None:
            return AnomalyComponents(
                template_score=None,
                transition_score=None,
                window_score=None,
                severity_hint=self.severity_hint,
            )
        return AnomalyComponents(
            template_score=self.template_score,
            transition_score=self.transition_score,
            window_score=self.window_score,
            severity_hint=self.severity_hint,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "score": self.final_anomaly_score,
            "level": self.anomaly_level,
            "decision": self.decision,
            "baseline_status": self.baseline_status,
            "reasons": self.reasons,
            "components": self.components().to_dict(),
            "evidence": self.evidence,
            "transition_scope": self.transition_scope,
            "transition_confidence": self.transition_confidence,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "log_id": self.log_id,
            "dataset": self.dataset,
            "service": self.service,
            "template_id": self.template_id,
            "template_score": self.template_score,
            "transition_score": self.transition_score,
            "window_score": self.window_score,
            "severity_hint": self.severity_hint,
            "final_anomaly_score": self.final_anomaly_score,
            "anomaly_level": self.anomaly_level,
            "decision": self.decision,
            "baseline_status": self.baseline_status,
            "reasons": self.reasons,
            "evidence": self.evidence,
            "transition_scope": self.transition_scope,
            "transition_confidence": self.transition_confidence,
            "anomaly": self.to_payload(),
        }
