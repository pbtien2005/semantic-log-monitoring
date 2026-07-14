"""Raw log store backed by OpenSearch."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


DEFAULT_RAW_LOG_INDEX = "semantic-raw-logs"


@dataclass(frozen=True, slots=True)
class RawLogStoreSettings:
    base_url: str = os.getenv("RAW_LOG_STORE_URL", "http://localhost:9200")
    index_name: str = os.getenv("RAW_LOG_INDEX", DEFAULT_RAW_LOG_INDEX)
    timeout_seconds: float = float(os.getenv("RAW_LOG_STORE_TIMEOUT_SECONDS", "5"))


class RawLogStoreError(RuntimeError):
    """Raised when the raw log store cannot complete a request."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type


class OpenSearchRawLogStore:
    def __init__(
        self,
        settings: RawLogStoreSettings | None = None,
        *,
        opener: Callable[[Request, float], Any] | None = None,
    ) -> None:
        self.settings = settings or RawLogStoreSettings()
        self._opener = opener or urlopen
        self._index_ready = False

    def index_log(self, payload: dict[str, Any], *, index_status: str = "pending") -> dict[str, Any]:
        self.ensure_index()
        document = {
            **payload,
            "ingest_status": payload.get("ingest_status") or "received",
            "index_status": index_status,
            "updated_at": now_iso(),
        }
        log_id = str(document.get("log_id") or "")
        if not log_id:
            raise RawLogStoreError("raw log payload must include log_id")
        self._request(
            "PUT",
            f"/{self.settings.index_name}/_doc/{quote(log_id, safe='')}",
            document,
        )
        return document

    def update_index_status(
        self,
        log_id: str,
        *,
        index_status: str,
        index_error: str | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> None:
        self.ensure_index()
        doc: dict[str, Any] = {
            "index_status": index_status,
            "updated_at": now_iso(),
        }
        if index_status == "indexed":
            doc["indexed_at"] = now_iso()
            doc["index_error"] = None
        if index_error:
            doc["index_error"] = index_error
        if extra_fields:
            doc.update(extra_fields)
        self._request(
            "POST",
            f"/{self.settings.index_name}/_update/{quote(log_id, safe='')}",
            {"doc": doc},
        )

    def get_log(self, log_id: str) -> dict[str, Any] | None:
        self.ensure_index()
        try:
            response = self._request(
                "GET",
                f"/{self.settings.index_name}/_doc/{quote(log_id, safe='')}",
            )
        except RawLogStoreError as exc:
            if exc.status_code == 404:
                return None
            raise
        if not response.get("found", True):
            return None
        source = response.get("_source")
        return source if isinstance(source, dict) else None

    def search_logs(
        self,
        *,
        dataset: str | None = None,
        source_id: str | None = None,
        host: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        self.ensure_index()
        filters = []
        if dataset:
            filters.append({"term": {"dataset": dataset}})
        if source_id:
            filters.append({"term": {"source_id": source_id}})
        if host:
            filters.append({"term": {"host": host}})

        response = self._request(
            "POST",
            f"/{self.settings.index_name}/_search",
            {
                "size": max(1, min(int(limit), 1000)),
                "sort": [
                    {"timestamp_ms": {"order": "asc", "missing": "_last"}},
                    {"line_number": {"order": "asc", "missing": "_last"}},
                    {"ingested_at": {"order": "asc", "missing": "_last"}},
                ],
                "query": {"bool": {"filter": filters}} if filters else {"match_all": {}},
            },
        )
        return [hit.get("_source", {}) for hit in response.get("hits", {}).get("hits", [])]

    def recent_logs(self, *, limit: int = 200) -> list[dict[str, Any]]:
        self.ensure_index()
        response = self._request(
            "POST",
            f"/{self.settings.index_name}/_search",
            {
                "size": max(1, min(int(limit), 500)),
                "sort": [
                    {"timestamp_ms": {"order": "desc", "missing": "_last"}},
                    {"ingested_at": {"order": "desc", "missing": "_last"}},
                ],
                "query": {"match_all": {}},
            },
        )
        return [hit.get("_source", {}) for hit in response.get("hits", {}).get("hits", [])]

    def ensure_index(self) -> None:
        if self._index_ready:
            return
        try:
            self._request("PUT", f"/{self.settings.index_name}", index_mapping())
        except RawLogStoreError as exc:
            if exc.error_type != "resource_already_exists_exception":
                raise
        self._index_ready = True

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = urljoin(self.settings.base_url.rstrip("/") + "/", path.lstrip("/"))
        data = json.dumps(body or {}).encode("utf-8") if body is not None else None
        request = Request(
            url,
            data=data,
            method=method,
            headers={"content-type": "application/json"},
        )
        try:
            with self._opener(request, timeout=self.settings.timeout_seconds) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RawLogStoreError(
                f"OpenSearch {method} {path} failed: {detail}",
                status_code=exc.code,
                error_type=opensearch_error_type(detail),
            ) from exc
        except URLError as exc:
            raise RawLogStoreError(f"OpenSearch unavailable: {exc.reason}") from exc
        except OSError as exc:
            raise RawLogStoreError(f"OpenSearch request failed: {exc}") from exc
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RawLogStoreError(
                f"OpenSearch {method} {path} returned invalid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise RawLogStoreError(
                f"OpenSearch {method} {path} returned a non-object JSON response"
            )
        return payload


def opensearch_error_type(detail: str) -> str | None:
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        value = error.get("type")
        return str(value) if value else None
    return str(error) if error else None


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def index_mapping() -> dict[str, Any]:
    return {
        "mappings": {
            "dynamic": True,
            "properties": {
                "log_id": {"type": "keyword"},
                "dataset": {"type": "keyword"},
                "timestamp": {"type": "date", "ignore_malformed": True},
                "timestamp_ms": {"type": "long"},
                "level": {"type": "keyword"},
                "service": {"type": "keyword"},
                "component": {"type": "keyword"},
                "message": {"type": "text"},
                "raw_log": {"type": "text"},
                "source_id": {"type": "keyword"},
                "request_id": {"type": "keyword"},
                "trace_id": {"type": "keyword"},
                "block_id": {"type": "keyword"},
                "candidate_id": {"type": "keyword"},
                "template_id": {"type": "keyword"},
                "template_match_status": {"type": "keyword"},
                "ingest_status": {"type": "keyword"},
                "index_status": {"type": "keyword"},
                "index_error": {"type": "text"},
                "ingested_at": {"type": "date", "ignore_malformed": True},
                "indexed_at": {"type": "date", "ignore_malformed": True},
                "updated_at": {"type": "date", "ignore_malformed": True},
                "anomaly_score": {"type": "float"},
                "anomaly_level": {"type": "keyword"},
                "anomaly_decision": {"type": "keyword"},
            },
        }
    }
