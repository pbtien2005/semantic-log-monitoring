from __future__ import annotations

import json
import re
import unittest

from infra.scripts.demo.rca_logs import (
    HIGH_RCA_DEMO_LOGS,
    HIGH_RCA_INCIDENT_LOG_ID,
    INCIDENT_LOG_ID,
    RCA_DEMO_LOGS,
)
from infra.scripts.demo.send_rca_logs import build_ingest_url, encode_payload
from src.chunking.builders import build_line_chunk
from src.ingestion.kafka_contract import normalize_raw_log_payload
from src.rca import rank_rca_evidence


class RcaDemoLogsTest(unittest.TestCase):
    def test_demo_contains_one_error_incident_for_shared_block(self) -> None:
        self.assertGreaterEqual(len(RCA_DEMO_LOGS), 5)

        error_logs = [log for log in RCA_DEMO_LOGS if log["level"] == "ERROR"]
        self.assertEqual([log["log_id"] for log in error_logs], [INCIDENT_LOG_ID])

        block_ids = {
            re.search(r"blk_-?\d+", str(log["raw_log"])).group(0)
            for log in RCA_DEMO_LOGS
        }
        self.assertEqual(block_ids, {"blk_4292382298896622412"})

    def test_demo_payloads_are_ingest_ready(self) -> None:
        required_keys = {
            "dataset",
            "source_id",
            "raw_log",
            "message",
            "timestamp",
            "level",
            "component",
            "log_id",
        }

        for line_number, log in enumerate(RCA_DEMO_LOGS, start=1):
            self.assertTrue(required_keys <= set(log))
            self.assertEqual(log["dataset"], "hdfs")
            self.assertEqual(log["line_number"], line_number)
            normalized = normalize_raw_log_payload(log)
            self.assertEqual(normalized["log_id"], log["log_id"])
            self.assertEqual(normalized["dataset"], "hdfs")

    def test_send_script_helpers_build_ingest_request(self) -> None:
        self.assertEqual(
            build_ingest_url("http://localhost:8000/"),
            "http://localhost:8000/api/ingest/logs",
        )

        payload = json.loads(encode_payload(RCA_DEMO_LOGS[0]).decode("utf-8"))
        self.assertEqual(payload["log_id"], RCA_DEMO_LOGS[0]["log_id"])
        self.assertEqual(payload["dataset"], "hdfs")

    def test_high_rca_demo_has_multiple_high_scoring_candidates(self) -> None:
        self.assertGreaterEqual(len(HIGH_RCA_DEMO_LOGS), 12)

        chunks = [build_line_chunk(normalize_raw_log_payload(log)) for log in HIGH_RCA_DEMO_LOGS]
        incident = next(log for log in chunks if log["log_id"] == HIGH_RCA_INCIDENT_LOG_ID)
        evidence = rank_rca_evidence(chunks, incident, lookback_ms=10 * 60 * 1000, limit=8)

        high_candidates = [
            candidate
            for candidate in evidence.candidates
            if candidate.rca_score >= 0.70
        ]
        self.assertGreaterEqual(len(high_candidates), 3)
        self.assertTrue(
            all("shared_entity_or_session" in candidate.reasons for candidate in high_candidates)
        )
        self.assertTrue(
            all("same_template" in candidate.reasons for candidate in high_candidates)
        )


if __name__ == "__main__":
    unittest.main()
