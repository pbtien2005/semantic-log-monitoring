from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from app.chat_api import create_app


class IngestionApiTest(unittest.TestCase):
    def test_ingest_logs_endpoint_publishes_to_kafka(self) -> None:
        with (
            patch("app.chat_api.publish_ingest_log") as publish_ingest_log,
            patch("app.chat_api.raw_log_store") as raw_log_store,
        ):
            publish_ingest_log.return_value = {
                "topic": "logs.raw",
                "key": "req-1",
                "log_id": "online:abc",
            }

            response = TestClient(create_app()).post(
                "/api/ingest/logs",
                content=json.dumps(
                    {
                        "dataset": "payment-prod",
                        "source_id": "payment-api-01",
                        "source": "api",
                        "service": "payment-service",
                        "request_id": "req-1",
                        "raw_log": "payment failed",
                    }
                ),
                headers={"content-type": "application/json"},
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json(),
            {"accepted": True, "topic": "logs.raw", "key": "req-1", "log_id": "online:abc"},
        )
        raw_log_store.index_log.assert_called_once()
        indexed_payload = raw_log_store.index_log.call_args.args[0]
        self.assertEqual(indexed_payload["dataset"], "payment-prod")
        self.assertEqual(indexed_payload["index_status"], "pending")
        publish_ingest_log.assert_called_once()

    def test_ingest_logs_endpoint_validates_payload(self) -> None:
        response = TestClient(create_app()).post(
            "/api/ingest/logs",
            content=json.dumps({"raw_log": "   "}),
            headers={"content-type": "application/json"},
        )

        self.assertEqual(response.status_code, 400)

    def test_recent_logs_endpoint_reads_raw_log_store(self) -> None:
        with patch("app.chat_api.raw_log_store") as raw_log_store:
            raw_log_store.recent_logs.return_value = [
                {
                    "log_id": "hdfs:abc",
                    "dataset": "hdfs",
                    "timestamp": "2026-07-06T10:00:00+07:00",
                    "level": "ERROR",
                    "service": "dfs.DataNode",
                    "message": "Connection reset by peer",
                    "index_status": "indexed",
                }
            ]

            response = TestClient(create_app()).get("/api/logs/recent?limit=25")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["logs"][0]["log_id"], "hdfs:abc")
        raw_log_store.recent_logs.assert_called_once_with(limit=25)


if __name__ == "__main__":
    unittest.main()
