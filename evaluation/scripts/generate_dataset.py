"""Generate deterministic synthetic ground-truth datasets for evaluation."""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from evaluation.checksums import manifest_for_files
from evaluation.config import EvaluationConfig, load_config
from evaluation.ids import query_id, sequence_id
from evaluation.io import JsonObject, ensure_dir, read_jsonl, write_json, write_jsonl
from evaluation.paths import dataset_dir, scenarios_dir
from evaluation.time_utils import isoformat_z


DEFAULT_START = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)
EVALUATION_ONLY_FIELDS = {"ground_truth_role", "scenario_id"}


@dataclass(frozen=True)
class GeneratorOptions:
    output_dir: Path
    blueprint_path: Path
    version: str = "groundtruth-v1.0"
    seed: int = 20260714
    log_count: int = 2000
    query_count: int = 50
    incident_count: int = 15
    anomaly_count: int = 18


@dataclass
class GeneratedDataset:
    logs: list[JsonObject]
    incidents: list[JsonObject]
    anomalies: list[JsonObject]
    queries: list[JsonObject]


def generate(options: GeneratorOptions) -> GeneratedDataset:
    rng = random.Random(options.seed)
    blueprints = list(read_jsonl(options.blueprint_path))
    if options.incident_count > len(blueprints):
        raise ValueError(
            f"Requested {options.incident_count} incidents but only "
            f"{len(blueprints)} blueprints exist"
        )
    if options.log_count < options.incident_count * 80:
        raise ValueError("log_count is too small to preserve evidence interleaving")

    selected = blueprints[: options.incident_count]
    logs: list[JsonObject] = []
    incidents: list[JsonObject] = []

    def append_log(record: JsonObject) -> JsonObject:
        index = len(logs) + 1
        enriched = dict(record)
        enriched["log_id"] = sequence_id("demo", index)
        enriched["timestamp"] = isoformat_z(DEFAULT_START + timedelta(seconds=index - 1))
        enriched["raw_log"] = raw_log_for(enriched)
        logs.append(enriched)
        return enriched

    for incident_index, blueprint in enumerate(selected, start=1):
        add_noise_block(
            append_log,
            rng,
            count=rng.randint(3, 12),
            reason="normal_flow",
            incident_index=incident_index,
        )
        incident = emit_incident_logs(append_log, rng, blueprint)
        incidents.append(incident)

    while len(logs) < options.log_count:
        add_noise_block(
            append_log,
            rng,
            count=min(options.log_count - len(logs), rng.randint(8, 24)),
            reason="tail_background",
            incident_index=len(logs) + 1,
        )
    if len(logs) > options.log_count:
        raise RuntimeError("dataset generation exceeded requested log_count")

    log_by_id = {str(log["log_id"]): log for log in logs}
    anomalies = build_anomalies(logs, incidents, options.anomaly_count)
    queries = build_queries(incidents, log_by_id, options.query_count)
    return GeneratedDataset(logs=logs, incidents=incidents, anomalies=anomalies, queries=queries)


