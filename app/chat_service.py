"""Chat service for React dashboard questions."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

from app.chat_query_utils import (
    extract_log_id as extract_log_id,
    extract_query_level,
    extract_query_terms,
    extract_rca_lookback_ms,
    extract_recent_window_hours,
    is_rca_query,
    is_recent_log_query as is_recent_log_query,
    normalize_filter,
    normalize_query_text,
    single_level,
)
from app.chat_log_utils import (
    coerce_timestamp_ms,
    fallback_answer,
    filter_rca_scope,
    find_incident_log,
    float_or_zero as float_or_zero,
    load_local_logs,
    load_online_rca_logs,
    normalize_context_logs,
    normalize_log_payload,
    online_raw_log_to_rca_log as online_raw_log_to_rca_log,
    rank_local_logs,
    sort_logs_newest,
    summarize_context,
    text_value,
    timestamp_to_ms as timestamp_to_ms,
    truncate,
    upsert_log_by_identity,
)
from app.rca_presenter import (
    build_rca_answer_context,
    format_rca_answer,
    rca_candidate_details as rca_candidate_details,
    rca_log_to_context as rca_log_to_context,
    summarize_rca_context,
)
from src.rag.answer import DEFAULT_RAG_BASE_URL, DEFAULT_RAG_MODEL, generate_answer
from src.rca import rank_rca_evidence
from src.retrieval.context_builder import build_retrieval_context
from src.retrieval.milvus_search import DEFAULT_MODEL, DEFAULT_URI, execute_plan
from src.retrieval.pending_template_registry import PendingTemplateRegistry
from src.retrieval.query_plan import RetrievalPlan, TimeRange
from src.retrieval.query_planner import (
    PlannerOptions,
    plan_query,
)
from src.retrieval.template_registry import TemplateRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatSettings:
    enable_rag: bool = os.getenv("ENABLE_RAG_CHAT", "1") != "0"
    milvus_uri: str = os.getenv("MILVUS_URI", DEFAULT_URI)
    embedding_model: str = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)
    answer_model: str = os.getenv("CLIPROXY_MODEL", DEFAULT_RAG_MODEL)
    answer_base_url: str = os.getenv("CLIPROXY_BASE_URL", DEFAULT_RAG_BASE_URL)
    top_k: int = int(os.getenv("CHAT_TOP_K", "24"))
    template_k: int = int(os.getenv("CHAT_TEMPLATE_K", "8"))


@lru_cache(maxsize=4)
def get_milvus_client(uri: str) -> Any:
    from pymilvus import MilvusClient

    return MilvusClient(uri=uri)


@lru_cache(maxsize=2)
def get_embedding_model(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


@lru_cache(maxsize=1)
def get_template_registry() -> TemplateRegistry:
    return TemplateRegistry.load(PROJECT_ROOT)


@lru_cache(maxsize=1)
def get_pending_template_registry() -> PendingTemplateRegistry:
    return PendingTemplateRegistry.load(PROJECT_ROOT)


def clear_rag_dependency_caches() -> None:
    get_milvus_client.cache_clear()
    get_embedding_model.cache_clear()
    get_template_registry.cache_clear()
    get_pending_template_registry.cache_clear()


def answer_chat_query(
    query: str,
    *,
    dataset: str | None = None,
    component: str | None = None,
    levels: Sequence[str] | None = None,
    mode: str | None = None,
    incident_log: dict[str, Any] | None = None,
    context_logs: Sequence[dict[str, Any]] | None = None,
    settings: ChatSettings | None = None,
) -> dict[str, Any]:
    active_settings = settings or ChatSettings()
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query is required")

    if is_rca_query(normalized_query, mode=mode, incident_log=incident_log):
        return answer_rca_query(
            normalized_query,
            dataset=normalize_filter(dataset),
            component=normalize_filter(component),
            levels=levels,
            incident_log=incident_log,
            context_logs=context_logs,
            settings=active_settings,
        )

    if not active_settings.enable_rag:
        return {
            "answer": fallback_answer(normalized_query),
            "source": "fallback",
            "context": None,
        }

    try:
        context, answer = run_rag_pipeline(
            query=normalized_query,
            dataset=normalize_filter(dataset),
            component=normalize_filter(component),
            level=single_level(levels),
            settings=active_settings,
        )
    except Exception as exc:  # pragma: no cover - exercised in integration environments.
        logger.warning("RAG pipeline failed; using local logs: %s", exc)
        return {
            "answer": answer_from_local_logs(
                normalized_query,
                dataset=normalize_filter(dataset),
                component=normalize_filter(component),
                levels=levels,
                rag_error=exc,
            ),
            "source": "local",
            "context": {"error": str(exc)},
        }

    return {
        "answer": answer or fallback_answer(normalized_query),
        "source": "rag" if answer else "fallback",
        "context": summarize_context(context),
    }


def run_rag_pipeline(
    *,
    query: str,
    dataset: str | None,
    component: str | None,
    level: str | None,
    settings: ChatSettings,
) -> tuple[dict[str, Any], str | None]:
    plan = plan_query(
        query,
        PlannerOptions(
            dataset=dataset,
            level=level,
            component=component,
            top_k=settings.top_k,
        ),
    )
    client = get_milvus_client(settings.milvus_uri)
    model = get_embedding_model(settings.embedding_model) if plan.use_vector_search else None
    registry = get_template_registry() if plan.use_vector_search else None
    pending_registry = get_pending_template_registry() if plan.use_vector_search else None
    response = execute_plan(
        client=client,
        model=model,
        plan=plan,
        template_k=settings.template_k,
        template_registry=registry,
        pending_template_registry=pending_registry,
    )
    context = build_retrieval_context(
        query=query,
        plan=plan,
        response=response,
        include_templates=True,
    )
    return (
        context,
        generate_answer(
            context,
            model=settings.answer_model,
            base_url=settings.answer_base_url,
        ),
    )


def answer_recent_logs(
    query: str,
    *,
    dataset: str | None,
    component: str | None,
    levels: Sequence[str] | None,
    limit: int = 5,
) -> str:
    logs = load_local_logs()
    if dataset:
        logs = [log for log in logs if log["dataset"] == dataset]
    if component:
        logs = [log for log in logs if log["service"] == component]
    selected_levels = {level.upper() for level in levels or []}
    if selected_levels:
        logs = [log for log in logs if log["level"] in selected_levels]

    logs = [log for log in logs if log["parsed_timestamp"] is not None]
    if not logs:
        return "Không có log phù hợp với bộ lọc hiện tại."

    hours = extract_recent_window_hours(query)
    latest = max(log["parsed_timestamp"] for log in logs)
    assert latest is not None
    start = latest - timedelta(hours=hours)
    rows = sorted(
        [log for log in logs if log["parsed_timestamp"] and log["parsed_timestamp"] >= start],
        key=lambda item: item["parsed_timestamp"],
        reverse=True,
    )[:limit]

    if not rows:
        return f"Không có log nào trong {hours} tiếng gần nhất theo mốc dữ liệu hiện có."

    lines = [
        (
            f"Đây là {len(rows)} log mới nhất trong {hours} tiếng gần đây theo mốc dữ liệu hiện có "
            f"({start} -> {latest}):"
        )
    ]
    for row in rows:
        lines.append(
            f"- {row['timestamp']} {row['level']} {row['service']}: {truncate(row['message'], 180)}"
        )
    return "\n".join(lines)


def answer_rca_query(
    query: str,
    *,
    dataset: str | None,
    component: str | None,
    levels: Sequence[str] | None,
    incident_log: dict[str, Any] | None,
    context_logs: Sequence[dict[str, Any]] | None,
    settings: ChatSettings | None = None,
) -> dict[str, Any]:
    active_settings = settings or ChatSettings()
    lookback_ms = extract_rca_lookback_ms(query)
    logs = normalize_context_logs(context_logs or [])
    retrieval_mode = "context"
    if not logs:
        logs = load_online_rca_logs(query, dataset=dataset)
        retrieval_mode = "online" if logs else "local"
    if not logs:
        logs = load_local_logs()
    if incident_log:
        incident = normalize_log_payload(incident_log)
        logs = upsert_log_by_identity(logs, incident)
    else:
        incident = find_incident_log(query, logs)

    if not incident:
        return answer_without_rca_incident(
            query,
            dataset=dataset,
            component=component,
            levels=levels,
            settings=active_settings,
        )

    scoped_logs = filter_rca_scope(
        logs,
        dataset=dataset or text_value(incident, "dataset"),
        component=component,
        levels=levels,
    )
    scoped_logs = upsert_log_by_identity(scoped_logs, incident)
    evidence = rank_rca_evidence(scoped_logs, incident, lookback_ms=lookback_ms, limit=8)
    retrieval_error = None
    if active_settings.enable_rag and not evidence.candidates:
        try:
            semantic_logs = run_rca_semantic_retrieval(
                query=query,
                incident=incident,
                dataset=dataset or text_value(incident, "dataset"),
                component=component,
                levels=levels,
                settings=active_settings,
                lookback_ms=lookback_ms,
            )
        except Exception as exc:
            logger.warning("RCA semantic retrieval failed: %s", exc)
            semantic_logs = []
            retrieval_error = f"{exc.__class__.__name__}: {exc}"
        if semantic_logs:
            scoped_logs = upsert_log_by_identity(
                filter_rca_scope(
                    [*scoped_logs, *normalize_context_logs(semantic_logs)],
                    dataset=dataset or text_value(incident, "dataset"),
                    component=component,
                    levels=levels,
                ),
                incident,
            )
            evidence = rank_rca_evidence(scoped_logs, incident, lookback_ms=lookback_ms, limit=8)
            retrieval_mode = "semantic_fallback"
    candidates = [candidate.log for candidate in evidence.candidates]
    rca_context = build_rca_answer_context(
        query=query,
        incident=incident,
        evidence=evidence,
        lookback_ms=lookback_ms,
        retrieval_mode=retrieval_mode,
        retrieval_error=retrieval_error,
    )
    try:
        answer = generate_answer(
            rca_context,
            model=active_settings.answer_model,
            base_url=active_settings.answer_base_url,
        )
    except Exception as exc:
        logger.warning("RCA answer generation failed; using deterministic formatter: %s", exc)
        answer = format_rca_answer(query, incident, candidates)
    return {
        "answer": answer,
        "source": "rca",
        "context": summarize_rca_context(rca_context),
    }


def answer_without_rca_incident(
    query: str,
    *,
    dataset: str | None,
    component: str | None,
    levels: Sequence[str] | None,
    settings: ChatSettings,
) -> dict[str, Any]:
    if not settings.enable_rag:
        return {
            "answer": fallback_answer(query),
            "source": "fallback",
            "context": None,
        }
    try:
        context, answer = run_rag_pipeline(
            query=query,
            dataset=dataset,
            component=component,
            level=single_level(levels),
            settings=settings,
        )
    except Exception as exc:
        logger.warning("RAG fallback for RCA without incident failed: %s", exc)
        return {
            "answer": answer_from_local_logs(
                query,
                dataset=dataset,
                component=component,
                levels=levels,
                rag_error=exc,
            ),
            "source": "local",
            "context": {"error": str(exc)},
        }
    return {
        "answer": answer or fallback_answer(query),
        "source": "rag" if answer else "fallback",
        "context": summarize_context(context),
    }


def run_rca_semantic_retrieval(
    *,
    query: str,
    incident: dict[str, Any],
    dataset: str | None,
    component: str | None,
    levels: Sequence[str] | None,
    settings: ChatSettings,
    lookback_ms: int,
) -> list[dict[str, Any]]:
    incident_time = coerce_timestamp_ms(incident.get("timestamp_ms"))
    if incident_time is None:
        return []

    semantic_query = " ".join(
        part
        for part in (
            query,
            str(incident.get("service") or incident.get("component") or ""),
            str(incident.get("template_id") or ""),
            str(incident.get("message") or incident.get("raw_log") or ""),
        )
        if part
    )
    plan = RetrievalPlan(
        raw_query=query,
        normalized_query=normalize_query_text(query),
        semantic_query=semantic_query,
        answer_mode="root_cause",
        dataset=dataset or text_value(incident, "dataset"),
        level=single_level(levels),
        component=component,
        time_range=TimeRange(start_ms=max(0, incident_time - lookback_ms), end_ms=incident_time),
        top_k=min(max(settings.top_k, 8), 50),
        vector_search_k=max(settings.top_k, 50),
        use_vector_search=True,
    )
    client = get_milvus_client(settings.milvus_uri)
    model = get_embedding_model(settings.embedding_model)
    registry = get_template_registry()
    pending_registry = get_pending_template_registry()
    response = execute_plan(
        client=client,
        model=model,
        plan=plan,
        template_k=settings.template_k,
        template_registry=registry,
        pending_template_registry=pending_registry,
    )
    context = build_retrieval_context(
        query=query,
        plan=plan,
        response=response,
        include_templates=True,
    )
    incident_id = text_value(incident, "log_id")
    return [
        normalize_log_payload(row)
        for row in context.get("logs", [])
        if text_value(row, "log_id") != incident_id
    ]


def answer_from_local_logs(
    query: str,
    *,
    dataset: str | None,
    component: str | None,
    levels: Sequence[str] | None,
    rag_error: Exception,
    limit: int = 5,
) -> str:
    logs = load_local_logs()
    query_level = extract_query_level(query)
    query_terms = extract_query_terms(query)
    effective_levels = [query_level] if query_level else list(levels or [])

    rows, widened = select_local_fallback_rows(
        logs,
        dataset=dataset,
        component=component,
        levels=effective_levels,
        query_terms=query_terms,
        limit=limit,
    )
    if not rows:
        return (
            "RAG semantic chưa khả dụng và không có log local phù hợp với bộ lọc hiện tại. "
            f"Lỗi RAG: {rag_error.__class__.__name__}."
        )

    services = sorted({row["service"] for row in rows})
    levels_seen = sorted({row["level"] for row in rows})
    scope_note = (
        "Mình đã mở rộng tìm kiếm ngoài bộ lọc UI vì các token trong câu hỏi không khớp bộ lọc hiện tại."
        if widened
        else "Mình dùng bộ lọc hiện tại kết hợp token trong câu hỏi."
    )
    lines = [
        (
            "RAG semantic chưa khả dụng nên mình trả lời bằng log local theo bộ lọc/câu hỏi hiện tại. "
            f"Lỗi RAG: {rag_error.__class__.__name__}."
        ),
        scope_note,
        f"Câu hỏi: {query}",
        f"Log liên quan: {len(rows)} dòng, level {', '.join(levels_seen)}, service {', '.join(services[:4])}.",
    ]
    for row in rows:
        lines.append(
            f"- {row['timestamp']} {row['level']} {row['service']}: {truncate(row['message'], 180)}"
        )
    return "\n".join(lines)


def select_local_fallback_rows(
    logs: list[dict[str, Any]],
    *,
    dataset: str | None,
    component: str | None,
    levels: Sequence[str] | None,
    query_terms: Sequence[str],
    limit: int,
) -> tuple[list[dict[str, Any]], bool]:
    candidates = filter_local_log_records(
        logs,
        dataset=dataset,
        component=component,
        levels=levels,
    )
    ranked = rank_local_logs(candidates, query_terms)
    if ranked:
        return ranked[:limit], False

    if query_terms and (dataset or component):
        widened_candidates = filter_local_log_records(
            logs,
            dataset=None,
            component=None,
            levels=levels,
        )
        widened_ranked = rank_local_logs(widened_candidates, query_terms)
        if widened_ranked:
            return widened_ranked[:limit], True

    return sort_logs_newest(candidates)[:limit], False


def filter_local_log_records(
    logs: list[dict[str, Any]],
    *,
    dataset: str | None,
    component: str | None,
    levels: Sequence[str] | None,
) -> list[dict[str, Any]]:
    filtered = logs
    if dataset:
        filtered = [log for log in filtered if log["dataset"] == dataset]
    if component:
        filtered = [log for log in filtered if log["service"] == component]
    selected_levels = {level.upper() for level in levels or []}
    if selected_levels:
        filtered = [log for log in filtered if log["level"] in selected_levels]
    return filtered
