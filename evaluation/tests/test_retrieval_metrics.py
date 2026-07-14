from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evaluation.io import read_json, write_jsonl
from evaluation.metrics import calculate_retrieval_metrics, ndcg_at, reciprocal_rank
from evaluation.scripts.calculate_retrieval_metrics import write_retrieval_metrics_report


class RetrievalMetricsTest(unittest.TestCase):
    def test_rank_metrics_ignore_duplicate_relevance(self) -> None:
        self.assertEqual(reciprocal_rank(["x", "b", "b", "a"], {"a", "b"}), 0.5)
        self.assertAlmostEqual(
            ndcg_at(
                ["x", "b", "b", "a", "c"],
                {"a": 3, "b": 2, "c": 1},
                5,
            ),
            0.61756,
            places=5,
        )

    def test_calculates_retrieval_and_rca_summary(self) -> None:
        metrics = calculate_retrieval_metrics(
            results=[
                {
                    "query_id": "q001",
                    "experiment": "toy_v1",
                    "retrieved_log_ids": ["x", "b", "b", "a", "c"],
                    "retrieved_template_ids": ["T_NOISE", "T_B", "T_B", "T_A", "T_C"],
                    "latency_ms": 12.5,
                },
                {
                    "query_id": "q002",
                    "experiment": "toy_v1",
                    "retrieved_log_ids": ["silent-symptom"],
                    "retrieved_template_ids": ["T_SYMPTOM"],
                    "latency_ms": 3.0,
                },
            ],
            queries=[
                {
                    "query_id": "q001",
                    "incident_id": "incident-001",
                    "expected_log_ids": ["a", "b", "c"],
                    "required_log_ids": ["a"],
                    "root_cause_log_id": "a",
                    "relevance_judgments": {"a": 3, "b": 2, "c": 1},
                },
                {
                    "query_id": "q002",
                    "incident_id": "incident-002",
                    "expected_log_ids": ["silent-symptom"],
                    "required_log_ids": [],
                    "root_cause_log_id": None,
                    "relevance_judgments": {"silent-symptom": 2},
                },
            ],
            incidents=[
                {
                    "incident_id": "incident-001",
                    "scenario_type": "explicit_root_cause",
                    "root_cause_log_id": "a",
                    "incident_log_id": "c",
                    "evidence_log_ids": ["a", "b", "c"],
                    "required_evidence_log_ids": ["a"],
                },
                {
                    "incident_id": "incident-002",
                    "scenario_type": "silent_root_cause",
                    "root_cause_log_id": None,
                    "incident_log_id": "silent-symptom",
                    "evidence_log_ids": ["silent-symptom"],
                    "required_evidence_log_ids": [],
                },
            ],
            ks=(5,),
        )

        self.assertEqual(metrics["experiment"], "toy_v1")
        self.assertEqual(metrics["query_count"], 2)
        self.assertAlmostEqual(metrics["retrieval"]["hit@5"], 1.0)
        self.assertAlmostEqual(metrics["retrieval"]["recall@5"], 1.0)
        self.assertAlmostEqual(metrics["retrieval"]["required_evidence_recall@5"], 1.0)
        self.assertAlmostEqual(metrics["retrieval"]["precision@5"], 0.4)
        self.assertAlmostEqual(metrics["retrieval"]["mrr"], 0.75)
        self.assertAlmostEqual(metrics["retrieval"]["unique_template@5"], 2.5)
        self.assertAlmostEqual(metrics["retrieval"]["duplicate_template_ratio@5"], 0.1)
        self.assertEqual(metrics["rca"]["root_cause_evaluable_query_count"], 1)
        self.assertEqual(metrics["rca"]["root_cause_excluded_query_count"], 1)
        self.assertAlmostEqual(metrics["rca"]["root_cause_hit@5"], 1.0)
        self.assertAlmostEqual(metrics["rca"]["root_cause_mrr"], 0.25)
        self.assertAlmostEqual(metrics["rca"]["causal_chain_completeness@5"], 0.5)

    def test_script_writes_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results_path = root / "results.jsonl"
            queries_path = root / "queries.jsonl"
            incidents_path = root / "incidents.jsonl"
            output_path = root / "report.json"
            write_jsonl(
                results_path,
                [
                    {
                        "query_id": "q001",
                        "experiment": "toy_v1",
                        "retrieved_log_ids": ["a"],
                        "retrieved_template_ids": ["T_A"],
                    }
                ],
            )
            write_jsonl(
                queries_path,
                [
                    {
                        "query_id": "q001",
                        "incident_id": "incident-001",
                        "expected_log_ids": ["a"],
                        "required_log_ids": ["a"],
                        "root_cause_log_id": "a",
                        "relevance_judgments": {"a": 3},
                    }
                ],
            )
            write_jsonl(
                incidents_path,
                [
                    {
                        "incident_id": "incident-001",
                        "scenario_type": "explicit_root_cause",
                        "root_cause_log_id": "a",
                        "incident_log_id": "a",
                        "evidence_log_ids": ["a"],
                        "required_evidence_log_ids": ["a"],
                    }
                ],
            )

            write_retrieval_metrics_report(
                results_path=results_path,
                queries_path=queries_path,
                incidents_path=incidents_path,
                output_path=output_path,
                ks=(1,),
            )
            report = read_json(output_path)
            self.assertEqual(report["experiment"], "toy_v1")
            self.assertEqual(report["query_count"], 1)


if __name__ == "__main__":
    unittest.main()
