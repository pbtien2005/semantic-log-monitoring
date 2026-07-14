from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from evaluation.checksums import sha256_file
from evaluation.config import load_config
from evaluation.ids import query_id, scenario_id, sequence_id, stable_id
from evaluation.io import read_jsonl, write_jsonl
from evaluation.time_utils import parse_iso_timestamp, timestamp_sequence


class EvaluationFoundationTest(unittest.TestCase):
    def test_jsonl_roundtrip_streams_objects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.jsonl"
            count = write_jsonl(path, [{"b": 2}, {"a": 1}])
            self.assertEqual(count, 2)
            self.assertEqual(list(read_jsonl(path)), [{"b": 2}, {"a": 1}])

    def test_deterministic_ids(self) -> None:
        self.assertEqual(stable_id("demo", "a", 1), stable_id("demo", "a", 1))
        self.assertNotEqual(stable_id("demo", "a", 1), stable_id("demo", "a", 2))
        self.assertEqual(sequence_id("demo", 31), "demo:000031")
        self.assertEqual(scenario_id(2), "incident-002")
        self.assertEqual(query_id(4), "q004")

    def test_timestamps_are_utc_and_deterministic(self) -> None:
        start = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)
        values = list(timestamp_sequence(start, 3, step=timedelta(milliseconds=250)))
        self.assertEqual(
            values,
            [
                "2026-07-14T10:00:00.000Z",
                "2026-07-14T10:00:00.250Z",
                "2026-07-14T10:00:00.500Z",
            ],
        )
        self.assertEqual(parse_iso_timestamp(values[1]).tzinfo, UTC)

    def test_config_loader_reads_example_yaml(self) -> None:
        config = load_config(Path("evaluation") / "config.example.yaml")
        self.assertEqual(config.dataset.seed, 20260714)
        self.assertEqual(config.dataset.log_count, 2000)
        self.assertEqual(config.dataset.anomaly_count, 18)
        self.assertEqual(config.retrieval.top_k, 24)
        self.assertIn("template_first_recency_v1", config.retrieval.experiments)
        self.assertEqual(config.quality_gates.root_cause_mrr, 0.50)

    def test_sha256_file_changes_with_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.txt"
            path.write_text("one", encoding="utf-8")
            first = sha256_file(path)
            path.write_text("two", encoding="utf-8")
            self.assertNotEqual(first, sha256_file(path))


if __name__ == "__main__":
    unittest.main()
