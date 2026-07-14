"""Load evaluation logs through supported ingestion paths."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evaluation.io import JsonObject, read_jsonl


EVALUATION_ONLY_FIELDS = {
    "ground_truth_role",
    "scenario_id",
}


@dataclass(frozen=True)
class LoadOptions:
    dataset_path: Path
    mode: str = "api"
    base_url: str = "http://localhost:8000"
    endpoint: str = "/api/ingest/logs"
    batch_size: int = 100
    timeout_seconds: float = 10.0
    delay_seconds: float = 0.0
    dry_run: bool = False
    limit: int | None = None


@dataclass
class LoadFailure:
    log_id: str | None
    index: int
    error: str


@dataclass
class LoadSummary:
    mode: str
    dry_run: bool
    input_count: int = 0
    attempted_count: int = 0
    successful_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    failures: list[LoadFailure] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "dry_run": self.dry_run,
            "input_count": self.input_count,
            "attempted_count": self.attempted_count,
            "successful_count": self.successful_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "failures": [failure.__dict__ for failure in self.failures],
        }


class DirectModeUnavailable(RuntimeError):
    """Raised when direct loading would bypass the production pipeline."""


def strip_evaluation_fields(record: JsonObject) -> JsonObject:
    return {key: value for key, value in record.items() if key not in EVALUATION_ONLY_FIELDS}


def build_ingest_url(base_url: str, endpoint: str = "/api/ingest/logs") -> str:
    return f"{base_url.rstrip('/')}/{endpoint.strip('/')}"


def iter_payloads(path: str | Path, *, limit: int | None = None) -> list[JsonObject]:
    payloads: list[JsonObject] = []
    for record in read_jsonl(path):
        payloads.append(strip_evaluation_fields(record))
        if limit is not None and len(payloads) >= limit:
            break
    return payloads


def load_evaluation_logs(options: LoadOptions) -> LoadSummary:
    if options.batch_size < 1:
        raise ValueError("batch_size must be positive")
    if options.limit is not None and options.limit < 1:
        raise ValueError("limit must be positive when provided")
    if options.mode == "api":
        return load_via_api(options)
    if options.mode == "direct":
        return load_via_direct(options)
    raise ValueError(f"Unsupported load mode: {options.mode}")


def load_via_api(options: LoadOptions) -> LoadSummary:
    payloads = iter_payloads(options.dataset_path, limit=options.limit)
    summary = LoadSummary(mode="api", dry_run=options.dry_run, input_count=len(payloads))
    if options.dry_run:
        summary.skipped_count = len(payloads)
        return summary

    url = build_ingest_url(options.base_url, options.endpoint)
    for start in range(0, len(payloads), options.batch_size):
        batch = payloads[start : start + options.batch_size]
        for offset, payload in enumerate(batch, start=start + 1):
            summary.attempted_count += 1
            try:
                response = send_payload(url, payload, timeout_seconds=options.timeout_seconds)
            except Exception as exc:
                summary.failed_count += 1
                summary.failures.append(
                    LoadFailure(log_id=optional_log_id(payload), index=offset, error=str(exc))
                )
                continue
            status = int(response.get("status") or 0)
            if 200 <= status < 300:
                summary.successful_count += 1
            else:
                summary.failed_count += 1
                summary.failures.append(
                    LoadFailure(
                        log_id=optional_log_id(payload),
                        index=offset,
                        error=f"unexpected HTTP status {status}",
                    )
                )
            if options.delay_seconds > 0 and offset < len(payloads):
                time.sleep(options.delay_seconds)
    return summary


def load_via_direct(options: LoadOptions) -> LoadSummary:
    raise DirectModeUnavailable(
        "direct mode is not enabled because the current reusable worker entrypoint "
        "requires live Milvus/model/OpenSearch dependencies. Use mode=api to exercise "
        "the real ingestion pipeline without bypassing production behavior."
    )


def send_payload(url: str, payload: JsonObject, *, timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return {
                "status": response.status,
                "body": json.loads(body) if body else {},
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc)) from exc


def optional_log_id(payload: JsonObject) -> str | None:
    value = payload.get("log_id")
    return str(value) if value is not None else None
