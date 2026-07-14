from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evaluation.io import read_json, read_jsonl, write_json, write_jsonl
from evaluation.scripts.generate_dataset import GeneratorOptions, generate, write_dataset
from evaluation.validation import validate_dataset_dir


BLUEPRINT_PATH = Path("evaluation") / "scenarios" / "incident_blueprints.jsonl"


class GroundTruthValidationTest(unittest.TestCase):
    def test_generated_dataset_passes_validation(self) -> None:
        with self.generated_dataset_dir() as dataset:
            report = validate_dataset_dir(dataset)
            self.assertTrue(report.passed, report.errors)
            self.assertEqual(report.counts["logs"], 600)

    def test_detects_missing_log_reference(self) -> None:
        with self.generated_dataset_dir() as dataset:
            dataset_path = Path(dataset)
            incidents_path = dataset_path / "incidents.jsonl"
            incidents = list(read_jsonl(incidents_path))
            incidents[0]["incident_log_id"] = "demo:missing"
            write_jsonl(incidents_path, incidents)
            report = validate_dataset_dir(dataset)
            self.assertFalse(report.passed)
            self.assertTrue(any("unknown log_id" in error for error in report.errors))

    def test_detects_duplicate_log_id(self) -> None:
        with self.generated_dataset_dir() as dataset:
            dataset_path = Path(dataset)
            logs_path = dataset_path / "logs.jsonl"
            logs = list(read_jsonl(logs_path))
            logs[1]["log_id"] = logs[0]["log_id"]
            write_jsonl(logs_path, logs)
            report = validate_dataset_dir(dataset)
            self.assertFalse(report.passed)
            self.assertTrue(any("duplicate log_id" in error for error in report.errors))

    def test_detects_root_cause_after_incident(self) -> None:
        with self.generated_dataset_dir() as dataset:
            dataset_path = Path(dataset)
            logs_path = dataset_path / "logs.jsonl"
            incidents = list(read_jsonl(dataset_path / "incidents.jsonl"))
            first = next(item for item in incidents if item["root_cause_log_id"] is not None)
            logs = list(read_jsonl(logs_path))
            by_id = {log["log_id"]: log for log in logs}
            by_id[first["root_cause_log_id"]]["timestamp"] = "2099-01-01T00:00:00.000Z"
            write_jsonl(logs_path, logs)
            report = validate_dataset_dir(dataset)
            self.assertFalse(report.passed)
            self.assertTrue(any("root cause occurs after incident" in error for error in report.errors))

    def test_detects_invalid_relevance(self) -> None:
        with self.generated_dataset_dir() as dataset:
            dataset_path = Path(dataset)
            path = dataset_path / "groundtruth_queries.jsonl"
            queries = list(read_jsonl(path))
            first_key = next(iter(queries[0]["relevance_judgments"]))
            queries[0]["relevance_judgments"][first_key] = 9
            write_jsonl(path, queries)
            report = validate_dataset_dir(dataset)
            self.assertFalse(report.passed)
            self.assertTrue(any("invalid relevance" in error for error in report.errors))

    def test_detects_silent_case_with_root_cause_id(self) -> None:
        with self.generated_dataset_dir(incident_count=15, log_count=1400, query_count=50) as dataset:
            dataset_path = Path(dataset)
            path = dataset_path / "incidents.jsonl"
            incidents = list(read_jsonl(path))
            silent = next(item for item in incidents if item["scenario_type"] == "silent_root_cause")
            silent["root_cause_log_id"] = incidents[0]["root_cause_log_id"]
            write_jsonl(path, incidents)
            report = validate_dataset_dir(dataset)
            self.assertFalse(report.passed)
            self.assertTrue(any("silent incident must not have root_cause_log_id" in error for error in report.errors))

    def test_detects_manifest_checksum_mismatch(self) -> None:
        with self.generated_dataset_dir() as dataset:
            dataset_path = Path(dataset)
            manifest_path = dataset_path / "dataset_manifest.json"
            manifest = read_json(manifest_path)
            manifest["files"]["logs.jsonl"]["sha256"] = "bad"
            write_json(manifest_path, manifest)
            report = validate_dataset_dir(dataset)
            self.assertFalse(report.passed)
            self.assertTrue(any("checksum mismatch" in error for error in report.errors))

    def generated_dataset_dir(
        self,
        *,
        incident_count: int = 5,
        log_count: int = 600,
        query_count: int = 12,
    ) -> tempfile.TemporaryDirectory[str]:
        temp = tempfile.TemporaryDirectory()
        options = GeneratorOptions(
            output_dir=Path(temp.name),
            blueprint_path=BLUEPRINT_PATH,
            version="test-v1",
            seed=20260714,
            log_count=log_count,
            query_count=query_count,
            incident_count=incident_count,
            anomaly_count=8,
        )
        write_dataset(generate(options), options)
        return temp


if __name__ == "__main__":
    unittest.main()
