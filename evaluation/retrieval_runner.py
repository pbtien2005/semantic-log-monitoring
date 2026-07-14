"""Evaluation-only retrieval experiment runner."""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from evaluation.io import JsonObject, read_jsonl, write_jsonl


SUPPORTED_EXPERIMENTS = {
    "baseline_log_only_v1",
    "template_first_recency_v1",
}

TOKEN_RE = re.compile(r"[a-zA-Z0-9_.$:-]+")
ID_RE = re.compile(r"\b(?:req|inst|blk|vol|port|session|token|img|user)-[a-zA-Z0-9_.:-]+\b")
SERVICE_RE = re.compile(
    r"\b(?:nova-api|nova-compute|cinder-volume|neutron-server|keystone|glance-api|"
    r"hdfs-datanode|hdfs-namenode|apache-httpd|app-server|rabbitmq|memcached)\b"
)


@dataclass(frozen=True)
class RetrievalRunOptions:
    logs_path: Path
    queries_path: Path
    output_path: Path
    experiment: str
    top_k: int = 24
    limit: int | None = None


def run_retrieval_evaluation(options: RetrievalRunOptions) -> int:
    if options.experiment not in SUPPORTED_EXPERIMENTS:
        raise ValueError(f"Unsupported experiment: {options.experiment}")
    if options.top_k < 1:
        raise ValueError("top_k must be positive")
    if options.limit is not None and options.limit < 1:
        raise ValueError("limit must be positive when provided")

    logs = list(read_jsonl(options.logs_path))
    queries = list(read_jsonl(options.queries_path))
    if options.limit is not None:
        queries = queries[: options.limit]

    index = build_index(logs)
    results = [
        evaluate_query(query, index=index, experiment=options.experiment, top_k=options.top_k)
        for query in queries
    ]
    return write_jsonl(options.output_path, results)


@dataclass(frozen=True)
class RetrievalIndex:
    logs: list[JsonObject]
    log_tokens: list[set[str]]
    avg_position: float


def build_index(logs: list[JsonObject]) -> RetrievalIndex:
    if not logs:
        raise ValueError("logs dataset is empty")
    return RetrievalIndex(
        logs=logs,
        log_tokens=[set(tokens(log_text(log))) for log in logs],
        avg_position=(len(logs) - 1) / 2,
    )


def evaluate_query(
    query: JsonObject,
    *,
    index: RetrievalIndex,
    experiment: str,
    top_k: int,
) -> JsonObject:
    started = time.perf_counter()
    query_text = str(query.get("query") or "")
    query_terms = set(tokens(query_text))
    entity_terms = set(extract_entities(query_text))
    service_terms = set(SERVICE_RE.findall(query_text))

    scored: list[tuple[float, int, JsonObject]] = []
    for position, log in enumerate(index.logs):
        if experiment == "baseline_log_only_v1":
            score = baseline_score(query_terms, index.log_tokens[position])
        else:
            score = template_first_score(
                query_terms,
                entity_terms,
                service_terms,
                log,
                index.log_tokens[position],
                position=position,
                total=max(1, len(index.logs) - 1),
            )
        if score > 0:
            scored.append((score, position, log))

    if experiment == "template_first_recency_v1":
        ranked = diversify_by_template(scored, top_k=top_k)
    else:
        ranked = sorted(scored, key=lambda item: (-item[0], item[1]))[:top_k]

    latency_ms = (time.perf_counter() - started) * 1000
    logs = [item[2] for item in ranked]
    scores = [round(item[0], 6) for item in ranked]
    template_ids = [str(log.get("template_id") or "") for log in logs]
    unique_template_count = len({template_id for template_id in template_ids if template_id})
    retrieved_count = len(logs)
    duplicate_template_ratio = (
        0.0 if retrieved_count == 0 else 1 - unique_template_count / retrieved_count
    )
    return {
        "query_id": query.get("query_id"),
        "experiment": experiment,
        "retrieved_log_ids": [log.get("log_id") for log in logs],
        "retrieved_template_ids": template_ids,
        "scores": scores,
        "latency_ms": round(latency_ms, 3),
        "timings": {
            "local_scoring_ms": round(latency_ms, 3),
        },
        "unique_template_count": unique_template_count,
        "duplicate_template_ratio": round(duplicate_template_ratio, 6),
    }


def baseline_score(query_terms: set[str], log_terms: set[str]) -> float:
    if not query_terms:
        return 0.0
    overlap = query_terms & log_terms
    if not overlap:
        return 0.0
    precision_like = len(overlap) / len(query_terms)
    rarity_boost = sum(1.0 / math.sqrt(max(1, len(term))) for term in overlap)
    return precision_like + 0.05 * rarity_boost


def template_first_score(
    query_terms: set[str],
    entity_terms: set[str],
    service_terms: set[str],
    log: JsonObject,
    log_terms: set[str],
    *,
    position: int,
    total: int,
) -> float:
    score = baseline_score(query_terms, log_terms)
    log_text_value = log_text(log).casefold()
    for entity in entity_terms:
        if entity.casefold() in log_text_value:
            score += 2.0
    service = str(log.get("service") or "")
    component = str(log.get("component") or "")
    if service in service_terms or component in service_terms:
        score += 1.0
    template_id = str(log.get("template_id") or "").casefold()
    template_terms = set(tokens(template_id.replace("_", " ")))
    score += 0.35 * len(query_terms & template_terms)
    level = str(log.get("level") or "").upper()
    if level == "ERROR":
        score += 0.2
    elif level == "WARN":
        score += 0.1
    recency = position / total
    score += 0.05 * recency
    return score


def diversify_by_template(
    scored: list[tuple[float, int, JsonObject]],
    *,
    top_k: int,
    per_template_limit: int = 3,
) -> list[tuple[float, int, JsonObject]]:
    ranked = sorted(scored, key=lambda item: (-item[0], item[1]))
    selected: list[tuple[float, int, JsonObject]] = []
    template_counts: dict[str, int] = {}
    deferred: list[tuple[float, int, JsonObject]] = []
    for item in ranked:
        template_id = str(item[2].get("template_id") or "")
        current = template_counts.get(template_id, 0)
        if current < per_template_limit:
            selected.append(item)
            template_counts[template_id] = current + 1
        else:
            deferred.append(item)
        if len(selected) >= top_k:
            return selected
    for item in deferred:
        selected.append(item)
        if len(selected) >= top_k:
            break
    return selected


def tokens(value: str) -> list[str]:
    return [token.casefold() for token in TOKEN_RE.findall(value)]


def extract_entities(value: str) -> list[str]:
    return ID_RE.findall(value)


def log_text(log: JsonObject) -> str:
    return " ".join(
        str(log.get(key) or "")
        for key in (
            "log_id",
            "dataset",
            "source_id",
            "service",
            "component",
            "level",
            "request_id",
            "instance_id",
            "block_id",
            "template_id",
            "message",
            "raw_log",
        )
    )
