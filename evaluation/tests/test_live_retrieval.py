from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from evaluation.io import read_jsonl, write_jsonl
from evaluation.live_retrieval import (
    DirectRetrievalDependencies,
    LiveRetrievalOptions,
    ProductionDirectRetriever,
    extract_log_records,
    run_live_retrieval_evaluation,
)
from src.retrieval.milvus_models import RetrievalResponse, RetrievalResult
from src.retrieval.query_plan import RetrievalPlan


class LiveRetrievalTest(unittest.TestCase):
    def test_direct_retriever_uses_production_plan_and_execute_contract(self) -> None:
        calls: dict[str, Any] = {}

        def fake_plan_query(query: str, options: Any) -> RetrievalPlan:
            calls["query"] = query
            calls["planner_options"] = options
            return RetrievalPlan(
                raw_query=query,
                normalized_query=query,
                semantic_query=f"semantic {query}",
                dataset=options.dataset,
                component=options.component,
                top_k=options.top_k,
            )

        def fake_execute_plan(**kwargs: Any) -> RetrievalResponse:
            calls["execute"] = kwargs
            return RetrievalResponse(
                mode="filtered_vector",
                filter_expr='dataset == "openstack"',
                log_lines=[
                    live_result("demo:000002", "T_RETRY", 0.7),
                    live_result("demo:000001", "T_ROOT", 0.95),
                ],
                templates=[],
            )

        retriever = ProductionDirectRetriever(
            LiveRetrievalOptions(
                queries_path=Path("queries.jsonl"),
                output_path=Path("results.jsonl"),
                top_k=2,
                template_k=3,
                dataset="openstack",
                component="nova-api",
            ),
            dependencies=DirectRetrievalDependencies(
                client=object(),
                model=object(),
                template_registry=None,
                pending_template_registry=None,
                plan_query_fn=fake_plan_query,
                execute_plan_fn=fake_execute_plan,
            ),
        )

        row = retriever.search({"query_id": "q001", "query": "find root cause"})

        self.assertEqual(row["experiment"], "production_direct_v1")
        self.assertEqual(row["query_id"], "q001")
        self.assertEqual(row["retrieved_log_ids"], ["demo:000002", "demo:000001"])
        self.assertEqual(row["retrieved_template_ids"], ["T_RETRY", "T_ROOT"])
        self.assertEqual(row["scores"], [0.7, 0.95])
        self.assertEqual(row["retrieval_mode"], "filtered_vector")
        self.assertEqual(row["filter_expr"], 'dataset == "openstack"')
        self.assertEqual(calls["query"], "find root cause")
        self.assertEqual(calls["planner_options"].top_k, 2)
        self.assertEqual(calls["execute"]["template_k"], 3)
        self.assertEqual(calls["execute"]["config"].final_top_k, 2)

    def test_api_retrieval_runner_writes_metrics_compatible_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queries_path = root / "queries.jsonl"
            output_path = root / "results.jsonl"
            write_jsonl(
                queries_path,
                [{"query_id": "q001", "query": "find root cause", "query_type": "rca"}],
            )
            with RetrievalApiServer() as server:
                count = run_live_retrieval_evaluation(
                    LiveRetrievalOptions(
                        queries_path=queries_path,
                        output_path=output_path,
                        mode="api",
                        base_url=server.base_url,
                        endpoint="/retrieve",
                        top_k=2,
                    )
                )

            self.assertEqual(count, 1)
            [row] = list(read_jsonl(output_path))
            self.assertEqual(row["experiment"], "production_api_v1")
            self.assertEqual(row["retrieved_log_ids"], ["demo:000001", "demo:000002"])
            self.assertEqual(row["retrieved_template_ids"], ["T_ROOT", "T_RETRY"])
            self.assertIn("latency_ms", row)

    def test_extract_log_records_finds_common_response_shapes(self) -> None:
        payload = {
            "context": {
                "logs": [{"log_id": "a", "template_id": "T_A", "score": 0.9}],
            },
            "results": [{"id": "b", "templateId": "T_B", "score": 0.8}],
        }
        records = extract_log_records(payload)
        self.assertEqual([record["log_id"] for record in records], ["a", "b"])
        self.assertEqual([record["template_id"] for record in records], ["T_A", "T_B"])


def live_result(log_id: str, template_id: str, score: float) -> RetrievalResult:
    return RetrievalResult(
        collection="log_line",
        primary_id=log_id,
        score=score,
        semantic_score=score,
        source="vector",
        entity={
            "log_id": log_id,
            "dataset": "openstack",
            "template_id": template_id,
            "level": "ERROR",
            "component": "nova-api",
            "timestamp_ms": 1000,
            "payload": {"template_id": template_id, "raw_log": "raw"},
        },
    )


class RetrievalApiHandler(BaseHTTPRequestHandler):
    server: Any

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        self.server.payloads.append(payload)
        body = json.dumps(
            {
                "logs": [
                    {"log_id": "demo:000001", "template_id": "T_ROOT", "score": 0.95},
                    {"log_id": "demo:000002", "template_id": "T_RETRY", "score": 0.7},
                ]
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


class RetrievalApiServer:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.base_url = ""

    def __enter__(self) -> "RetrievalApiServer":
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), RetrievalApiHandler)
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


if __name__ == "__main__":
    unittest.main()
