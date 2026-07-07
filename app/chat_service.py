"""Chat service for React dashboard questions."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from src.rag.answer import DEFAULT_RAG_BASE_URL, DEFAULT_RAG_MODEL, generate_answer
from src.rca import rank_rca_evidence
from src.rca.ranking import DEFAULT_LOOKBACK_MS, ENTITY_KEYS
from src.retrieval.context_builder import build_retrieval_context
from src.retrieval.milvus_search import DEFAULT_MODEL, DEFAULT_URI, execute_plan
from src.retrieval.query_plan import RetrievalPlan, TimeRange
from src.retrieval.query_planner import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    PlannerOptions,
    plan_query,
)
from src.retrieval.query_normalizer import normalize_query
from src.retrieval.template_registry import TemplateRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_ROOT = PROJECT_ROOT / "data" / "benchmark"
RECENT_TERMS = ("moi nhat", "gan day", "vua xay ra", "latest", "recent", "newest", "last logs")
RCA_TERMS = ("rca", "root cause", "log_id=", "anomaly log", "incident log")
BLOCK_ID_RE = re.compile(r"\bblk_-?\d+\b")
IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b")
LOG_ID_RE = re.compile(r"\blog_id=([^\s]+)")
QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "cac",
    "den",
    "error",
    "errors",
    "find",
    "hoac",
    "lien",
    "log",
    "logs",
    "loi",
    "quan",
    "related",
    "the",
    "tim",
    "to",
    "warn",
    "warning",
    "info",
    "notice",
}
LEVEL_NAMES = {"ERROR", "WARN", "WARNING", "INFO", "NOTICE", "DEBUG"}


@dataclass(frozen=True)
class ChatSettings:
    enable_rag: bool = os.getenv("ENABLE_RAG_CHAT", "1") != "0"
    milvus_uri: str = os.getenv("MILVUS_URI", DEFAULT_URI)
    embedding_model: str = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)
    planner_model: str = os.getenv("CLIPROXY_PLANNER_MODEL", DEFAULT_LLM_MODEL)
    planner_base_url: str = os.getenv("CLIPROXY_BASE_URL", DEFAULT_LLM_BASE_URL)
    answer_model: str = os.getenv("CLIPROXY_MODEL", DEFAULT_RAG_MODEL)
    answer_base_url: str = os.getenv("CLIPROXY_BASE_URL", DEFAULT_RAG_BASE_URL)
    top_k: int = int(os.getenv("CHAT_TOP_K", "24"))
    template_k: int = int(os.getenv("CHAT_TEMPLATE_K", "8"))
    use_planner_llm: bool = os.getenv("CHAT_USE_PLANNER_LLM", "1") == "1"


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


def clear_rag_dependency_caches() -> None:
    get_milvus_client.cache_clear()
    get_embedding_model.cache_clear()
    get_template_registry.cache_clear()


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
            use_llm=settings.use_planner_llm,
            llm_model=settings.planner_model,
            llm_base_url=settings.planner_base_url,
        ),
    )
    client = get_milvus_client(settings.milvus_uri)
    model = get_embedding_model(settings.embedding_model) if plan.use_vector_search else None
    registry = get_template_registry() if plan.use_vector_search else None
    response = execute_plan(
        client=client,
        model=model,
        plan=plan,
        template_k=settings.template_k,
        template_registry=registry,
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
        logs = load_local_logs()
        retrieval_mode = "local"
    if incident_log:
        incident = normalize_log_payload(incident_log)
        logs = upsert_log_by_identity(logs, incident)
    else:
        incident = find_incident_log(query, logs)

    if not incident:
        return {
            "answer": (
                "RCA cần một incident log rõ ràng nhưng mình chưa tìm thấy log phù hợp. "
                "Hãy gửi dạng `RCA log_id=...` hoặc bấm nút RCA trên dòng anomaly."
            ),
            "source": "rca",
            "context": {"incident_log_id": None, "candidate_count": 0},
        }

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
    except Exception:
        answer = format_rca_answer(query, incident, candidates)
    return {
        "answer": answer,
        "source": "rca",
        "context": summarize_rca_context(rca_context),
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
        level=None,
        component=component,
        time_range=TimeRange(start_ms=max(0, incident_time - lookback_ms), end_ms=incident_time),
        top_k=min(max(settings.top_k, 8), 50),
        vector_search_k=max(settings.top_k, 50),
        use_vector_search=True,
    )
    client = get_milvus_client(settings.milvus_uri)
    model = get_embedding_model(settings.embedding_model)
    registry = get_template_registry()
    response = execute_plan(
        client=client,
        model=model,
        plan=plan,
        template_k=settings.template_k,
        template_registry=registry,
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


def build_rca_answer_context(
    *,
    query: str,
    incident: dict[str, Any],
    evidence: Any,
    lookback_ms: int,
    retrieval_mode: str,
    retrieval_error: str | None = None,
) -> dict[str, Any]:
    candidate_by_id = {
        candidate.log_id: candidate
        for candidate in evidence.candidates
        if candidate.log_id
    }
    rows = sorted(
        [candidate.log for candidate in evidence.candidates] + [incident],
        key=lambda item: (
            item.get("timestamp_ms") if item.get("timestamp_ms") is not None else 10**30,
            str(item.get("log_id") or ""),
        ),
    )
    logs = []
    for index, row in enumerate(rows, start=1):
        log_id = text_value(row, "log_id")
        candidate = candidate_by_id.get(log_id or "")
        logs.append(rca_log_to_context(row, line_id=f"L{index:02d}", candidate=candidate, incident=incident))

    return {
        "query": query,
        "plan": {
            "answer_mode": "root_cause",
            "semantic_query": query,
            "dataset": incident.get("dataset"),
            "top_k": len(logs),
            "use_vector_search": retrieval_mode == "semantic_fallback",
            "applied_template_filter": False,
            "fallback_used": retrieval_mode == "semantic_fallback",
        },
        "retrieval": {
            "mode": retrieval_mode,
            "filter_expr": f"rca_window_ms={lookback_ms}",
        },
        "logs": logs,
        "template_map": [],
        "templates": [],
        "rca": {
            "incident_log_id": incident.get("log_id"),
            "incident_timestamp_ms": incident.get("timestamp_ms"),
            "lookback_ms": lookback_ms,
            "candidate_count": len(evidence.candidates),
            "candidate_log_ids": [candidate.log_id for candidate in evidence.candidates],
            "candidate_details": rca_candidate_details(evidence),
            "entity_keys_used": list(ENTITY_KEYS),
            "retrieval_mode": retrieval_mode,
            "retrieval_error": retrieval_error,
        },
    }


def rca_log_to_context(
    row: dict[str, Any],
    *,
    line_id: str,
    candidate: Any | None,
    incident: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "line_id": line_id,
        "log_id": row.get("log_id"),
        "dataset": row.get("dataset"),
        "timestamp_ms": row.get("timestamp_ms"),
        "timestamp": row.get("timestamp"),
        "level": row.get("level"),
        "component": row.get("component") or row.get("service"),
        "template_id": row.get("template_id"),
        "raw_log": row.get("raw_log") or row.get("message"),
        "message": row.get("message") or row.get("raw_log"),
        "anomaly_score": row.get("anomaly_score"),
        "request_id": row.get("request_id"),
        "trace_id": row.get("trace_id"),
        "block_id": row.get("block_id"),
        "ip": row.get("ip"),
        "rca_role": "incident" if row.get("log_id") == incident.get("log_id") else "evidence",
    }
    if candidate is not None:
        payload["rca_score"] = candidate.rca_score
        payload["rca_reasons"] = candidate.reasons
        payload["ranking_components"] = candidate.components
    return {key: value for key, value in payload.items() if value is not None and value != ""}


def rca_candidate_details(evidence: Any) -> list[dict[str, Any]]:
    return [
        {
            "log_id": candidate.log_id,
            "timestamp_ms": candidate.timestamp_ms,
            "service": candidate.service,
            "template_id": candidate.template_id,
            "rca_score": candidate.rca_score,
            "reasons": candidate.reasons,
            "ranking_components": candidate.components,
        }
        for candidate in evidence.candidates
    ]


def summarize_rca_context(context: dict[str, Any]) -> dict[str, Any]:
    rca = context.get("rca") if isinstance(context.get("rca"), dict) else {}
    return {
        "incident_log_id": rca.get("incident_log_id"),
        "candidate_count": rca.get("candidate_count", 0),
        "candidate_log_ids": rca.get("candidate_log_ids", []),
        "candidate_details": rca.get("candidate_details", []),
        "lookback_ms": rca.get("lookback_ms"),
        "entity_keys_used": rca.get("entity_keys_used", []),
        "retrieval_mode": rca.get("retrieval_mode"),
        "retrieval_error": rca.get("retrieval_error"),
    }


def format_rca_answer(query: str, incident: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    incident_message = str(incident.get("message") or incident.get("raw_log") or "")
    entity_notes = []
    if incident.get("block_id"):
        entity_notes.append(f"block `{incident['block_id']}`")
    if incident.get("request_id"):
        entity_notes.append(f"request `{incident['request_id']}`")
    if incident.get("trace_id"):
        entity_notes.append(f"trace `{incident['trace_id']}`")
    if incident.get("ip"):
        entity_notes.append(f"peer `{incident['ip']}`")
    entity_text = ", ".join(entity_notes) if entity_notes else "cùng service/thời gian gần incident"

    lines = [
        "## RCA Summary",
        (
            f"Incident `{incident.get('log_id') or 'unknown'}` là `{incident.get('level')}` của "
            f"`{incident.get('service')}` tại `{incident.get('timestamp') or incident.get('timestamp_ms')}`."
        ),
        f"Log chính: {incident_message}",
        "",
        "## Vì sao bất thường",
        (
            f"Dòng này bất thường vì nó là lỗi mức `{incident.get('level')}` trong luồng `{incident.get('service')}` "
            f"và có dấu hiệu liên quan {entity_text}."
        ),
    ]

    if candidates:
        lines.extend(["", "## Timeline RCA"])
        for index, row in enumerate(sorted(candidates + [incident], key=lambda item: item.get("timestamp_ms") or 0), start=1):
            marker = "incident" if row.get("log_id") == incident.get("log_id") else "evidence"
            lines.append(
                f"- L{index:02d} [{marker}] {row.get('timestamp') or row.get('timestamp_ms')} "
                f"{row.get('level')} {row.get('service')}: {truncate(str(row.get('message') or row.get('raw_log') or ''), 220)}"
            )
        lines.extend(
            [
                "",
                "## Nhận định",
                (
                    "Các evidence trước incident cho thấy lỗi không xuất hiện đơn lẻ. "
                    "Ưu tiên kiểm tra các dòng cùng entity/service ngay trước incident vì chúng thường mô tả triệu chứng dẫn tới lỗi chính."
                ),
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Timeline RCA",
                "- Chưa tìm thấy log trước incident trong context hiện tại.",
                "",
                "## Nhận định",
                "Mức chắc chắn thấp vì context chỉ có incident log, chưa có evidence trước/sau để dựng chuỗi nguyên nhân.",
            ]
        )

    lines.extend(
        [
            "",
            "## Next checks",
            "- Kiểm tra log cùng entity ở node/service liên quan trong vài phút trước incident.",
            "- Nếu có peer/IP/request/block id, đối chiếu log ở phía còn lại.",
            "- Kiểm tra network, timeout, restart process hoặc áp lực tài nguyên tại thời điểm incident.",
            "",
            f"Query RCA: {query}",
        ]
    )
    return "\n".join(lines)


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


def normalize_context_logs(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_log_payload(record) for record in records if isinstance(record, dict)]


def normalize_log_payload(record: dict[str, Any]) -> dict[str, Any]:
    timestamp = str(record.get("timestamp") or "")
    timestamp_ms = coerce_timestamp_ms(record.get("timestamp_ms") or record.get("parsedMs") or record.get("parsed_timestamp_ms"))
    if timestamp_ms is None:
        timestamp_ms = timestamp_to_ms(timestamp)
    message = str(record.get("message") or record.get("rawLog") or record.get("raw_log") or "")
    raw_log = str(record.get("rawLog") or record.get("raw_log") or message)
    service = record.get("service") or record.get("component") or record.get("logger")
    normalized = {
        "dataset": record.get("dataset") or "unknown",
        "timestamp": timestamp,
        "timestamp_ms": timestamp_ms,
        "parsed_timestamp": datetime.fromtimestamp(timestamp_ms / 1000) if timestamp_ms is not None else None,
        "level": str(record.get("level") or "UNKNOWN").upper(),
        "service": service or f"{record.get('dataset') or 'unknown'}-service",
        "component": record.get("component") or service,
        "message": message or raw_log,
        "raw_log": raw_log,
        "log_id": record.get("log_id") or record.get("logId"),
        "template_id": record.get("template_id") or record.get("templateId"),
        "anomaly_score": record.get("anomaly_score") if record.get("anomaly_score") is not None else record.get("anomalyScore"),
        "request_id": record.get("request_id") or record.get("requestId"),
        "trace_id": record.get("trace_id") or record.get("traceId"),
        "host": record.get("host"),
    }
    text = f"{normalized['message']} {raw_log}"
    block_match = BLOCK_ID_RE.search(text)
    if block_match:
        normalized["block_id"] = block_match.group(0)
    ip_match = IP_RE.search(text)
    if ip_match:
        normalized["ip"] = ip_match.group(0)
    return normalized


def coerce_timestamp_ms(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def timestamp_to_ms(value: str) -> int | None:
    if not value:
        return None
    try:
        return int(pd.Timestamp(value).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def upsert_log_by_identity(logs: list[dict[str, Any]], log: dict[str, Any]) -> list[dict[str, Any]]:
    log_id = text_value(log, "log_id")
    if not log_id:
        return [*logs, log]
    return [row for row in logs if text_value(row, "log_id") != log_id] + [log]


def find_incident_log(query: str, logs: list[dict[str, Any]]) -> dict[str, Any] | None:
    log_id = extract_log_id(query)
    if log_id:
        for log in logs:
            if text_value(log, "log_id") == log_id:
                return log

    terms = extract_query_terms(query)
    ranked = rank_local_logs(logs, terms)
    for log in ranked:
        if str(log.get("level")).upper() in {"ERROR", "CRITICAL"} or float_or_zero(log.get("anomaly_score")) >= 0.6:
            return log
    return None


def filter_rca_scope(
    logs: list[dict[str, Any]],
    *,
    dataset: str | None,
    component: str | None,
    levels: Sequence[str] | None,
) -> list[dict[str, Any]]:
    filtered = logs
    if dataset:
        filtered = [log for log in filtered if log.get("dataset") == dataset]
    if component:
        filtered = [log for log in filtered if log.get("service") == component or log.get("component") == component]
    return filtered


def extract_log_id(query: str) -> str | None:
    match = LOG_ID_RE.search(query)
    return match.group(1).strip() if match else None


def text_value(log: dict[str, Any], key: str) -> str | None:
    value = log.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def rank_local_logs(
    logs: list[dict[str, Any]],
    query_terms: Sequence[str],
) -> list[dict[str, Any]]:
    if not query_terms:
        return []

    scored: list[tuple[int, datetime, dict[str, Any]]] = []
    for log in logs:
        haystack_service = str(log["service"]).lower()
        haystack_message = str(log["message"]).lower()
        score = 0
        for term in query_terms:
            if term in haystack_service:
                score += 3
            if term in haystack_message:
                score += 2
        if score > 0:
            scored.append((score, log["parsed_timestamp"] or datetime.min, log))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in scored]


def sort_logs_newest(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        logs,
        key=lambda item: item["parsed_timestamp"] or datetime.min,
        reverse=True,
    )


def load_local_logs() -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    for path in sorted(LOGS_ROOT.glob("*/logs.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                logs.append(normalize_log_payload({**record, "dataset": record.get("dataset") or path.parent.name}))
    return logs


def is_recent_log_query(query: str) -> bool:
    normalized = normalize_query_text(query)
    return any(term in normalized for term in RECENT_TERMS)


def is_rca_query(query: str, *, mode: str | None = None, incident_log: dict[str, Any] | None = None) -> bool:
    if mode and mode.lower() == "rca":
        return True
    if incident_log:
        return True
    normalized = normalize_query_text(query)
    return any(term in normalized for term in RCA_TERMS)


def normalize_query_text(query: str) -> str:
    lowered = query.lower().replace("đ", "d")
    normalized = unicodedata.normalize("NFD", lowered)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def normalize_query_text(query: str) -> str:
    return normalize_query(query).accentless_text


def extract_recent_window_hours(query: str, default: int = 1) -> int:
    match = re.search(r"\b(\d{1,3})\s*(?:h|gio|tieng|hour|hours)\b", normalize_query_text(query))
    return max(1, int(match.group(1))) if match else default


def extract_rca_lookback_ms(query: str, default: int = DEFAULT_LOOKBACK_MS) -> int:
    normalized = normalize_query_text(query)
    minute_match = re.search(r"\b(\d{1,4})\s*(?:m|min|mins|minute|minutes|phut|p)\b", normalized)
    if minute_match:
        return max(1, int(minute_match.group(1))) * 60 * 1000
    hour_match = re.search(r"\b(\d{1,3})\s*(?:h|hour|hours|gio|tieng)\b", normalized)
    if hour_match:
        return max(1, int(hour_match.group(1))) * 60 * 60 * 1000
    return default


def extract_query_level(query: str) -> str | None:
    upper = query.upper()
    for level in LEVEL_NAMES:
        if re.search(rf"\b{re.escape(level)}\b", upper):
            return "WARN" if level == "WARNING" else level
    return None


def extract_query_terms(query: str) -> list[str]:
    normalized = normalize_query_text(query)
    terms: list[str] = []
    for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_.$-]*", normalized):
        lowered = token.lower()
        if len(lowered) < 3 or lowered in QUERY_STOPWORDS:
            continue
        if lowered not in terms:
            terms.append(lowered)
    return terms


def normalize_filter(value: str | None) -> str | None:
    if not value or value in {"all", "Tất cả"}:
        return None
    return value


def single_level(levels: Sequence[str] | None) -> str | None:
    clean_levels = [level for level in levels or [] if level and level != "UNKNOWN"]
    return clean_levels[0] if len(clean_levels) == 1 else None


def fallback_answer(query: str) -> str:
    return (
        "Mình đã nhận câu hỏi nhưng chưa có câu trả lời RAG khả dụng. "
        f"Câu hỏi: {query}. Hãy kiểm tra trạng thái Milvus và CLIProxyAPI nếu bạn muốn câu trả lời theo ngữ cảnh truy hồi."
    )


def summarize_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": context.get("query"),
        "dataset": context.get("plan", {}).get("dataset") if isinstance(context.get("plan"), dict) else None,
        "line_count": len(context.get("log_lines", [])) if isinstance(context.get("log_lines"), list) else None,
        "template_count": len(context.get("templates", [])) if isinstance(context.get("templates"), list) else None,
    }


def truncate(value: str, max_length: int) -> str:
    return value if len(value) <= max_length else f"{value[: max_length - 3]}..."