def emit_incident_logs(
    append_log: Any,
    rng: random.Random,
    blueprint: JsonObject,
) -> JsonObject:
    noise_plan = blueprint["noise_plan"]
    min_gap = int(noise_plan["interleave_min"])
    max_gap = int(noise_plan["interleave_max"])
    evidence_logs: list[JsonObject] = []
    required_log_ids: list[str] = []
    optional_log_ids: list[str] = []

    root_cause_log: JsonObject | None = None
    root_event = blueprint.get("root_cause_event")
    if isinstance(root_event, dict):
        root_cause_log = append_log(log_from_event(blueprint, root_event, role="root_cause"))
        evidence_logs.append(root_cause_log)
        required_log_ids.append(str(root_cause_log["log_id"]))

    for event_index, event in enumerate(blueprint["intermediate_events"], start=1):
        add_noise_block(
            append_log,
            rng,
            count=rng.randint(min_gap, max_gap),
            reason="interleaved_evidence_noise",
            incident_index=event_index,
        )
        role = "evidence" if event_index == 1 else "related"
        evidence_log = append_log(log_from_event(blueprint, event, role=role))
        evidence_logs.append(evidence_log)
        if root_cause_log is None and not required_log_ids:
            required_log_ids.append(str(evidence_log["log_id"]))
        else:
            optional_log_ids.append(str(evidence_log["log_id"]))

    add_noise_block(
        append_log,
        rng,
        count=rng.randint(min_gap, max_gap),
        reason="pre_incident_noise",
        incident_index=len(evidence_logs) + 1,
    )
    incident_log = append_log(log_from_event(blueprint, blueprint["incident_event"], role="incident"))
    evidence_logs.append(incident_log)
    optional_log_ids.append(str(incident_log["log_id"]))

    evidence_ids = [str(log["log_id"]) for log in evidence_logs]
    related_entities = dict(blueprint.get("entities", {}))
    root_cause_summary = root_cause_summary_for(blueprint)
    return {
        "incident_id": blueprint["incident_id"],
        "scenario_type": blueprint["scenario_type"],
        "incident_log_id": incident_log["log_id"],
        "root_cause_log_id": root_cause_log["log_id"] if root_cause_log else None,
        "evidence_log_ids": evidence_ids,
        "required_evidence_log_ids": required_log_ids,
        "optional_evidence_log_ids": optional_log_ids,
        "related_entities": related_entities,
        "root_cause_summary": root_cause_summary,
        "timeline_explanation": timeline_explanation_for(blueprint),
        "why_incident_is_not_root_cause": (
            "The incident log is the propagated symptom; the causal signal occurs earlier."
            if root_cause_log
            else "This silent scenario has no direct root-cause log, so RCA must rely on indirect evidence."
        ),
    }


def log_from_event(blueprint: JsonObject, event: JsonObject, *, role: str) -> JsonObject:
    entities = blueprint.get("entities", {})
    return {
        "dataset": blueprint["dataset"],
        "source_id": source_id_for(entities, event),
        "service": event["service"],
        "component": event["component"],
        "level": event["level"],
        "request_id": entities.get("request_id"),
        "instance_id": entities.get("instance_id"),
        "block_id": entities.get("block_id"),
        "template_id": event["template_id"],
        "message": event["message"],
        "scenario_id": blueprint["incident_id"],
        "ground_truth_role": role,
    }


NORMAL_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    ("T_REQUEST_COMPLETED", "INFO", "Request completed successfully"),
    ("T_HEARTBEAT_RECEIVED", "INFO", "Heartbeat received from service peer"),
    ("T_CONNECTION_ESTABLISHED", "INFO", "Connection established to dependency"),
    ("T_CACHE_REFRESHED", "INFO", "Cache refreshed successfully"),
    ("T_BACKGROUND_SYNC_DONE", "INFO", "Background sync completed"),
)

NOISE_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    ("T_GENERIC_TIMEOUT_NOISE", "WARN", "Timeout while refreshing cache"),
    ("T_ENTITY_COLLISION_NOISE", "WARN", "Retry for unrelated entity completed"),
    ("T_TEMPORAL_NOISE", "WARN", "Similar warning outside incident time window"),
    ("T_CROSS_SERVICE_NOISE", "ERROR", "Unrelated service returned transient error"),
    ("T_TEMPLATE_DUPLICATE_NOISE", "INFO", "Repeated normal template emitted"),
)


def add_noise_block(
    append_log: Any,
    rng: random.Random,
    *,
    count: int,
    reason: str,
    incident_index: int,
) -> None:
    for offset in range(count):
        if rng.random() < 0.65:
            template_id, level, message = rng.choice(NORMAL_TEMPLATES)
            role = "normal"
        else:
            template_id, level, message = rng.choice(NOISE_TEMPLATES)
            role = "noise"
        service = rng.choice(
            [
                "nova-api",
                "nova-compute",
                "cinder-volume",
                "neutron-server",
                "hdfs-datanode",
                "hdfs-namenode",
                "apache-httpd",
                "app-server",
            ]
        )
        request_id = f"req-noise-{incident_index:03d}-{offset:03d}"
        append_log(
            {
                "dataset": dataset_for_service(service),
                "source_id": f"{service}-node-{rng.randint(1, 4):02d}",
                "service": service,
                "component": component_for_service(service),
                "level": level,
                "request_id": request_id,
                "instance_id": f"inst-noise-{rng.randint(1, 25):03d}" if service.startswith("nova") else None,
                "block_id": f"blk-noise-{rng.randint(1, 25):03d}" if service.startswith("hdfs") else None,
                "template_id": template_id,
                "message": f"{message} ({reason})",
                "scenario_id": None,
                "ground_truth_role": role,
            }
        )


