from __future__ import annotations

import unittest

from src.retrieval.query_normalizer import normalize_query
from src.retrieval.query_planner import PlannerOptions, plan_query


class QueryNormalizerTests(unittest.TestCase):
    def test_normalize_query_removes_zero_width_and_normalizes_whitespace(self) -> None:
        result = normalize_query("  Nova\u200b   compute\tERROR  ")

        self.assertEqual(result.raw_text, "  Nova\u200b   compute\tERROR  ")
        self.assertEqual(result.clean_text, "Nova compute ERROR")
        self.assertEqual(result.lower_text, "nova compute error")
        self.assertEqual(result.accentless_text, "nova compute error")

    def test_normalize_query_builds_accentless_text(self) -> None:
        result = normalize_query("Gần đây có lỗi ở Đà Nẵng không?")

        self.assertEqual(result.clean_text, "Gần đây có lỗi ở Đà Nẵng không?")
        self.assertEqual(result.lower_text, "gần đây có lỗi ở đà nẵng không?")
        self.assertEqual(result.accentless_text, "gan day co loi o da nang khong?")

    def test_planner_uses_accentless_recent_terms(self) -> None:
        plan = plan_query("  openstack\u200b  gan   day  ERROR  ", PlannerOptions())

        self.assertFalse(plan.use_vector_search)
        self.assertNotIn("strategy", plan.model_dump())
        self.assertEqual(plan.dataset, "openstack")
        self.assertEqual(plan.level, "ERROR")
        self.assertEqual(plan.sort.field if plan.sort else None, "timestamp_ms")


if __name__ == "__main__":
    unittest.main()
