from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evaluation.io import read_json, write_jsonl
from evaluation.metrics import calculate_anomaly_metrics
from evaluation.scripts.calculate_anomaly_metrics import write_anomaly_metrics_report


class AnomalyMetricsTest(unittest.TestCase):
    def test_calculates_binary_severity_score_and_signal_metrics(self) -> None:
        metrics = calculate_anomaly_metrics(
            groundtruth=[
                anomaly("a", True, "high", [0.7, 1.0], ["template_rarity", "entity_linkage"]),
                anomaly("b", True, "medium", [0.5, 0.9], ["sequence_anomaly"]),
                anomaly("c", False, "none", [0.0, 0.3], []),
                anomaly("d", False, "none", [0.0, 0.3], []),
            ],
            predictions=[
                prediction("a", True, 0.8, "high", ["template_rarity"]),
                prediction("b", False, 0.2, "none", []),
                prediction("c", True, 0.6, "high", ["template_rarity"]),
                prediction("d", False, 0.1, "none", []),
            ],
        )

        self.assertEqual(metrics["evaluated_count"], 4)
        self.assertEqual(metrics["confusion"], {"tp": 1, "fp": 1, "fn": 1, "tn": 1})
        self.assertAlmostEqual(metrics["precision"], 0.5)
        self.assertAlmostEqual(metrics["recall"], 0.5)
        self.assertAlmostEqual(metrics["f1"], 0.5)
        self.assertAlmostEqual(metrics["false_positive_rate"], 0.5)
        self.assertAlmostEqual(metrics["false_negative_rate"], 0.5)
        self.assertAlmostEqual(metrics["accuracy"], 0.5)
        self.assertAlmostEqual(metrics["severity_agreement"], 1.0)
        self.assertAlmostEqual(metrics["score_range_agreement"], 0.5)
        self.assertAlmostEqual(metrics["signal_overlap"], 0.25)

    def test_script_writes_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            groundtruth_path = root / "anomalies.jsonl"
            predictions_path = root / "predictions.jsonl"
            output_path = root / "report.json"
            write_jsonl(groundtruth_path, [anomaly("a", True, "high", [0.7, 1.0], ["s1"])])
            write_jsonl(predictions_path, [prediction("a", True, 0.9, "high", ["s1"])])

            write_anomaly_metrics_report(
                groundtruth_path=groundtruth_path,
                predictions_path=predictions_path,
                output_path=output_path,
            )
            report = read_json(output_path)
            self.assertEqual(report["evaluated_count"], 1)
            self.assertEqual(report["precision"], 1.0)


def anomaly(
    log_id: str,
    expected: bool,
    severity: str,
    score_range: list[float],
    signals: list[str],
) -> dict[str, object]:
    return {
        "anomaly_id": f"anomaly:{log_id}",
        "log_id": log_id,
        "expected_anomaly": expected,
        "expected_severity": severity,
        "expected_score_range": score_range,
        "signals": signals,
    }


def prediction(
    log_id: str,
    predicted: bool,
    score: float,
    severity: str,
    signals: list[str],
) -> dict[str, object]:
    return {
        "log_id": log_id,
        "predicted_anomaly": predicted,
        "score": score,
        "severity": severity,
        "signals": signals,
    }


if __name__ == "__main__":
    unittest.main()
