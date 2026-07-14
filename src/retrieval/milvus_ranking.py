"""Pure ranking and result-capping logic for Milvus retrieval."""

from __future__ import annotations

import math

from src.retrieval.milvus_models import RetrievalConfig, RetrievalResult
from src.retrieval.query_plan import RetrievalPlan


def result_payload_template_id(result: RetrievalResult) -> str | None:
    payload = result.entity.get("payload")
    if isinstance(payload, dict):
        value = payload.get("template_id")
        return str(value) if value else None
    return None


def occurrence_bonus(template_result: RetrievalResult, query: str) -> float:
    occurrences = int(template_result.entity.get("occurrences") or 0)
    if occurrences <= 0:
        return 0.0
    scaled = min(math.log1p(occurrences) / 10.0, 0.08)
    lowered = query.lower()
    if any(term in lowered for term in ("hiếm", "bất thường", "rare", "anomaly", "outlier")):
        return -scaled
    return scaled


def source_boost(template_result: RetrievalResult) -> float:
    return 0.05 if template_result.source in {"template_registry", "template_lookup"} else 0.0


def rerank_templates(templates: list[RetrievalResult], query: str) -> list[RetrievalResult]:
    reranked = []
    for template in templates:
        bonus = occurrence_bonus(template, query)
        reranked.append(
            RetrievalResult(
                collection=template.collection,
                primary_id=template.primary_id,
                score=template.semantic_score + bonus + source_boost(template),
                semantic_score=template.semantic_score,
                entity=template.entity,
                source=template.source,
            )
        )
    return sorted(reranked, key=lambda item: item.score, reverse=True)


def template_score_map(templates: list[RetrievalResult]) -> dict[str, float]:
    return {template.primary_id: template.score for template in templates}


def rerank_template_child_lines(
    lines: list[RetrievalResult],
    templates: list[RetrievalResult],
    *,
    line_weight: float = 0.65,
    template_weight: float = 0.35,
) -> list[RetrievalResult]:
    scores = template_score_map(templates)
    reranked = []
    for line in lines:
        template_id = str(line.entity.get("template_id") or "")
        parent_score = scores.get(template_id, line.semantic_score)
        final_score = line_weight * line.semantic_score + template_weight * parent_score
        reranked.append(
            RetrievalResult(
                collection=line.collection,
                primary_id=line.primary_id,
                score=final_score,
                semantic_score=line.semantic_score,
                entity=line.entity,
                source=line.source,
            )
        )
    return sorted(reranked, key=lambda item: item.score, reverse=True)


def merge_results(*groups: list[RetrievalResult], limit: int) -> list[RetrievalResult]:
    merged: dict[str, RetrievalResult] = {}
    for group in groups:
        for item in group:
            current = merged.get(item.primary_id)
            if current is None or item.score > current.score:
                merged[item.primary_id] = item
    return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:limit]


def cap_logs_per_template(
    lines: list[RetrievalResult],
    *,
    logs_per_template: int,
    limit: int,
) -> list[RetrievalResult]:
    if logs_per_template < 1:
        return lines[:limit]
    counts: dict[str, int] = {}
    capped: list[RetrievalResult] = []
    for line in lines:
        template_id = str(line.entity.get("template_id") or result_payload_template_id(line) or "")
        group_key = template_id or line.primary_id
        current = counts.get(group_key, 0)
        if current >= logs_per_template:
            continue
        counts[group_key] = current + 1
        capped.append(line)
        if len(capped) >= limit:
            break
    return capped


def result_timestamp_ms(result: RetrievalResult) -> int | None:
    value = result.entity.get("timestamp_ms")
    if value is None:
        payload = result.entity.get("payload")
        if isinstance(payload, dict):
            value = payload.get("timestamp_ms")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_semantic_score(score: float) -> float:
    if math.isnan(score):
        return 0.0
    return max(0.0, min(1.0, score))


def template_group_key(line: RetrievalResult) -> str:
    return str(line.entity.get("template_id") or result_payload_template_id(line) or line.primary_id)


def is_temporal_sort(plan: RetrievalPlan) -> bool:
    return plan.sort is not None and plan.sort.field == "timestamp_ms"


def rerank_template_group(
    lines: list[RetrievalResult],
    *,
    plan: RetrievalPlan,
    config: RetrievalConfig,
) -> list[RetrievalResult]:
    if not lines:
        return []
    if is_temporal_sort(plan):
        reverse = plan.sort is None or plan.sort.order == "desc"
        return sorted(
            lines,
            key=lambda line: result_timestamp_ms(line) if result_timestamp_ms(line) is not None else -1,
            reverse=reverse,
        )
    if not config.enable_recency_rerank or config.recency_weight <= 0:
        return sorted(lines, key=lambda line: line.score, reverse=True)

    timestamps = [timestamp for line in lines if (timestamp := result_timestamp_ms(line)) is not None]
    min_timestamp = min(timestamps) if timestamps else None
    max_timestamp = max(timestamps) if timestamps else None
    timestamp_span = (
        max_timestamp - min_timestamp
        if min_timestamp is not None and max_timestamp is not None
        else 0
    )
    total_weight = config.semantic_weight + config.recency_weight
    semantic_weight = config.semantic_weight / total_weight if total_weight > 0 else 1.0
    recency_weight = config.recency_weight / total_weight if total_weight > 0 else 0.0
    weighted: list[RetrievalResult] = []
    for line in lines:
        timestamp = result_timestamp_ms(line)
        recency_score = (
            (timestamp - min_timestamp) / timestamp_span
            if timestamp is not None and min_timestamp is not None and timestamp_span > 0
            else 0.0
        )
        weighted.append(
            RetrievalResult(
                collection=line.collection,
                primary_id=line.primary_id,
                score=(
                    semantic_weight * normalize_semantic_score(line.semantic_score)
                    + recency_weight * recency_score
                ),
                semantic_score=line.semantic_score,
                entity=line.entity,
                source=line.source,
            )
        )
    return sorted(
        weighted,
        key=lambda line: (
            line.score,
            result_timestamp_ms(line) if result_timestamp_ms(line) is not None else -1,
            line.semantic_score,
        ),
        reverse=True,
    )


def rerank_and_cap_lines(
    lines: list[RetrievalResult],
    *,
    plan: RetrievalPlan,
    config: RetrievalConfig,
    limit: int,
) -> list[RetrievalResult]:
    grouped: dict[str, list[RetrievalResult]] = {}
    for line in lines:
        grouped.setdefault(template_group_key(line), []).append(line)

    selected: list[RetrievalResult] = []
    for group in grouped.values():
        selected.extend(
            rerank_template_group(group, plan=plan, config=config)[: config.logs_per_template]
        )

    if is_temporal_sort(plan):
        reverse = plan.sort is None or plan.sort.order == "desc"
        selected.sort(
            key=lambda line: result_timestamp_ms(line) if result_timestamp_ms(line) is not None else -1,
            reverse=reverse,
        )
    else:
        selected.sort(key=lambda line: line.score, reverse=True)
    return selected[:limit]
