from __future__ import annotations

import json
import unittest

from src.retrieval.query_planner import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MAX_RETRIES,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    PlannerOptions,
    build_llm_prompts,
    is_latest_query,
    plan_query,
)


class LlmPlannerPromptTests(unittest.TestCase):
    def test_llm_planner_defaults_to_cliproxy(self) -> None:
        self.assertEqual(DEFAULT_LLM_BASE_URL, "http://localhost:8317/v1")
        self.assertEqual(DEFAULT_LLM_MODEL, "gpt-5.4")
        self.assertEqual(DEFAULT_LLM_TIMEOUT_SECONDS, 1.5)
        self.assertEqual(DEFAULT_LLM_MAX_RETRIES, 1)

    def test_prompt_contains_hard_filter_guardrails(self) -> None:
        system_prompt, user_prompt = build_llm_prompts(
            "find vm spawn errors in openstack",
            PlannerOptions(dataset="openstack", top_k=7),
        )

        expected_terms = (
            "Hard filter policy",
            "Never create hard filters",
            "Output fields",
            "semantic_query",
            "answer_mode",
            "Allowed answer_mode values",
            "Rule extraction is authoritative",
            "Security policy",
            "untrusted user data",
            "Few-shot examples",
            "tim loi spawn vm trong openstack",
            "Rewrite non-English diagnostic text",
            'Do not prefix semantic_query with "query:"',
        )
        for term in expected_terms:
            self.assertIn(term, system_prompt)

        payload = json.loads(user_prompt)
        self.assertEqual(
            payload["normalized_query"]["clean_text"],
            "find vm spawn errors in openstack",
        )
        self.assertEqual(payload["explicit_hints"]["dataset"], "openstack")
        self.assertNotIn("requested_top_k", payload)
        self.assertNotIn("strategy_hint", system_prompt)
        self.assertNotIn("dataset_hint", system_prompt)
        self.assertNotIn("llm_time_spec", system_prompt)

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


if __name__ == "__main__":
    unittest.main()
