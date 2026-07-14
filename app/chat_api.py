"""Starlette API for dashboard chat."""

from __future__ import annotations

import json
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.chat_service import answer_chat_query
from src.ingestion.kafka_contract import normalize_raw_log_payload
from src.ingestion.kafka_io import KafkaPublishError, publish_ingest_log
from src.ingestion.raw_log_store import OpenSearchRawLogStore, RawLogStoreError


raw_log_store = OpenSearchRawLogStore()


async def read_json_object(request: Request) -> tuple[dict[str, Any] | None, JSONResponse | None]:
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JSONResponse({"error": "invalid json"}, status_code=400)
    if not isinstance(payload, dict):
        return None, JSONResponse({"error": "json payload must be an object"}, status_code=400)
    return payload, None


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


async def chat(request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error:
        return error
    assert payload is not None

    query = str(payload.get("query") or "").strip()
    if not query:
        return JSONResponse({"error": "query is required"}, status_code=400)

    result = answer_chat_query(
        query,
        dataset=payload.get("dataset"),
        component=payload.get("service") or payload.get("component"),
        levels=payload.get("levels") or [],
        mode=payload.get("mode"),
        incident_log=payload.get("incident_log"),
        context_logs=payload.get("context_logs"),
    )
    return JSONResponse(result)


async def ingest_logs(request: Request) -> JSONResponse:
    payload, error = await read_json_object(request)
    if error:
        return error
    assert payload is not None

    try:
        normalized = normalize_raw_log_payload(payload)
        raw_log_store.index_log({**normalized, "index_status": "pending"}, index_status="pending")
        result = publish_ingest_log(normalized)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except RawLogStoreError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except KafkaPublishError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)

    return JSONResponse({"accepted": True, **result}, status_code=202)


async def recent_logs(request: Request) -> JSONResponse:
    try:
        limit = max(1, min(int(request.query_params.get("limit", "200")), 500))
    except ValueError:
        return JSONResponse({"error": "limit must be an integer"}, status_code=400)

    try:
        logs = raw_log_store.recent_logs(limit=limit)
    except RawLogStoreError as exc:
        return JSONResponse({"error": str(exc), "logs": []}, status_code=503)

    return JSONResponse({"logs": logs})


def create_app() -> Starlette:
    return Starlette(
        debug=False,
        routes=[
            Route("/healthz", health, methods=["GET"]),
            Route("/api/chat", chat, methods=["POST"]),
            Route("/api/ingest/logs", ingest_logs, methods=["POST"]),
            Route("/api/logs/recent", recent_logs, methods=["GET"]),
        ],
    )


app = create_app()
