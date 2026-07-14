"""Config objects and a small stdlib-only config loader for evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DatasetConfig:
    version: str = "groundtruth-v1.0"
    seed: int = 20260714
    log_count: int = 2000
    query_count: int = 50
    incident_count: int = 15
    anomaly_count: int = 18


@dataclass(frozen=True)
class RetrievalConfig:
    top_k: int = 24
    experiments: tuple[str, ...] = (
        "baseline_log_only_v1",
        "template_first_recency_v1",
    )


@dataclass(frozen=True)
class QualityGates:
    hit_at_10: float = 0.85
    recall_at_24: float = 0.80
    required_evidence_recall_at_24: float = 0.90
    root_cause_hit_at_10: float = 0.75
    root_cause_hit_at_24: float = 0.90
    root_cause_mrr: float = 0.50


@dataclass(frozen=True)
class EvaluationConfig:
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    quality_gates: QualityGates = field(default_factory=QualityGates)


def load_config(path: str | Path) -> EvaluationConfig:
    file_path = Path(path)
    raw = _load_mapping(file_path)
    dataset = raw.get("dataset", {})
    retrieval = raw.get("retrieval", {})
    quality_gates = raw.get("quality_gates", {})
    if not isinstance(dataset, dict) or not isinstance(retrieval, dict) or not isinstance(quality_gates, dict):
        raise ValueError(f"Invalid top-level config shape in {file_path}")

    return EvaluationConfig(
        dataset=DatasetConfig(
            version=str(dataset.get("version", DatasetConfig.version)),
            seed=int(dataset.get("seed", DatasetConfig.seed)),
            log_count=int(dataset.get("log_count", DatasetConfig.log_count)),
            query_count=int(dataset.get("query_count", DatasetConfig.query_count)),
            incident_count=int(dataset.get("incident_count", DatasetConfig.incident_count)),
            anomaly_count=int(dataset.get("anomaly_count", DatasetConfig.anomaly_count)),
        ),
        retrieval=RetrievalConfig(
            top_k=int(retrieval.get("top_k", RetrievalConfig.top_k)),
            experiments=tuple(str(item) for item in retrieval.get("experiments", RetrievalConfig.experiments)),
        ),
        quality_gates=QualityGates(
            hit_at_10=float(quality_gates.get("hit_at_10", QualityGates.hit_at_10)),
            recall_at_24=float(quality_gates.get("recall_at_24", QualityGates.recall_at_24)),
            required_evidence_recall_at_24=float(
                quality_gates.get(
                    "required_evidence_recall_at_24",
                    QualityGates.required_evidence_recall_at_24,
                )
            ),
            root_cause_hit_at_10=float(
                quality_gates.get("root_cause_hit_at_10", QualityGates.root_cause_hit_at_10)
            ),
            root_cause_hit_at_24=float(
                quality_gates.get("root_cause_hit_at_24", QualityGates.root_cause_hit_at_24)
            ),
            root_cause_mrr=float(quality_gates.get("root_cause_mrr", QualityGates.root_cause_mrr)),
        ),
    )


def _load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"Expected JSON object in {path}")
        return value
    return _parse_simple_yaml(path.read_text(encoding="utf-8"), source=path)


def _parse_simple_yaml(text: str, *, source: Path) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current_section: str | None = None
    current_list_key: str | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue
        indent = len(line_without_comment) - len(line_without_comment.lstrip(" "))
        stripped = line_without_comment.strip()

        if indent == 0:
            key, value = _split_key_value(stripped, source, line_number)
            if value == "":
                root[key] = {}
                current_section = key
                current_list_key = None
            else:
                root[key] = _parse_scalar(value)
                current_section = None
                current_list_key = None
            continue

        if current_section is None or not isinstance(root.get(current_section), dict):
            raise ValueError(f"Unexpected indentation in {source} at line {line_number}")

        section = root[current_section]
        if not isinstance(section, dict):
            raise ValueError(f"Invalid section in {source} at line {line_number}")

        if stripped.startswith("- "):
            if current_list_key is None:
                raise ValueError(f"List item without list key in {source} at line {line_number}")
            value = stripped[2:].strip()
            target = section[current_list_key]
            if not isinstance(target, list):
                raise ValueError(f"Expected list for {current_list_key} in {source} at line {line_number}")
            target.append(_parse_scalar(value))
            continue

        key, value = _split_key_value(stripped, source, line_number)
        if value == "":
            section[key] = []
            current_list_key = key
        else:
            section[key] = _parse_scalar(value)
            current_list_key = None

    return root


def _split_key_value(line: str, source: Path, line_number: int) -> tuple[str, str]:
    if ":" not in line:
        raise ValueError(f"Expected key/value pair in {source} at line {line_number}")
    key, value = line.split(":", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Empty key in {source} at line {line_number}")
    return key, value.strip()


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "None", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value
