"""Build stable retrieval context dictionaries for RAG and UI consumers."""

from __future__ import annotations

from typing import Any

from src.retrieval.milvus_search import RetrievalResponse, RetrievalResult
from src.retrieval.query_plan import RetrievalPlan


def compact_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if item is not None and item != [] and item != {}
    }


def result_payload(result: RetrievalResult) -> dict[str, Any]:
    payload = result.entity.get("payload", {})
    return payload if isinstance(payload, dict) else {}


def log_result_to_context(result: RetrievalResult) -> dict[str, Any]:
    payload = result_payload(result)
    return compact_dict(
        {
            "log_id": result.primary_id,
            "dataset": result.entity.get("dataset"),
            "timestamp_ms": result.entity.get("timestamp_ms"),
            "timestamp": payload.get("timestamp"),
            "level": result.entity.get("level"),
            "component": result.entity.get("component"),
            "template_id": result.entity.get("template_id") or payload.get("template_id"),
            "score": result.score,
            "semantic_score": result.semantic_score,
            "source": result.source,
            "raw_log": payload.get("raw_log"),
            "message": payload.get("message"),
            "template": payload.get("template"),
            "signals": payload.get("signals"),
            "line_number": payload.get("line_number"),
            "source_file": payload.get("source_file"),
            "source_log": payload.get("source_log"),
            "request_id": payload.get("request_id"),
            "instance_id": payload.get("instance_id"),
            "block_id": payload.get("block_id"),
            "ip": payload.get("ip"),
            "http_status": payload.get("http_status"),
            "duration_ms": payload.get("duration_ms"),
        }
    )


def template_result_to_context(result: RetrievalResult) -> dict[str, Any]:
    payload = result_payload(result)
    return compact_dict(
        {
            "template_id": result.primary_id,
            "dataset": result.entity.get("dataset"),
            "level": result.entity.get("level"),
            "component": result.entity.get("component"),
            "occurrences": result.entity.get("occurrences"),
            "score": result.score,
            "semantic_score": result.semantic_score,
            "source": result.source,
            "template": payload.get("template"),
            "signals": payload.get("signals"),
            "entities": payload.get("entities"),
            "sample_log_ids": payload.get("sample_log_ids"),
            "sample_messages": payload.get("sample_messages"),
            "first_timestamp_ms": payload.get("first_timestamp_ms"),
            "last_timestamp_ms": payload.get("last_timestamp_ms"),
        }
    )


