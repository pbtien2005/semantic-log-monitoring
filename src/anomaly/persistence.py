"""JSON persistence for anomaly baselines."""

from __future__ import annotations

import json
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.anomaly.schema import (
    AnomalyBaseline,
    AnomalyConfig,
    BaselineMetadata,
    WindowProfile,
)


def _dataclass_from_dict(cls: type[Any], data: dict[str, Any]) -> Any:
    allowed = {field.name for field in fields(cls)}
    return cls(**{key: value for key, value in data.items() if key in allowed})


def baseline_to_dict(baseline: AnomalyBaseline) -> dict[str, Any]:
    return {
        "metadata": baseline.metadata.to_dict(),
        "config": baseline.config.to_dict(),
        "service_template_counts": baseline.service_template_counts,
        "service_totals": baseline.service_totals,
        "transition_counts": baseline.transition_counts,
        "previous_template_totals": baseline.previous_template_totals,
        "service_template_vocab": baseline.service_template_vocab,
        "template_p99_surprise": baseline.template_p99_surprise,
        "transition_p99_surprise": baseline.transition_p99_surprise,
        "window_profiles": {
            service: profile.to_dict()
            for service, profile in baseline.window_profiles.items()
        },
    }


def baseline_from_dict(data: dict[str, Any]) -> AnomalyBaseline:
    config = _dataclass_from_dict(AnomalyConfig, data.get("config", {}))
    metadata = _dataclass_from_dict(BaselineMetadata, data.get("metadata", {}))
    return AnomalyBaseline(
        service_template_counts={
            service: {str(template): int(count) for template, count in counts.items()}
            for service, counts in data.get("service_template_counts", {}).items()
        },
        service_totals={
            str(service): int(count)
            for service, count in data.get("service_totals", {}).items()
        },
        transition_counts={
            str(service): {
                str(previous): {str(current): int(count) for current, count in next_counts.items()}
                for previous, next_counts in previous_map.items()
            }
            for service, previous_map in data.get("transition_counts", {}).items()
        },
        previous_template_totals={
            str(service): {str(template): int(count) for template, count in counts.items()}
            for service, counts in data.get("previous_template_totals", {}).items()
        },
        service_template_vocab={
            str(service): [str(template) for template in templates]
            for service, templates in data.get("service_template_vocab", {}).items()
        },
        template_p99_surprise={
            str(service): float(value)
            for service, value in data.get("template_p99_surprise", {}).items()
        },
        transition_p99_surprise={
            str(service): float(value)
            for service, value in data.get("transition_p99_surprise", {}).items()
        },
        window_profiles={
            str(service): _dataclass_from_dict(WindowProfile, profile)
            for service, profile in data.get("window_profiles", {}).items()
        },
        config=config,
        metadata=metadata,
    )


def save_baseline(baseline: AnomalyBaseline, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = baseline_to_dict(baseline)
    if not payload["metadata"].get("trained_at"):
        payload["metadata"]["trained_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> AnomalyBaseline:
    return baseline_from_dict(json.loads(path.read_text(encoding="utf-8")))
