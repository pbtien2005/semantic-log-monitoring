from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evaluation.checksums import sha256_file
from evaluation.io import read_json, read_jsonl
from evaluation.scripts.generate_dataset import GeneratorOptions, generate, write_dataset
from evaluation.time_utils import parse_iso_timestamp


BLUEPRINT_PATH = Path("evaluation") / "scenarios" / "incident_blueprints.jsonl"


class DatasetGenerationTest(unittest.TestCase):
    def test_same_seed_generates_same_dataset(self) -> None:
        options = self.options(seed=1234)
        first = generate(options)
        second = generate(options)
        self.assertEqual(first.logs, second.logs)
        self.assertEqual(first.incidents, second.incidents)
        self.assertEqual(first.queries, second.queries)
        self.assertEqual(first.anomalies, second.anomalies)

    def test_different_seed_changes_log_sequence(self) -> None:
        first = generate(self.options(seed=1234))
        second = generate(self.options(seed=5678))
        self.assertNotEqual(first.logs, second.logs)

    def test_counts_unique_ids_and_timestamp_order(self) -> None:
        dataset = generate(self.options())
        self.assertEqual(len(dataset.logs), 600)
        self.assertEqual(len(dataset.incidents), 5)
        self.assertEqual(len(dataset.queries), 12)
        self.assertEqual(len(dataset.anomalies), 8)

        log_ids = [str(log["log_id"]) for log in dataset.logs]
        self.assertEqual(len(log_ids), len(set(log_ids)))

        timestamps = [parse_iso_timestamp(str(log["timestamp"])) for log in dataset.logs]
        self.assertEqual(timestamps, sorted(timestamps))
        self.assertEqual(len(set(timestamps)), len(timestamps))

    def test_incident_ground_truth_references_existing_logs(self) -> None:
        dataset = generate(self.options(incident_count=8, log_count=900))
        log_ids = {str(log["log_id"]) for log in dataset.logs}
        for incident in dataset.incidents:
            self.assertIn(str(incident["incident_log_id"]), log_ids)
            if incident["root_cause_log_id"] is not None:
                self.assertIn(str(incident["root_cause_log_id"]), log_ids)
            for log_id in incident["evidence_log_ids"]:
                self.assertIn(str(log_id), log_ids)
            self.assertTrue(set(incident["required_evidence_log_ids"]).issubset(incident["evidence_log_ids"]))

    def test_evidence_chain_is_interleaved_with_noise_or_normal_logs(self) -> None:
        dataset = generate(self.options(incident_count=3, log_count=360))
        index_by_id = {str(log["log_id"]): index for index, log in enumerate(dataset.logs)}
        for incident in dataset.incidents:
            positions = [index_by_id[str(log_id)] for log_id in incident["evidence_log_ids"]]
            self.assertEqual(positions, sorted(positions))
            for left, right in zip(positions, positions[1:]):
                between = dataset.logs[left + 1 : right]
                self.assertGreaterEqual(len(between), 5)
                self.assertTrue(
                    any(log["ground_truth_role"] in {"normal", "noise"} for log in between)
                )

    def test_anomalies_include_positive_and_negative_samples(self) -> None:
        dataset = generate(self.options(anomaly_count=10))
        values = {record["expected_anomaly"] for record in dataset.anomalies}
        self.assertEqual(values, {False, True})

    def test_queries_reference_expected_logs_and_templates(self) -> None:
        dataset = generate(self.options())
        log_by_id = {str(log["log_id"]): log for log in dataset.logs}
        for query in dataset.queries:
            self.assertTrue(query["expected_log_ids"])
            self.assertTrue(query["required_log_ids"])
            self.assertTrue(set(query["required_log_ids"]).issubset(query["expected_log_ids"]))
            for log_id in query["expected_log_ids"]:
                self.assertIn(str(log_id), log_by_id)
            for template_id in query["expected_template_ids"]:
                self.assertTrue(str(template_id).startswith("T_"))

    def test_write_dataset_manifest_uses_actual_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            options = self.options(output_dir=Path(tmp))
            dataset = generate(options)
            manifest = write_dataset(dataset, options)
            manifest_path = Path(tmp) / "dataset_manifest.json"
            persisted_manifest = read_json(manifest_path)
            self.assertEqual(manifest, persisted_manifest)
            self.assertEqual(manifest["log_count"], 600)
            self.assertEqual(len(list(read_jsonl(Path(tmp) / "logs.jsonl"))), 600)
            self.assertEqual(
                manifest["files"]["logs.jsonl"]["sha256"],
                sha256_file(Path(tmp) / "logs.jsonl"),
            )

    def options(
        self,
        *,
        output_dir: Path | None = None,
        seed: int = 20260714,
        log_count: int = 600,
        query_count: int = 12,
        incident_count: int = 5,
        anomaly_count: int = 8,
    ) -> GeneratorOptions:
        return GeneratorOptions(
            output_dir=output_dir or Path("evaluation") / "datasets",
            blueprint_path=BLUEPRINT_PATH,
            version="test-v1",
            seed=seed,
            log_count=log_count,
            query_count=query_count,
            incident_count=incident_count,
            anomaly_count=anomaly_count,
        )


if __name__ == "__main__":
    unittest.main()