def build_anomalies(
    logs: list[JsonObject],
    incidents: list[JsonObject],
    anomaly_count: int,
) -> list[JsonObject]:
    log_by_id = {str(log["log_id"]): log for log in logs}
    records: list[JsonObject] = []

    positive_ids: list[str] = []
    for incident in incidents:
        root_id = incident.get("root_cause_log_id")
        if root_id:
            positive_ids.append(str(root_id))
        positive_ids.extend(str(item) for item in incident["required_evidence_log_ids"])
        positive_ids.append(str(incident["incident_log_id"]))
    positive_ids = dedupe(positive_ids)

    positive_target = max(1, min(len(positive_ids), anomaly_count // 2 + anomaly_count % 2))
    for log_id in positive_ids[:positive_target]:
        log = log_by_id[log_id]
        severity = "high" if log["ground_truth_role"] == "root_cause" else "medium"
        records.append(
            {
                "anomaly_id": sequence_id("anomaly", len(records) + 1, width=3),
                "incident_id": log.get("scenario_id"),
                "log_id": log_id,
                "expected_anomaly": True,
                "expected_severity": severity,
                "expected_score_range": [0.7, 1.0] if severity == "high" else [0.5, 0.9],
                "signals": anomaly_signals_for(log),
                "reason": f"{log['template_id']} is part of the controlled incident evidence chain.",
            }
        )

    negative_logs = [
        log
        for log in logs
        if log.get("ground_truth_role") in {"normal", "noise"}
        and str(log.get("level")) in {"INFO", "WARN"}
    ]
    for log in negative_logs:
        if len(records) >= anomaly_count:
            break
        records.append(
            {
                "anomaly_id": sequence_id("anomaly", len(records) + 1, width=3),
                "incident_id": None,
                "log_id": log["log_id"],
                "expected_anomaly": False,
                "expected_severity": "none",
                "expected_score_range": [0.0, 0.3],
                "signals": [],
                "reason": "Background or controlled noise remains within the expected baseline.",
            }
        )
    return records


def build_queries(
    incidents: list[JsonObject],
    log_by_id: dict[str, JsonObject],
    query_count: int,
) -> list[JsonObject]:
    query_types = (
        ["entity"] * 8
        + ["semantic"] * 10
        + ["service"] * 7
        + ["rca"] * 12
        + ["anomaly"] * 5
        + ["hard"] * 6
        + ["silent"] * 2
    )
    if query_count != len(query_types):
        base = query_types
        query_types = [base[index % len(base)] for index in range(query_count)]
    difficulties = difficulty_plan(query_count)

    queries: list[JsonObject] = []
    incident_index = 0
    silent_incidents = [incident for incident in incidents if incident["scenario_type"] == "silent_root_cause"]
    for index, query_type in enumerate(query_types[:query_count], start=1):
        if query_type == "silent" and silent_incidents:
            incident = silent_incidents[(index - 1) % len(silent_incidents)]
        else:
            incident = incidents[incident_index % len(incidents)]
            incident_index += 1

        expected_ids = [str(item) for item in incident["evidence_log_ids"]]
        required_ids = [str(item) for item in incident["required_evidence_log_ids"]]
        relevance = relevance_judgments_for(incident)
        templates = dedupe(str(log_by_id[log_id]["template_id"]) for log_id in expected_ids)
        query_text = query_text_for(query_type, incident, log_by_id)

        queries.append(
            {
                "query_id": query_id(index),
                "query": query_text,
                "query_type": "rca" if query_type in {"rca", "hard", "silent"} else query_type,
                "difficulty": difficulties[index - 1],
                "incident_id": incident["incident_id"],
                "expected_log_ids": expected_ids,
                "required_log_ids": required_ids,
                "root_cause_log_id": incident.get("root_cause_log_id"),
                "expected_template_ids": templates,
                "relevance_judgments": relevance,
                "expected_answer_concepts": answer_concepts_for(incident, log_by_id),
            }
        )
    return queries


def relevance_judgments_for(incident: JsonObject) -> dict[str, int]:
    judgments: dict[str, int] = {}
    root_id = incident.get("root_cause_log_id")
    for log_id in incident["evidence_log_ids"]:
        judgments[str(log_id)] = 2
    for log_id in incident["required_evidence_log_ids"]:
        judgments[str(log_id)] = 3 if root_id else 2
    if root_id:
        judgments[str(root_id)] = 3
    return judgments


def query_text_for(query_type: str, incident: JsonObject, log_by_id: dict[str, JsonObject]) -> str:
    entities = incident["related_entities"]
    incident_log = log_by_id[str(incident["incident_log_id"])]
    root_id = incident.get("root_cause_log_id")
    root_log = log_by_id[str(root_id)] if root_id else None
    request_id = entities.get("request_id", "the affected request")
    entity = (
        entities.get("instance_id")
        or entities.get("block_id")
        or entities.get("session_id")
        or entities.get("token_id")
        or request_id
    )
    service = root_log["service"] if root_log else incident_log["service"]
    if query_type == "entity":
        return f"Find the important logs for {entity} and request {request_id}."
    if query_type == "semantic":
        return f"Find evidence explaining the degradation that led to {incident_log['template_id']}."
    if query_type == "service":
        return f"Show {service} events connected to incident {incident['incident_id']}."
    if query_type == "anomaly":
        return f"Which anomalous events appear around incident {incident['incident_id']}?"
    if query_type == "hard":
        return f"Find the earlier cause, not just the final symptom, for {entity}."
    if query_type == "silent":
        return f"Explain the incident for {entity} when no direct root-cause error was emitted."
    return f"Why did {entity} fail in incident {incident['incident_id']}?"


def difficulty_plan(count: int) -> list[str]:
    if count == 50:
        return ["easy"] * 15 + ["medium"] * 20 + ["hard"] * 15
    levels = ["easy", "medium", "hard"]
    return [levels[index % len(levels)] for index in range(count)]


def answer_concepts_for(incident: JsonObject, log_by_id: dict[str, JsonObject]) -> list[str]:
    concepts = [str(incident["root_cause_summary"])]
    for log_id in incident["required_evidence_log_ids"]:
        concepts.append(str(log_by_id[str(log_id)]["template_id"]))
    concepts.append(str(log_by_id[str(incident["incident_log_id"])]["template_id"]))
    return dedupe(concepts)


def root_cause_summary_for(blueprint: JsonObject) -> str:
    root_event = blueprint.get("root_cause_event")
    if isinstance(root_event, dict):
        return str(root_event["message"])
    hidden = blueprint.get("hidden_root_cause", {})
    if isinstance(hidden, dict):
        return str(hidden.get("summary", blueprint["description"]))
    return str(blueprint["description"])


def timeline_explanation_for(blueprint: JsonObject) -> str:
    event_names: list[str] = []
    root_event = blueprint.get("root_cause_event")
    if isinstance(root_event, dict):
        event_names.append(str(root_event["template_id"]))
    event_names.extend(str(event["template_id"]) for event in blueprint["intermediate_events"])
    event_names.append(str(blueprint["incident_event"]["template_id"]))
    return " -> ".join(event_names)


def raw_log_for(log: JsonObject) -> str:
    return (
        f"{log['timestamp']} {log['level']} {log['service']} "
        f"{log['component']}: {log['message']}"
    )


def source_id_for(entities: JsonObject, event: JsonObject) -> str:
    if entities.get("host"):
        return str(entities["host"])
    if entities.get("datanode"):
        return str(entities["datanode"])
    service = str(event.get("service", "service"))
    return f"{service}-node-01"


def dataset_for_service(service: str) -> str:
    if service.startswith("hdfs"):
        return "hdfs"
    if service.startswith("apache") or service == "app-server":
        return "apache"
    return "openstack"


def component_for_service(service: str) -> str:
    mapping = {
        "nova-api": "nova.api.openstack.compute",
        "nova-compute": "nova.compute.manager",
        "cinder-volume": "cinder.volume.manager",
        "neutron-server": "neutron.plugins.ml2.managers",
        "hdfs-datanode": "dfs.DataNode",
        "hdfs-namenode": "dfs.FSNamesystem",
        "apache-httpd": "mod_proxy",
        "app-server": "request.router",
    }
    return mapping.get(service, f"{service}.component")


def anomaly_signals_for(log: JsonObject) -> list[str]:
    role = str(log.get("ground_truth_role"))
    signals = ["entity_linkage"]
    if role == "root_cause":
        signals.insert(0, "template_rarity")
    if str(log.get("level")) in {"WARN", "ERROR"}:
        signals.append("sequence_anomaly")
    return dedupe(signals)


def dedupe(values: Any) -> list[Any]:
    seen: set[Any] = set()
    result: list[Any] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def write_dataset(dataset: GeneratedDataset, options: GeneratorOptions) -> dict[str, Any]:
    ensure_dir(options.output_dir)
    files = {
        "logs.jsonl": dataset.logs,
        "groundtruth_queries.jsonl": dataset.queries,
        "anomalies.jsonl": dataset.anomalies,
        "incidents.jsonl": dataset.incidents,
    }
    output_paths: list[Path] = []
    for filename, records in files.items():
        path = options.output_dir / filename
        write_jsonl(path, records)
        output_paths.append(path)

    manifest = {
        "dataset_version": options.version,
        "seed": options.seed,
        "log_count": len(dataset.logs),
        "query_count": len(dataset.queries),
        "incident_count": len(dataset.incidents),
        "anomaly_count": len(dataset.anomalies),
        "created_at": DEFAULT_START.date().isoformat(),
        "files": manifest_for_files(output_paths, base_dir=options.output_dir),
        "notes": "Initial deterministic synthetic controlled evaluation dataset.",
    }
    write_json(options.output_dir / "dataset_manifest.json", manifest)
    return manifest


def options_from_args(args: argparse.Namespace) -> GeneratorOptions:
    config = load_config(args.config) if args.config else EvaluationConfig()
    output_dir = Path(args.output_dir) if args.output_dir else dataset_dir()
    blueprint_path = Path(args.blueprint_path) if args.blueprint_path else scenarios_dir() / "incident_blueprints.jsonl"
    return GeneratorOptions(
        output_dir=output_dir,
        blueprint_path=blueprint_path,
        version=args.version or config.dataset.version,
        seed=args.seed if args.seed is not None else config.dataset.seed,
        log_count=args.log_count if args.log_count is not None else config.dataset.log_count,
        query_count=args.query_count if args.query_count is not None else config.dataset.query_count,
        incident_count=args.incident_count if args.incident_count is not None else config.dataset.incident_count,
        anomaly_count=args.anomaly_count if args.anomaly_count is not None else config.dataset.anomaly_count,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--blueprint-path", type=Path)
    parser.add_argument("--version")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--log-count", type=int)
    parser.add_argument("--query-count", type=int)
    parser.add_argument("--incident-count", type=int)
    parser.add_argument("--anomaly-count", type=int)
    return parser.parse_args()


def main() -> None:
    options = options_from_args(parse_args())
    dataset = generate(options)
    manifest = write_dataset(dataset, options)
    print(
        "Generated dataset: "
        f"logs={manifest['log_count']}, "
        f"queries={manifest['query_count']}, "
        f"incidents={manifest['incident_count']}, "
        f"anomalies={manifest['anomaly_count']}, "
        f"seed={manifest['seed']}"
    )


if __name__ == "__main__":
    main()