def sorted_logs_for_context(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(log: dict[str, Any]) -> tuple[int, int, str]:
        timestamp = log.get("timestamp_ms")
        if isinstance(timestamp, int):
            return (0, timestamp, str(log.get("log_id") or ""))
        return (1, 0, str(log.get("log_id") or ""))

    return sorted(logs, key=sort_key)


def build_template_refs(
    templates: list[dict[str, Any]],
    logs: list[dict[str, Any]],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    refs: dict[str, str] = {}
    template_map: list[dict[str, Any]] = []

    def register(template_id: str, template: dict[str, Any] | None = None) -> None:
        if not template_id or template_id in refs:
            return
        ref = f"T{len(refs) + 1:02d}"
        refs[template_id] = ref
        record = compact_dict(
            {
                "template_ref": ref,
                "template_id": template_id,
                "dataset": (template or {}).get("dataset"),
                "level": (template or {}).get("level"),
                "component": (template or {}).get("component"),
                "occurrences": (template or {}).get("occurrences"),
                "score": (template or {}).get("score"),
                "template": (template or {}).get("template"),
                "signals": (template or {}).get("signals"),
                "sample_messages": (template or {}).get("sample_messages"),
            }
        )
        template_map.append(record)

    for template in templates:
        register(str(template.get("template_id") or ""), template)
    for log in logs:
        register(
            str(log.get("template_id") or ""),
            {
                "dataset": log.get("dataset"),
                "level": log.get("level"),
                "component": log.get("component"),
                "template": log.get("template"),
                "signals": log.get("signals"),
            },
        )
    return refs, template_map


def build_retrieval_context(
    *,
    query: str,
    plan: RetrievalPlan,
    response: RetrievalResponse,
    include_templates: bool = True,
) -> dict[str, Any]:
    logs = sorted_logs_for_context(
        [log_result_to_context(result) for result in response.log_lines]
    )
    templates = (
        [template_result_to_context(result) for result in response.templates]
        if include_templates
        else []
    )
    template_refs, template_map = build_template_refs(templates, logs)
    for index, log in enumerate(logs, start=1):
        log["line_id"] = f"L{index:02d}"
        template_id = str(log.get("template_id") or "")
        if template_id:
            log["template_ref"] = template_refs.get(template_id)
    for template in templates:
        template_id = str(template.get("template_id") or "")
        if template_id:
            template["template_ref"] = template_refs.get(template_id)

    context = {
        "query": query,
        "plan": plan.model_dump(mode="json"),
        "retrieval": {
            "mode": response.mode,
            "filter_expr": response.filter_expr,
        },
        "logs": logs,
        "template_map": template_map,
    }
    if include_templates:
        context["templates"] = templates
    return context


def format_score(score: Any) -> str:
    if isinstance(score, (float, int)):
        return f"{float(score):.3f}"
    return "null"


def format_context_for_prompt(context: dict[str, Any]) -> str:
    plan = context.get("plan") or {}
    retrieval = context.get("retrieval") or {}
    lines = [
        "[QUERY]",
        f"raw_query={context.get('query')}",
        f"semantic_query={plan.get('semantic_query')}",
        "",
        "[RETRIEVAL]",
        f"mode={retrieval.get('mode')}",
        f"filter_expr={retrieval.get('filter_expr')}",
        f"vector_search={plan.get('use_vector_search')}",
        f"template_filter_applied={plan.get('applied_template_filter')}",
        f"fallback_used={plan.get('fallback_used')}",
        f"candidate_template_ids={plan.get('candidate_template_ids') or []}",
        "",
        "[TEMPLATE_MAP]",
    ]

    template_map = context.get("template_map") or []
    if template_map:
        for template in template_map:
            lines.append(
                f"{template.get('template_ref')} | template_id={template.get('template_id')} "
                f"| level={template.get('level')} | component={template.get('component')} "
                f"| score={format_score(template.get('score'))} "
                f"| occurrences={template.get('occurrences')}"
            )
            lines.append(f"template={template.get('template')}")
            signals = template.get("signals")
            if signals:
                lines.append(f"signals={signals}")
    else:
        lines.append("none")

    lines.extend(["", "[LOGS_SORTED_BY_TIME]"])
    logs = context.get("logs", [])
    if not logs:
        lines.append("none")
    for log in logs:
        line_id = log.get("line_id")
        template_ref = log.get("template_ref") or "T??"
        lines.append(
            f"[{line_id}] ts={log.get('timestamp_ms')} | {template_ref} | {log.get('level')} "
            f"| component={log.get('component')} | score={format_score(log.get('score'))}"
        )
        lines.append(
            f"meta=log_id={log.get('log_id')} dataset={log.get('dataset')} "
            f"source_file={log.get('source_file')} line_number={log.get('line_number')}"
        )
        raw = log.get("raw_log") or log.get("message") or ""
        lines.append(f"raw={raw}")

    lines.extend(
        [
            "",
            "[ANSWER_RULES]",
            "- Use only the evidence in [LOGS_SORTED_BY_TIME] and [TEMPLATE_MAP].",
            "- Cite line_id such as [L01] for every concrete claim.",
            "- Prefer chronological causality: earlier lines may explain later symptoms.",
            "- Separate likely root cause, symptoms/effects, and next checks.",
            "- Do not cite template refs as evidence unless no log line supports the claim.",
            "- If evidence is insufficient, say exactly what is missing.",
        ]
    )
    return "\n".join(lines)
