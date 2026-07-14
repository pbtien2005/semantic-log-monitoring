"""Cross-file validation for generated ground-truth datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evaluation.checksums import sha256_file
from evaluation.ids import sequence_id
from evaluation.io import JsonObject, read_json, read_jsonl
from evaluation.time_utils import parse_iso_timestamp


DATASET_FILES = {
    "logs": "logs.jsonl",
    "queries": "groundtruth_queries.jsonl",
    "anomalies": "anomalies.jsonl",
    "incidents": "incidents.jsonl",
    "manifest": "dataset_manifest.json",
}


@dataclass(frozen=True)
class DatasetRecords:
    logs: list[JsonObject]
    queries: list[JsonObject]
    anomalies: list[JsonObject]
    incidents: list[JsonObject]
    manifest: JsonObject


@dataclass
class ValidationReport:
    dataset_dir: Path
    errors: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.errors

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)


class GroundTruthValidationError(Exception):
    """Raised when a ground-truth dataset fails validation."""

    def __init__(self, report: ValidationReport) -> None:
        super().__init__("\n".join(report.errors))
        self.report = report


def load_dataset(dataset_path: str | Path) -> DatasetRecords:
    dataset = Path(dataset_path)
    return DatasetRecords(
        logs=list(read_jsonl(dataset / DATASET_FILES["logs"])),
        queries=list(read_jsonl(dataset / DATASET_FILES["queries"])),
        anomalies=list(read_jsonl(dataset / DATASET_FILES["anomalies"])),
        incidents=list(read_jsonl(dataset / DATASET_FILES["incidents"])),
        manifest=read_json(dataset / DATASET_FILES["manifest"]),
    )


def validate_dataset_dir(dataset_path: str | Path, *, raise_on_error: bool = False) -> ValidationReport:
    dataset = Path(dataset_path)
    report = ValidationReport(dataset_dir=dataset)
    try:
        records = load_dataset(dataset)
    except Exception as exc:
        report.errors.append(f"failed to load dataset from {dataset}: {exc}")
        if raise_on_error:
            raise GroundTruthValidationError(report) from exc
        return report

    report.counts = {
        "logs": len(records.logs),
        "queries": len(records.queries),
        "anomalies": len(records.anomalies),
        "incidents": len(records.incidents),
    }

    log_by_id = validate_logs(records.logs, report)
    incident_by_id = validate_incidents(records.incidents, log_by_id, report)
    validate_queries(records.queries, log_by_id, incident_by_id, report)
    validate_anomalies(records.anomalies, log_by_id, incident_by_id, report)
    validate_manifest(dataset, records.manifest, report)

    if raise_on_error and report.errors:
        raise GroundTruthValidationError(report)
    return report


def validate_logs(logs: list[JsonObject], report: ValidationReport) -> dict[str, JsonObject]:
    log_by_id: dict[str, JsonObject] = {}
    previous_timestamp = None

    for index, log in enumerate(logs, start=1):
        context = f"logs.jsonl record {index}"
        log_id = require_str(log, "log_id", report, context)
        if log_id:
            report.require(log_id not in log_by_id, f"duplicate log_id: {log_id}")
            report.require(
                log_id == sequence_id("demo", index),
                f"{context} has non-deterministic log_id {log_id}; expected {sequence_id('demo', index)}",
            )
            log_by_id[log_id] = log

        timestamp = require_str(log, "timestamp", report, context)
        if timestamp:
            try:
                parsed = parse_iso_timestamp(timestamp)
            except Exception as exc:
                report.errors.append(f"{context} has invalid timestamp {timestamp!r}: {exc}")
                parsed = None
            if parsed is not None:
                if previous_timestamp is not None:
                    report.require(
                        parsed > previous_timestamp,
                        f"{context} timestamp is not strictly increasing: {timestamp}",
                    )
                previous_timestamp = parsed

        for key in ("dataset", "service", "component", "level", "template_id", "message", "raw_log"):
            require_str(log, key, report, context)
        role = require_str(log, "ground_truth_role", report, context)
        if role:
            report.require(
                role in {"normal", "noise", "related", "evidence", "root_cause", "incident"},
                f"{context} has invalid ground_truth_role: {role}",
            )
    return log_by_id


def validate_incidents(
    incidents: list[JsonObject],
    log_by_id: dict[str, JsonObject],
    report: ValidationReport,
) -> dict[str, JsonObject]:
    incident_by_id: dict[str, JsonObject] = {}
    for index, incident in enumerate(incidents, start=1):
        context = f"incidents.jsonl record {index}"
        incident_id = require_str(incident, "incident_id", report, context)
        if incident_id:
            report.require(incident_id not in incident_by_id, f"duplicate incident_id: {incident_id}")
            incident_by_id[incident_id] = incident

        scenario_type = require_str(incident, "scenario_type", report, context)
        report.require(
            scenario_type in {"explicit_root_cause", "silent_root_cause"},
            f"{context} has invalid scenario_type: {scenario_type}",
        )

        incident_log_id = require_str(incident, "incident_log_id", report, context)
        root_cause_log_id = incident.get("root_cause_log_id")
        evidence_ids = require_list(incident, "evidence_log_ids", report, context)
        required_ids = require_list(incident, "required_evidence_log_ids", report, context)
        optional_ids = require_list(incident, "optional_evidence_log_ids", report, context)

        require_log_ref(incident_log_id, log_by_id, report, f"{context}.incident_log_id")
        for log_id in evidence_ids + required_ids + optional_ids:
            require_log_ref(log_id, log_by_id, report, f"{context} evidence reference")
        report.require(
            set(required_ids).issubset(set(evidence_ids)),
            f"{context} required_evidence_log_ids must be a subset of evidence_log_ids",
        )
        report.require(
            set(optional_ids).issubset(set(evidence_ids)),
            f"{context} optional_evidence_log_ids must be a subset of evidence_log_ids",
        )
        if incident_log_id:
            report.require(
                str(incident_log_id) in set(evidence_ids),
                f"{context} incident_log_id must be included in evidence_log_ids",
            )

        if scenario_type == "explicit_root_cause":
            report.require(
                isinstance(root_cause_log_id, str) and bool(root_cause_log_id),
                f"{context} explicit incident must have exactly one root_cause_log_id",
            )
            if isinstance(root_cause_log_id, str):
                require_log_ref(root_cause_log_id, log_by_id, report, f"{context}.root_cause_log_id")
                report.require(
                    root_cause_log_id in set(evidence_ids),
                    f"{context} root_cause_log_id must be included in evidence_log_ids",
                )
                require_root_before_incident(root_cause_log_id, incident_log_id, log_by_id, report, context)
        if scenario_type == "silent_root_cause":
            report.require(root_cause_log_id is None, f"{context} silent incident must not have root_cause_log_id")

        require_ordered_chain(evidence_ids, log_by_id, report, context)
        require_str(incident, "root_cause_summary", report, context)
        require_str(incident, "timeline_explanation", report, context)
        require_str(incident, "why_incident_is_not_root_cause", report, context)
    return incident_by_id


def validate_queries(
    queries: list[JsonObject],
    log_by_id: dict[str, JsonObject],
    incident_by_id: dict[str, JsonObject],
    report: ValidationReport,
) -> None:
    seen: set[str] = set()
    for index, query in enumerate(queries, start=1):
        context = f"groundtruth_queries.jsonl record {index}"
        qid = require_str(query, "query_id", report, context)
        if qid:
            report.require(qid not in seen, f"duplicate query_id: {qid}")
            seen.add(qid)
        incident_id = require_str(query, "incident_id", report, context)
        report.require(incident_id in incident_by_id, f"{context} references unknown incident_id: {incident_id}")

        expected_ids = require_list(query, "expected_log_ids", report, context)
        required_ids = require_list(query, "required_log_ids", report, context)
        report.require(
            set(required_ids).issubset(set(expected_ids)),
            f"{context} required_log_ids must be a subset of expected_log_ids",
        )
        for log_id in expected_ids + required_ids:
            require_log_ref(log_id, log_by_id, report, f"{context} log reference")

        root_cause_log_id = query.get("root_cause_log_id")
        if root_cause_log_id is not None:
            require_log_ref(root_cause_log_id, log_by_id, report, f"{context}.root_cause_log_id")
            report.require(
                root_cause_log_id in expected_ids,
                f"{context} root_cause_log_id must be included in expected_log_ids",
            )
        elif incident_id in incident_by_id:
            report.require(
                incident_by_id[incident_id].get("scenario_type") == "silent_root_cause",
                f"{context} null root_cause_log_id is only valid for silent incidents",
            )

        judgments = query.get("relevance_judgments")
        report.require(isinstance(judgments, dict), f"{context} relevance_judgments must be an object")
        if isinstance(judgments, dict):
            for log_id, relevance in judgments.items():
                require_log_ref(str(log_id), log_by_id, report, f"{context} relevance_judgments")
                report.require(
                    isinstance(relevance, int) and relevance in {0, 1, 2, 3},
                    f"{context} has invalid relevance {relevance!r} for {log_id}",
                )
            for log_id in expected_ids:
                report.require(
                    str(log_id) in judgments,
                    f"{context} expected log {log_id} is missing a relevance judgment",
                )

        require_str(query, "query", report, context)
        require_str(query, "query_type", report, context)
        difficulty = require_str(query, "difficulty", report, context)
        report.require(difficulty in {"easy", "medium", "hard"}, f"{context} has invalid difficulty: {difficulty}")
        require_list(query, "expected_template_ids", report, context)
        require_list(query, "expected_answer_concepts", report, context)


def validate_anomalies(
    anomalies: list[JsonObject],
    log_by_id: dict[str, JsonObject],
    incident_by_id: dict[str, JsonObject],
    report: ValidationReport,
) -> None:
    seen: set[str] = set()
    has_positive = False
    has_negative = False
    for index, anomaly in enumerate(anomalies, start=1):
        context = f"anomalies.jsonl record {index}"
        anomaly_id = require_str(anomaly, "anomaly_id", report, context)
        if anomaly_id:
            report.require(anomaly_id not in seen, f"duplicate anomaly_id: {anomaly_id}")
            seen.add(anomaly_id)
        log_id = require_str(anomaly, "log_id", report, context)
        require_log_ref(log_id, log_by_id, report, f"{context}.log_id")
        incident_id = anomaly.get("incident_id")
        if incident_id is not None:
            report.require(
                incident_id in incident_by_id,
                f"{context} references unknown incident_id: {incident_id}",
            )
        expected = anomaly.get("expected_anomaly")
        report.require(isinstance(expected, bool), f"{context} expected_anomaly must be boolean")
        has_positive = has_positive or expected is True
        has_negative = has_negative or expected is False
        severity = require_str(anomaly, "expected_severity", report, context)
        report.require(
            severity in {"none", "low", "medium", "high"},
            f"{context} has invalid expected_severity: {severity}",
        )
        score_range = anomaly.get("expected_score_range")
        report.require(
            isinstance(score_range, list)
            and len(score_range) == 2
            and all(isinstance(value, (int, float)) for value in score_range)
            and 0 <= score_range[0] <= score_range[1] <= 1,
            f"{context} has invalid expected_score_range: {score_range}",
        )
        require_list(anomaly, "signals", report, context)
        require_str(anomaly, "reason", report, context)
    report.require(has_positive, "anomalies.jsonl must include at least one positive sample")
    report.require(has_negative, "anomalies.jsonl must include at least one negative sample")


def validate_manifest(dataset: Path, manifest: JsonObject, report: ValidationReport) -> None:
    expected_counts = {
        "log_count": report.counts.get("logs", 0),
        "query_count": report.counts.get("queries", 0),
        "anomaly_count": report.counts.get("anomalies", 0),
        "incident_count": report.counts.get("incidents", 0),
    }
    for key, expected in expected_counts.items():
        report.require(
            manifest.get(key) == expected,
            f"dataset_manifest.json {key}={manifest.get(key)!r} does not match actual {expected}",
        )
    files = manifest.get("files")
    report.require(isinstance(files, dict), "dataset_manifest.json files must be an object")
    if not isinstance(files, dict):
        return
    for filename in (
        DATASET_FILES["logs"],
        DATASET_FILES["queries"],
        DATASET_FILES["anomalies"],
        DATASET_FILES["incidents"],
    ):
        entry = files.get(filename)
        report.require(isinstance(entry, dict), f"dataset_manifest.json missing file entry: {filename}")
        if not isinstance(entry, dict):
            continue
        expected_hash = entry.get("sha256")
        actual_hash = sha256_file(dataset / filename)
        report.require(
            expected_hash == actual_hash,
            f"dataset_manifest.json checksum mismatch for {filename}: {expected_hash!r} != {actual_hash}",
        )


def require_root_before_incident(
    root_cause_log_id: str,
    incident_log_id: str,
    log_by_id: dict[str, JsonObject],
    report: ValidationReport,
    context: str,
) -> None:
    root_log = log_by_id.get(root_cause_log_id)
    incident_log = log_by_id.get(incident_log_id)
    if not root_log or not incident_log:
        return
    try:
        root_ts = parse_iso_timestamp(str(root_log["timestamp"]))
        incident_ts = parse_iso_timestamp(str(incident_log["timestamp"]))
    except Exception:
        return
    report.require(root_ts <= incident_ts, f"{context} root cause occurs after incident log")


def require_ordered_chain(
    evidence_ids: list[Any],
    log_by_id: dict[str, JsonObject],
    report: ValidationReport,
    context: str,
) -> None:
    timestamps = []
    for log_id in evidence_ids:
        log = log_by_id.get(str(log_id))
        if not log:
            return
        try:
            timestamps.append(parse_iso_timestamp(str(log["timestamp"])))
        except Exception:
            return
    report.require(timestamps == sorted(timestamps), f"{context} evidence chain is not time ordered")


def require_log_ref(
    log_id: Any,
    log_by_id: dict[str, JsonObject],
    report: ValidationReport,
    context: str,
) -> None:
    report.require(isinstance(log_id, str) and log_id in log_by_id, f"{context} references unknown log_id: {log_id}")


def require_str(record: JsonObject, key: str, report: ValidationReport, context: str) -> str:
    value = record.get(key)
    report.require(isinstance(value, str) and bool(value), f"{context} missing non-empty string field: {key}")
    return value if isinstance(value, str) else ""


def require_list(record: JsonObject, key: str, report: ValidationReport, context: str) -> list[Any]:
    value = record.get(key)
    report.require(isinstance(value, list), f"{context} missing list field: {key}")
    return value if isinstance(value, list) else []
