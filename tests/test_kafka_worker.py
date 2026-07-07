from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from infra.scripts.ingestion.consume_kafka_logs import (
    ConsumerMessage,
    IngestionBatchResult,
    process_kafka_batch,
    process_records,
)
from src.anomaly.schema import AnomalyConfig
from src.anomaly.scoring import build_baseline
from src.anomaly.state import OnlineAnomalyState
from src.chunking.builders import build_line_chunk
from src.chunking.template_matcher import TemplateMatcher


@dataclass(frozen=True, slots=True)
class FakeMessage:
    value: bytes
    topic: str = "logs.raw"
    partition: int = 0
    offset: int = 1


class KafkaWorkerTest(unittest.TestCase):
    def test_process_kafka_batch_commits_after_successful_processing(self) -> None:
        processor = Mock(return_value=IngestionBatchResult(processed=1, failed=0))
        consumer = Mock()
        dlq = Mock()
        raw_log_store = Mock()
        messages: list[ConsumerMessage] = [
            FakeMessage(
                value=json.dumps(
                    {
                        "dataset": "payment-prod",
                        "source_id": "payment-api-01",
                        "raw_log": "payment failed",
                        "component": "checkout",
                    }
                ).encode("utf-8")
            )
        ]

        result = process_kafka_batch(
            messages,
            processor=processor,
            consumer=consumer,
            dlq_producer=dlq,
            raw_log_store=raw_log_store,
        )

        self.assertEqual(result.processed, 1)
        consumer.commit.assert_called_once()
        dlq.send.assert_not_called()
        raw_log_store.update_index_status.assert_called_once()
        self.assertEqual(raw_log_store.update_index_status.call_args.kwargs["index_status"], "indexed")

    def test_process_kafka_batch_does_not_commit_when_processing_fails(self) -> None:
        processor = Mock(side_effect=RuntimeError("milvus down"))
        consumer = Mock()
        raw_log_store = Mock()
        messages: list[ConsumerMessage] = [
            FakeMessage(
                value=json.dumps(
                    {
                        "dataset": "payment-prod",
                        "source_id": "payment-api-01",
                        "raw_log": "payment failed",
                    }
                ).encode("utf-8")
            )
        ]

        with self.assertRaises(RuntimeError):
            process_kafka_batch(
                messages,
                processor=processor,
                consumer=consumer,
                dlq_producer=Mock(),
                raw_log_store=raw_log_store,
            )

        consumer.commit.assert_not_called()
        raw_log_store.update_index_status.assert_called_once()
        self.assertEqual(raw_log_store.update_index_status.call_args.kwargs["index_status"], "failed")
        self.assertIn("milvus down", raw_log_store.update_index_status.call_args.kwargs["index_error"])

    def test_process_kafka_batch_sends_invalid_json_to_dlq_and_commits(self) -> None:
        processor = Mock()
        consumer = Mock()
        dlq = Mock()
        messages: list[ConsumerMessage] = [FakeMessage(value=b"{bad json")]

        result = process_kafka_batch(messages, processor=processor, consumer=consumer, dlq_producer=dlq)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.failed, 1)
        processor.assert_not_called()
        dlq.send.assert_called_once()
        consumer.commit.assert_called_once()

    def test_process_records_accepts_online_dataset_and_upserts_by_log_id(self) -> None:
        class FakeVector:
            def tolist(self) -> list[float]:
                return [0.1] * 768

        class FakeModel:
            def encode(self, texts: list[str], **_: Any) -> list[FakeVector]:
                self.texts = texts
                return [FakeVector() for _ in texts]

        class FakeClient:
            def __init__(self) -> None:
                self.rows: list[dict[str, Any]] = []

            def upsert(self, *, collection_name: str, data: list[dict[str, Any]]) -> dict[str, int]:
                self.collection_name = collection_name
                self.rows.extend(data)
                return {"upsert_count": len(data)}

            def flush(self, collection_name: str) -> None:
                self.flushed_collection = collection_name

        client = FakeClient()
        model = FakeModel()

        result = process_records(
            [
                {
                    "log_id": "payment-prod:abc",
                    "dataset": "payment-prod",
                    "source_id": "payment-api-01",
                    "host": "host-01",
                    "environment": "prod",
                    "raw_log": "checkout failed for request req-1",
                    "message": "checkout failed for request req-1",
                    "timestamp": "2026-07-04T10:00:00Z",
                    "component": "checkout",
                    "level": "ERROR",
                    "event_id": None,
                    "source_file": "api",
                    "line_number": 1,
                }
            ],
            client=client,
            model=model,
            batch_size=32,
        )

        self.assertEqual(result.processed, 1)
        self.assertEqual(client.rows[0]["log_id"], "payment-prod:abc")
        self.assertEqual(client.rows[0]["dataset"], "payment-prod")
        self.assertEqual(client.rows[0]["payload"]["source_id"], "payment-api-01")
        self.assertEqual(client.rows[0]["payload"]["host"], "host-01")
        self.assertEqual(client.rows[0]["payload"]["environment"], "prod")
        self.assertEqual(client.rows[0]["payload"]["raw_log"], "checkout failed for request req-1")

    def test_process_records_uses_template_catalog_when_available(self) -> None:
        class FakeVector:
            def tolist(self) -> list[float]:
                return [0.1] * 768

        class FakeModel:
            def encode(self, texts: list[str], **_: Any) -> list[FakeVector]:
                self.texts = texts
                return [FakeVector() for _ in texts]

        class FakeClient:
            def __init__(self) -> None:
                self.rows: list[dict[str, Any]] = []

            def upsert(self, *, collection_name: str, data: list[dict[str, Any]]) -> dict[str, int]:
                self.rows.extend(data)
                return {"upsert_count": len(data)}

            def flush(self, collection_name: str) -> None:
                self.flushed_collection = collection_name

        matcher = TemplateMatcher.from_records(
            [
                {
                    "template_id": "apache::E2",
                    "dataset": "apache",
                    "template": "workerEnv.init() ok <*>",
                    "regex": r"^workerEnv\.init\(\) ok (?P<config_path>\S+)$",
                    "intent": ["worker_env_initialized"],
                    "priority": 100,
                }
            ]
        )
        client = FakeClient()

        process_records(
            [
                {
                    "log_id": "apache:1",
                    "dataset": "apache",
                    "source_id": "apache-node",
                    "raw_log": "workerEnv.init() ok /etc/apache2/workers.properties",
                    "message": "workerEnv.init() ok /etc/apache2/workers.properties",
                    "timestamp": "Sun Dec 04 04:47:01 2005",
                    "component": None,
                    "level": "INFO",
                    "event_id": None,
                    "source_file": "apache.log",
                    "line_number": 1,
                }
            ],
            client=client,
            model=FakeModel(),
            batch_size=32,
            template_matchers={"apache": matcher},
        )

        row = client.rows[0]
        self.assertEqual(row["template_id"], "apache::E2")
        self.assertEqual(row["payload"]["template_id"], "apache::E2")
        self.assertEqual(row["payload"]["template_match_status"], "matched")
        self.assertEqual(row["payload"]["template_slots"]["config_path"], "/etc/apache2/workers.properties")

    def test_process_records_writes_pending_template_for_catalog_miss(self) -> None:
        class FakeVector:
            def tolist(self) -> list[float]:
                return [0.1] * 768

        class FakeModel:
            def encode(self, texts: list[str], **_: Any) -> list[FakeVector]:
                return [FakeVector() for _ in texts]

        class FakeClient:
            def __init__(self) -> None:
                self.rows: list[dict[str, Any]] = []

            def upsert(self, *, collection_name: str, data: list[dict[str, Any]]) -> dict[str, int]:
                self.rows.extend(data)
                return {"upsert_count": len(data)}

            def flush(self, collection_name: str) -> None:
                self.flushed_collection = collection_name

        matcher = TemplateMatcher.from_records(
            [
                {
                    "template_id": "apache::other",
                    "dataset": "apache",
                    "template": "other",
                    "regex": r"^other$",
                    "intent": ["other"],
                    "priority": 100,
                }
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            pending_path = Path(tmp) / "pending_templates.jsonl"
            process_records(
                [
                    {
                        "log_id": "apache:1",
                        "dataset": "apache",
                        "source_id": "apache-node",
                        "raw_log": "mod_jk child workerEnv in error state 6",
                        "message": "mod_jk child workerEnv in error state 6",
                        "timestamp": "Sun Dec 04 04:47:01 2005",
                        "component": None,
                        "level": "ERROR",
                        "event_id": None,
                        "source_file": "apache.log",
                        "line_number": 1,
                    }
                ],
                client=FakeClient(),
                model=FakeModel(),
                batch_size=32,
                template_matchers={"apache": matcher},
                pending_template_path=pending_path,
            )

            records = [json.loads(line) for line in pending_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "pending")
        self.assertEqual(records[0]["active"], False)
        self.assertEqual(records[0]["template"], "mod_jk child workerEnv in error state <state_code>")
        self.assertEqual(records[0]["occurrences"], 1)

    def test_process_records_attaches_anomaly_payload_when_enabled(self) -> None:
        class FakeVector:
            def tolist(self) -> list[float]:
                return [0.1] * 768

        class FakeModel:
            def encode(self, texts: list[str], **_: Any) -> list[FakeVector]:
                self.texts = texts
                return [FakeVector() for _ in texts]

        class FakeClient:
            def __init__(self) -> None:
                self.rows: list[dict[str, Any]] = []

            def upsert(self, *, collection_name: str, data: list[dict[str, Any]]) -> dict[str, int]:
                self.collection_name = collection_name
                self.rows.extend(data)
                return {"upsert_count": len(data)}

            def flush(self, collection_name: str) -> None:
                self.flushed_collection = collection_name

        def record(index: int, message: str, *, level: str = "INFO") -> dict[str, Any]:
            return {
                "log_id": f"apache:{index}",
                "dataset": "apache",
                "source_id": "access-log",
                "host": "host-01",
                "environment": "prod",
                "raw_log": message,
                "message": message,
                "timestamp": f"2005-12-04 04:47:{index % 60:02d}",
                "component": "mod_jk",
                "level": level,
                "event_id": None,
                "source_file": "access.log",
                "line_number": index,
            }

        training_chunks = [
            build_line_chunk(record(index, "worker env initialized ok"))
            for index in range(1, 12)
        ]
        config = AnomalyConfig(min_logs_per_service=3, min_windows_per_service=100)
        baseline = build_baseline(training_chunks, config=config)
        client = FakeClient()

        result = process_records(
            [record(20, "database timeout while opening connection", level="ERROR")],
            client=client,
            model=FakeModel(),
            batch_size=32,
            anomaly_enabled=True,
            anomaly_baseline=baseline,
            anomaly_state=OnlineAnomalyState(window_size=config.window_size),
        )

        payload = client.rows[0]["payload"]
        self.assertEqual(result.processed, 1)
        self.assertEqual(payload["anomaly"]["baseline_status"], "ready")
        self.assertIn("new_template_for_service", payload["anomaly"]["reasons"])
        self.assertIn("anomaly_score", payload)
        self.assertIn("anomaly_components", payload)


if __name__ == "__main__":
    unittest.main()
