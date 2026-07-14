"""Build and summarize RCA context and fallback answers."""

from __future__ import annotations

from typing import Any

from app.chat_log_utils import text_value, truncate
from src.rca.ranking import ENTITY_KEYS


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
        logs.append(
            rca_log_to_context(
                row,
                line_id=f"L{index:02d}",
                candidate=candidate,
                incident=incident,
            )
        )

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


def format_rca_answer(
    query: str,
    incident: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> str:
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
        for index, row in enumerate(
            sorted(candidates + [incident], key=lambda item: item.get("timestamp_ms") or 0),
            start=1,
        ):
            marker = "incident" if row.get("log_id") == incident.get("log_id") else "evidence"
            lines.append(
                f"- L{index:02d} [{marker}] {row.get('timestamp') or row.get('timestamp_ms')} "
                f"{row.get('level')} {row.get('service')}: "
                f"{truncate(str(row.get('message') or row.get('raw_log') or ''), 220)}"
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
