from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evaluation.io import read_jsonl, write_jsonl
from evaluation.retrieval_runner import RetrievalRunOptions, run_retrieval_evaluation


class RetrievalRunnerTest(unittest.TestCase):
    def test_baseline_writes_top_k_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            logs_path, queries_path, output_path = write_fixture(Path(tmp))
            count = run_retrieval_evaluation(
                RetrievalRunOptions(
                    logs_path=logs_path,
                    queries_path=queries_path,
                    output_path=output_path,
                    experiment="baseline_log_only_v1",
                    top_k=2,
                )
            )
            self.assertEqual(count, 1)
            [row] = list(read_jsonl(output_path))
            self.assertEqual(row["query_id"], "q001")
            self.assertLessEqual(len(row["retrieved_log_ids"]), 2)
            self.assertIn("demo:000001", row["retrieved_log_ids"])
            self.assertIn("latency_ms", row)

    def test_template_first_diversifies_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            logs_path, queries_path, output_path = write_fixture(Path(tmp), duplicate_templates=True)
            run_retrieval_evaluation(
                RetrievalRunOptions(
                    logs_path=logs_path,
                    queries_path=queries_path,
                    output_path=output_path,
                    experiment="template_first_recency_v1",
                    top_k=4,
                )
            )
            [row] = list(read_jsonl(output_path))
            self.assertGreaterEqual(row["unique_template_count"], 2)
            self.assertLess(row["duplicate_template_ratio"], 1)

    def test_limit_restricts_query_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs_path, queries_path, output_path = write_fixture(root)
            queries = list(read_jsonl(queries_path))
            queries.append({**queries[0], "query_id": "q002", "query": "nova-api error"})
            write_jsonl(queries_path, queries)
            count = run_retrieval_evaluation(
                RetrievalRunOptions(
                    logs_path=logs_path,
                    queries_path=queries_path,
                    output_path=output_path,
                    experiment="baseline_log_only_v1",
                    limit=1,
                )
            )
            self.assertEqual(count, 1)


def write_fixture(root: Path, *, duplicate_templates: bool = False) -> tuple[Path, Path, Path]:
    logs = [
        log("demo:000001", "T_STORAGE_BACKEND_TIMEOUT", "cinder-volume", "Volume backend timed out"),
        log("demo:000002", "T_GENERIC_TIMEOUT", "nova-api", "Timeout while refreshing cache"),
        log("demo:000003", "T_VOLUME_ATTACH_RETRY", "nova-compute", "Retrying volume attach"),
        log("demo:000004", "T_API_SERVICE_UNAVAILABLE", "nova-api", "Instance creation failed"),
    ]
    if duplicate_templates:
        logs.extend(
            [
                log("demo:000005", "T_GENERIC_TIMEOUT", "nova-api", "Timeout while contacting identity"),
                log("demo:000006", "T_GENERIC_TIMEOUT", "nova-api", "Timeout while contacting scheduler"),
            ]
        )
    queries = [
        {
            "query_id": "q001",
            "query": "Find logs for volume timeout on nova-api",
        }
    ]
    logs_path = root / "logs.jsonl"
    queries_path = root / "queries.jsonl"
    output_path = root / "results.jsonl"
    write_jsonl(logs_path, logs)
    write_jsonl(queries_path, queries)
    return logs_path, queries_path, output_path


def log(log_id: str, template_id: str, service: str, message: str) -> dict[str, object]:
    return {
        "log_id": log_id,
        "timestamp": "2026-07-14T10:00:00.000Z",
        "dataset": "openstack",
        "source_id": "node-01",
        "service": service,
        "component": service,
        "level": "ERROR" if "failed" in message.casefold() else "WARN",
        "request_id": "req-demo-001",
        "instance_id": "inst-demo-001",
        "block_id": None,
        "template_id": template_id,
        "message": message,
        "raw_log": message,
    }


if __name__ == "__main__":
    unittest.main()
