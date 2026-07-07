"""Schemas for evidence-based RCA candidate retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RcaCandidate:
    log_id: str | None
    timestamp_ms: int | None
    service: str
    template_id: str | None
    rca_score: float
    reasons: list[str]
    log: dict[str, Any]
    components: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RcaEvidenceSet:
    incident_log_id: str | None
    incident_timestamp_ms: int | None
    candidates: list[RcaCandidate]

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_log_id": self.incident_log_id,
            "incident_timestamp_ms": self.incident_timestamp_ms,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }
