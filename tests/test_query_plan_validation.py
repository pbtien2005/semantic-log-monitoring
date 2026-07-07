from __future__ import annotations

import unittest

from src.retrieval.query_plan import RetrievalPlan


class QueryPlanValidationTests(unittest.TestCase):
    def test_retrieval_plan_ignores_extra_llm_fields(self) -> None:
        plan = RetrievalPlan.model_validate(
            {
                "strategy": "temporal",
                "raw_query": "latest warning logs",
                "normalized_query": "latest warning logs",
                "semantic_query": "warning logs",
                "dataset": "openstack",
                "level": "warning",
                "component": None,
                "entity_filters": {},
                "time_range": {
                    "start_ms": 1000,
                    "end_ms": 2000,
                    "llm_note": "extra nested field",
                },
                "sort": {
                    "field": "timestamp_ms",
                    "order": "desc",
                    "confidence": 0.9,
                },
                "top_k": 5,
                "use_vector_search": False,
                "confidence": 0.8,
                "explanation": "extra top-level field",
            }
        )

        dumped = plan.model_dump(mode="json")

        self.assertEqual(plan.dataset, "openstack")
        self.assertEqual(plan.level, "WARN")
        self.assertEqual(plan.time_range.start_ms if plan.time_range else None, 1000)
        self.assertNotIn("strategy", dumped)
        self.assertNotIn("confidence", dumped)
        self.assertNotIn("explanation", dumped)
        self.assertNotIn("llm_note", dumped["time_range"])
        self.assertNotIn("confidence", dumped["sort"])

    def test_retrieval_plan_allows_runtime_dataset_names(self) -> None:
        plan = RetrievalPlan(dataset="payment-prod", semantic_query="payment failures")

        self.assertEqual(plan.dataset, "payment-prod")


if __name__ == "__main__":
    unittest.main()
