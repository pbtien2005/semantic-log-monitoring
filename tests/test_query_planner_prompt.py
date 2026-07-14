from __future__ import annotations

import unittest

from src.retrieval.query_planner import (
    PlannerOptions,
    is_latest_query,
    plan_query,
)


class QueryPlannerTests(unittest.TestCase):
    def test_vietnamese_latest_query_uses_deterministic_temporal_execution(self) -> None:
        query = "cho toi log moi nhat trong 1 tieng gan day"

        self.assertTrue(is_latest_query(query))
        plan = plan_query(query, PlannerOptions(top_k=5))

        self.assertNotIn("strategy", plan.model_dump())
        self.assertEqual(plan.answer_mode, "general")
        self.assertFalse(plan.use_vector_search)
        self.assertEqual(plan.sort.field if plan.sort else None, "timestamp_ms")
        self.assertEqual(plan.sort.order if plan.sort else None, "desc")

    def test_latest_query_with_diagnostic_terms_keeps_vector_search(self) -> None:
        plan = plan_query("latest timeout errors in openstack", PlannerOptions(top_k=5))

        self.assertTrue(plan.use_vector_search)
        self.assertEqual(plan.dataset, "openstack")
        self.assertEqual(plan.sort.field if plan.sort else None, "timestamp_ms")
        self.assertEqual(plan.sort.order if plan.sort else None, "desc")

    def test_use_llm_option_is_ignored_for_query_rewrite(self) -> None:
        plan = plan_query(
            "tim loi spawn vm trong openstack",
            PlannerOptions(use_llm=True, top_k=5),
        )

        self.assertEqual(plan.semantic_query, "tim loi spawn vm trong openstack")
        self.assertEqual(plan.answer_mode, "search_log")
        self.assertEqual(plan.dataset, "openstack")


if __name__ == "__main__":
    unittest.main()
