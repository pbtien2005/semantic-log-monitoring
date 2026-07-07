from __future__ import annotations

import unittest
from typing import Any

import numpy as np

from src.retrieval.milvus_search import RetrievalConfig, execute_plan
from src.retrieval.query_plan import RetrievalPlan, SortSpec
from src.retrieval.template_registry import TemplateRegistry


class FakeVector(list[float]):
    def tolist(self) -> list[float]:
        return list(self)


class FakeModel:
    def encode(self, texts: list[str], **kwargs: Any) -> list[FakeVector]:
        return [FakeVector([1.0, 0.0, 0.0])]


class RecordingClient:
    def __init__(self, search_batches: list[list[dict[str, Any]]] | None = None) -> None:
        self.search_calls: list[dict[str, Any]] = []
        self.query_calls: list[dict[str, Any]] = []
        self.search_batches = list(search_batches or [])

    def search(self, **kwargs: Any) -> list[list[dict[str, Any]]]:
        self.search_calls.append(kwargs)
        batch = self.search_batches.pop(0) if self.search_batches else []
        return [batch]

    def query(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.query_calls.append(kwargs)
        return []


def hit(
    log_id: str,
    template_id: str,
    score: float = 0.8,
    *,
    timestamp_ms: int = 1000,
) -> dict[str, Any]:
    return {
        "distance": score,
        "entity": {
            "log_id": log_id,
            "dataset": "openstack",
            "template_id": template_id,
            "level": "ERROR",
            "component": "nova.compute.manager",
            "timestamp_ms": timestamp_ms,
            "payload": {"message": f"log {log_id}", "template_id": template_id},
        },
    }


def runtime_hit(
    log_id: str,
    dataset: str = "payment-prod",
    score: float = 0.8,
) -> dict[str, Any]:
    return {
        "distance": score,
        "entity": {
            "log_id": log_id,
            "dataset": dataset,
            "template_id": "template::payment-prod::checkout",
            "level": "ERROR",
            "component": "checkout",
            "timestamp_ms": 1000,
            "payload": {
                "message": "payment failed",
                "source_id": "payment-api-01",
                "template_id": "template::payment-prod::checkout",
            },
        },
    }


def registry_with_scores(scores: list[float]) -> TemplateRegistry:
    records = []
    vectors = []
    for index, score in enumerate(scores, start=1):
        records.append(
            {
                "template_id": f"template::openstack::{index}",
                "dataset": "openstack",
                "component": "nova.compute.manager",
                "level": "ERROR",
                "template": f"Template {index}",
                "search_text": f"template {index}",
                "signals": ["compute_lifecycle"],
                "occurrences": 3,
                "sample_messages": [f"sample {index}"],
            }
        )
        vectors.append([score, 0.0, 0.0])
    return TemplateRegistry.from_records(records, np.array(vectors, dtype=np.float32))


class FilteredRetrievalPipelineTests(unittest.TestCase):
    def test_default_recall_settings_are_8_templates_3_logs_each_and_24_total(self) -> None:
        plan = RetrievalPlan(
            raw_query="vm spawn error",
            normalized_query="vm spawn error",
            semantic_query="vm spawn error",
        )
        config = RetrievalConfig()

        self.assertEqual(config.template_k, 8)
        self.assertEqual(config.candidate_per_template, 10)
        self.assertEqual(config.logs_per_template, 3)
        self.assertEqual(config.final_top_k, 24)
        self.assertAlmostEqual(config.semantic_weight, 0.85)
        self.assertAlmostEqual(config.recency_weight, 0.15)
        self.assertEqual(plan.top_k, 24)

    def test_high_confidence_template_candidate_is_added_to_filter(self) -> None:
        client = RecordingClient(
            search_batches=[
                [
                    hit("log-1", "template::openstack::1"),
                    hit("log-2", "template::openstack::1", score=0.7),
                ]
            ]
        )
        plan = RetrievalPlan(
            raw_query="vm spawn error",
            normalized_query="vm spawn error",
            semantic_query="vm spawn failure scheduler no valid host",
            dataset="openstack",
            level="ERROR",
            component="nova.compute.manager",
            top_k=2,
        )

        response = execute_plan(
            client=client,
            model=FakeModel(),
            plan=plan,
            template_registry=registry_with_scores([0.9, 0.2]),
            config=RetrievalConfig(min_template_score=0.7, min_template_score_gap=0.1),
        )

        self.assertEqual(response.mode, "filtered_vector")
        self.assertIn('template_id in ["template::openstack::1"]', client.search_calls[0]["filter"])
        self.assertTrue(plan.applied_template_filter)
        self.assertEqual(plan.candidate_template_ids, ["template::openstack::1"])
        self.assertFalse(plan.fallback_used)

    def test_strong_entity_is_combined_with_template_prefilter(self) -> None:
        client = RecordingClient(search_batches=[[hit("log-1", "template::openstack::1")]])
        plan = RetrievalPlan(
            raw_query="logs for blk_-123",
            normalized_query="logs for blk_-123",
            semantic_query="logs for blk_-123",
            dataset="openstack",
            entity_filters={"block_id": "blk_-123"},
            top_k=1,
        )

        execute_plan(
            client=client,
            model=FakeModel(),
            plan=plan,
            template_registry=registry_with_scores([0.95, 0.1]),
            config=RetrievalConfig(min_template_score=0.7, min_template_score_gap=0.1),
        )

        self.assertIn("template_id in", client.search_calls[0]["filter"])
        self.assertIn('payload["block_id"] == "blk_-123"', client.search_calls[0]["filter"])
        self.assertTrue(plan.applied_template_filter)
        self.assertEqual(plan.candidate_template_ids, ["template::openstack::1"])

    def test_final_results_are_capped_to_three_logs_per_template(self) -> None:
        client = RecordingClient(
            search_batches=[
                [
                    hit("log-a1", "template::openstack::1", score=0.99),
                    hit("log-a2", "template::openstack::1", score=0.98),
                    hit("log-a3", "template::openstack::1", score=0.97),
                    hit("log-a4", "template::openstack::1", score=0.96),
                    hit("log-b1", "template::openstack::2", score=0.95),
                    hit("log-b2", "template::openstack::2", score=0.94),
                    hit("log-b3", "template::openstack::2", score=0.93),
                    hit("log-b4", "template::openstack::2", score=0.92),
                ]
            ]
        )
        plan = RetrievalPlan(
            raw_query="vm spawn error",
            normalized_query="vm spawn error",
            semantic_query="vm spawn error",
            dataset="openstack",
            top_k=24,
        )

        response = execute_plan(
            client=client,
            model=FakeModel(),
            plan=plan,
            template_registry=None,
            config=RetrievalConfig(logs_per_template=3),
        )

        self.assertEqual(
            [line.primary_id for line in response.log_lines],
            ["log-a1", "log-a2", "log-a3", "log-b1", "log-b2", "log-b3"],
        )

    def test_template_filter_uses_per_template_candidate_search(self) -> None:
        client = RecordingClient(
            search_batches=[
                [hit("log-1", "template::openstack::1")],
                [hit("log-2", "template::openstack::2")],
            ]
        )
        plan = RetrievalPlan(
            raw_query="vm spawn error",
            normalized_query="vm spawn error",
            semantic_query="vm spawn error",
            dataset="openstack",
            top_k=24,
        )

        execute_plan(
            client=client,
            model=FakeModel(),
            plan=plan,
            template_registry=registry_with_scores([0.95, 0.8]),
            config=RetrievalConfig(logs_per_template=3),
        )

        self.assertEqual(len(client.search_calls), 2)
        self.assertIn('template_id in ["template::openstack::1"]', client.search_calls[0]["filter"])
        self.assertIn('template_id in ["template::openstack::2"]', client.search_calls[1]["filter"])
        self.assertEqual(client.search_calls[0]["limit"], 10)
        self.assertNotIn("group_by_field", client.search_calls[0])
        self.assertNotIn("group_size", client.search_calls[0])

    def test_recency_rerank_prefers_newer_log_when_semantic_scores_are_close(self) -> None:
        client = RecordingClient(
            search_batches=[
                [
                    hit("old", "template::openstack::1", score=0.91, timestamp_ms=1000),
                    hit("new", "template::openstack::1", score=0.90, timestamp_ms=3000),
                ]
            ]
        )
        plan = RetrievalPlan(
            raw_query="vm spawn error",
            normalized_query="vm spawn error",
            semantic_query="vm spawn error",
            dataset="openstack",
            top_k=1,
        )

        response = execute_plan(
            client=client,
            model=FakeModel(),
            plan=plan,
            template_registry=registry_with_scores([0.95]),
            config=RetrievalConfig(logs_per_template=1),
        )

        self.assertEqual([line.primary_id for line in response.log_lines], ["new"])

    def test_semantic_score_still_wins_when_gap_is_large(self) -> None:
        client = RecordingClient(
            search_batches=[
                [
                    hit("strong-old", "template::openstack::1", score=0.99, timestamp_ms=1000),
                    hit("weak-new", "template::openstack::1", score=0.50, timestamp_ms=3000),
                ]
            ]
        )
        plan = RetrievalPlan(
            raw_query="vm spawn error",
            normalized_query="vm spawn error",
            semantic_query="vm spawn error",
            dataset="openstack",
            top_k=1,
        )

        response = execute_plan(
            client=client,
            model=FakeModel(),
            plan=plan,
            template_registry=registry_with_scores([0.95]),
            config=RetrievalConfig(logs_per_template=1),
        )

        self.assertEqual([line.primary_id for line in response.log_lines], ["strong-old"])

    def test_latest_temporal_plan_sorts_candidates_by_timestamp_desc(self) -> None:
        client = RecordingClient(
            search_batches=[
                [
                    hit("semantic-old", "template::openstack::1", score=0.99, timestamp_ms=1000),
                    hit("latest", "template::openstack::1", score=0.50, timestamp_ms=3000),
                ]
            ]
        )
        plan = RetrievalPlan(
            raw_query="latest vm spawn error",
            normalized_query="latest vm spawn error",
            semantic_query="vm spawn error",
            dataset="openstack",
            sort=SortSpec(field="timestamp_ms", order="desc"),
            top_k=1,
        )

        response = execute_plan(
            client=client,
            model=FakeModel(),
            plan=plan,
            template_registry=registry_with_scores([0.95]),
            config=RetrievalConfig(logs_per_template=1),
        )

        self.assertEqual([line.primary_id for line in response.log_lines], ["latest"])

    def test_template_filter_falls_back_when_results_are_too_few(self) -> None:
        client = RecordingClient(
            search_batches=[
                [hit("log-1", "template::openstack::1", score=0.9)],
                [
                    hit("log-1", "template::openstack::1", score=0.8),
                    hit("log-2", "template::openstack::2", score=0.7),
                    hit("log-3", "template::openstack::3", score=0.6),
                ],
            ]
        )
        plan = RetrievalPlan(
            raw_query="vm spawn error",
            normalized_query="vm spawn error",
            semantic_query="vm spawn failure scheduler",
            dataset="openstack",
            level="ERROR",
            top_k=3,
        )

        response = execute_plan(
            client=client,
            model=FakeModel(),
            plan=plan,
            template_registry=registry_with_scores([0.9, 0.2]),
            config=RetrievalConfig(
                min_template_score=0.7,
                min_template_score_gap=0.1,
                min_results_with_template_filter=2,
            ),
        )

        self.assertEqual(len(client.search_calls), 2)
        self.assertIn("template_id in", client.search_calls[0]["filter"])
        self.assertNotIn("template_id in", client.search_calls[1]["filter"])
        self.assertTrue(plan.fallback_used)
        self.assertEqual([line.primary_id for line in response.log_lines], ["log-1", "log-2", "log-3"])

    def test_runtime_dataset_uses_direct_log_vector_search_when_registry_has_no_templates(self) -> None:
        client = RecordingClient(search_batches=[[runtime_hit("payment-log-1")]])
        plan = RetrievalPlan(
            raw_query="payment failed",
            normalized_query="payment failed",
            semantic_query="payment failed",
            dataset="payment-prod",
            top_k=1,
        )

        response = execute_plan(
            client=client,
            model=FakeModel(),
            plan=plan,
            template_registry=registry_with_scores([0.95]),
            config=RetrievalConfig(),
        )

        self.assertEqual(response.mode, "filtered_vector")
        self.assertEqual([line.primary_id for line in response.log_lines], ["payment-log-1"])
        self.assertEqual(plan.candidate_template_ids, [])
        self.assertFalse(plan.applied_template_filter)
        self.assertIn('dataset == "payment-prod"', client.search_calls[0]["filter"])
        self.assertNotIn("template_id in", client.search_calls[0]["filter"])


if __name__ == "__main__":
    unittest.main()
