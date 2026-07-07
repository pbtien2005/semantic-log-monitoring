from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from src.retrieval.query_planner import (
    LLMRewriteResult,
    PlannerOptions,
    build_llm_prompts,
    plan_query,
)


class QueryRewriteMergeTests(unittest.TestCase):
    def test_llm_rewrite_runs_even_when_rule_entity_matches(self) -> None:
        rewrite = LLMRewriteResult(
            semantic_query="hdfs block transfer error failure root cause",
            answer_mode="root_cause",
        )

        with patch("src.retrieval.query_planner.llm_rewrite", return_value=rewrite) as llm_rewrite:
            plan = plan_query(
                "Trong 1 gio qua vi sao HDFS transfer block blk_-123 bi loi?",
                PlannerOptions(use_llm=True),
            )

        llm_rewrite.assert_called_once()
        self.assertEqual(plan.entity_filters, {"block_id": "blk_-123"})
        self.assertEqual(plan.semantic_query, "hdfs block transfer error failure root cause")
        self.assertEqual(plan.answer_mode, "root_cause")
        self.assertEqual(plan.dataset, "hdfs")
        self.assertIsNone(plan.level)
        self.assertTrue(plan.use_vector_search)
        self.assertNotIn("strategy", plan.model_dump())

    def test_llm_schema_ignores_strategy_and_hint_fields(self) -> None:
        rewrite = LLMRewriteResult.model_validate(
            {
                "semantic_query": "connection reset network failure",
                "answer_mode": "anomaly",
                "strategy_hint": "template_first",
                "dataset_hint": "openstack",
                "llm_time_spec": {"type": "mode", "value": "latest"},
            }
        )

        self.assertEqual(rewrite.semantic_query, "connection reset network failure")
        self.assertEqual(
            rewrite.model_dump(),
            {"semantic_query": "connection reset network failure", "answer_mode": "anomaly"},
        )

    def test_llm_rewrite_defaults_answer_mode_to_general_when_missing(self) -> None:
        rewrite = LLMRewriteResult.model_validate(
            {"semantic_query": "openstack recent errors"}
        )

        self.assertEqual(rewrite.answer_mode, "general")

    def test_llm_rewrite_prompt_receives_normalized_query_and_hard_filters(self) -> None:
        _system_prompt, user_prompt = build_llm_prompts(
            "  HDFS transfer block blk_-123 bi loi  ",
            PlannerOptions(top_k=7),
        )
        payload = json.loads(user_prompt)

        self.assertEqual(
            payload["normalized_query"]["clean_text"],
            "HDFS transfer block blk_-123 bi loi",
        )
        self.assertEqual(payload["rule_extraction"]["hard_filters"]["block_id"], "blk_-123")
        self.assertNotIn("requested_top_k", payload)
        self.assertNotIn("protected_terms", user_prompt)


if __name__ == "__main__":
    unittest.main()
