from __future__ import annotations

import unittest
from unittest.mock import patch

from src.retrieval.query_planner import (
    PlannerOptions,
    plan_query,
)


class QueryRewriteMergeTests(unittest.TestCase):
    def test_use_llm_option_no_longer_rewrites_query(self) -> None:
        with patch("src.retrieval.query_planner.build_retrieval_plan", wraps=plan_query.__globals__["build_retrieval_plan"]) as build_plan:
            plan = plan_query(
                "Trong 1 gio qua vi sao HDFS transfer block blk_-123 bi loi?",
                PlannerOptions(use_llm=True),
            )

        build_plan.assert_called_once()
        self.assertEqual(plan.entity_filters, {"block_id": "blk_-123"})
        self.assertEqual(
            plan.semantic_query,
            "Trong 1 gio qua vi sao HDFS transfer block blk_-123 bi loi?",
        )
        self.assertEqual(plan.answer_mode, "root_cause")
        self.assertEqual(plan.dataset, "hdfs")
        self.assertIsNone(plan.level)
        self.assertTrue(plan.use_vector_search)
        self.assertNotIn("strategy", plan.model_dump())


if __name__ == "__main__":
    unittest.main()
