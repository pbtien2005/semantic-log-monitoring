from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from evaluation.io import write_jsonl
from evaluation.loader import (
    DirectModeUnavailable,
    LoadOptions,
    build_ingest_url,
    iter_payloads,
    load_evaluation_logs,
    strip_evaluation_fields,
)


class LoaderTest(unittest.TestCase):
    def test_strip_evaluation_fields(self) -> None:
        payload = strip_evaluation_fields(
            {
                "log_id": "demo:1",
                "raw_log": "raw",
                "ground_truth_role": "root_cause",
                "scenario_id": "incident-001",
            }
        )
        self.assertEqual(payload, {"log_id": "demo:1", "raw_log": "raw"})

    def test_build_ingest_url(self) -> None:
        self.assertEqual(
            build_ingest_url("http://localhost:8000/", "/api/ingest/logs"),
            "http://localhost:8000/api/ingest/logs",
        )

    def test_dry_run_skips_sending_and_strips_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.jsonl"
            write_jsonl(path, [sample_log("demo:000001")])
            payloads = iter_payloads(path)
            self.assertNotIn("ground_truth_role", payloads[0])
            summary = load_evaluation_logs(LoadOptions(dataset_path=path, dry_run=True))
            self.assertEqual(summary.input_count, 1)
            self.assertEqual(summary.skipped_count, 1)
            self.assertEqual(summary.attempted_count, 0)

    def test_api_mode_posts_stripped_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.jsonl"
            write_jsonl(path, [sample_log("demo:000001"), sample_log("demo:000002")])
            with CapturingServer() as server:
                summary = load_evaluation_logs(
                    LoadOptions(dataset_path=path, base_url=server.base_url, batch_size=1)
                )
                self.assertEqual(summary.successful_count, 2)
                self.assertEqual(summary.failed_count, 0)
                self.assertEqual(len(server.payloads), 2)
                self.assertNotIn("ground_truth_role", server.payloads[0])
                self.assertNotIn("scenario_id", server.payloads[0])
                self.assertEqual(server.payloads[0]["log_id"], "demo:000001")

    def test_api_mode_reports_http_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.jsonl"
            write_jsonl(path, [sample_log("demo:000001")])
            with CapturingServer(status=500) as server:
                summary = load_evaluation_logs(LoadOptions(dataset_path=path, base_url=server.base_url))
                self.assertEqual(summary.successful_count, 0)
                self.assertEqual(summary.failed_count, 1)
                self.assertIn("HTTP 500", summary.failures[0].error)

    def test_direct_mode_is_explicitly_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs.jsonl"
            write_jsonl(path, [sample_log("demo:000001")])
            with self.assertRaises(DirectModeUnavailable):
                load_evaluation_logs(LoadOptions(dataset_path=path, mode="direct"))


class CapturingHandler(BaseHTTPRequestHandler):
    server: Any

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        self.server.payloads.append(payload)
        body = json.dumps({"accepted": self.server.status < 400}).encode("utf-8")
        self.send_response(self.server.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


class CapturingServer:
    def __init__(self, *, status: int = 202) -> None:
        self.status = status
        self.payloads: list[dict[str, Any]] = []
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.base_url = ""

    def __enter__(self) -> "CapturingServer":
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), CapturingHandler)
        self.server.status = self.status
        self.server.payloads = self.payloads
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)


def sample_log(log_id: str) -> dict[str, Any]:
    return {
        "log_id": log_id,
        "timestamp": "2026-07-14T10:00:00.000Z",
        "dataset": "openstack",
        "source_id": "compute-01",
        "service": "nova-api",
        "component": "nova.api.openstack.compute",
        "level": "ERROR",
        "request_id": "req-demo-001",
        "instance_id": "inst-demo-001",
        "block_id": None,
        "template_id": "T_TEST",
        "message": "Instance request failed",
        "raw_log": "2026-07-14T10:00:00.000Z ERROR nova-api: Instance request failed",
        "scenario_id": "incident-001",
        "ground_truth_role": "incident",
    }


if __name__ == "__main__":
    unittest.main()
