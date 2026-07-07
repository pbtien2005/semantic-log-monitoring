from __future__ import annotations

import unittest

from src.retrieval.query_entities import extract_query_entities
from src.retrieval.milvus_search import build_log_payload_filter
from src.retrieval.query_planner import PlannerOptions, plan_query


UUID = "550e8400-e29b-41d4-a716-446655440000"


class QueryEntityExtractionTests(unittest.TestCase):
    def test_block_and_request_ids_are_hard_filters(self) -> None:
        extraction = extract_query_entities(
            "find req-12345678 logs for blk_-1608999687919862906"
        )

        self.assertEqual(extraction.hard_filters["request_id"], "req-12345678")
        self.assertEqual(extraction.hard_filters["block_id"], "blk_-1608999687919862906")
        self.assertEqual(set(extraction.__dataclass_fields__), {"hard_filters"})

    def test_generic_uuid_is_soft_instead_of_instance_hard_filter(self) -> None:
        extraction = extract_query_entities(f"tim log cua {UUID}")
        plan = plan_query(f"tim log cua {UUID}", PlannerOptions())

        self.assertNotIn("instance_id", extraction.hard_filters)
        self.assertEqual(plan.entity_filters, {})
        self.assertEqual(build_log_payload_filter(f"tim log cua {UUID}"), "")

    def test_instance_context_promotes_uuid_to_instance_hard_filter(self) -> None:
        extraction = extract_query_entities(f"may ao instance {UUID} bi loi")

        self.assertEqual(extraction.hard_filters["instance_id"], UUID)
        self.assertEqual(
            build_log_payload_filter(f"may ao instance {UUID} bi loi"),
            f'payload["instance_id"] == "{UUID}"',
        )

    def test_ip_is_validated_before_filtering(self) -> None:
        valid = extract_query_entities("connection to 10.0.0.5 reset")
        invalid = extract_query_entities("connection to 999.999.999.999 reset")

        self.assertEqual(valid.hard_filters["ip"], "10.0.0.5")
        self.assertNotIn("ip", invalid.hard_filters)

    def test_http_status_requires_context(self) -> None:
        contextual = extract_query_entities("http status 503 from apache")
        bare_number = extract_query_entities("show me 503 recent logs")

        self.assertEqual(contextual.hard_filters["http_status"], 503)
        self.assertNotIn("http_status", bare_number.hard_filters)

    def test_aliases_do_not_create_entity_metadata(self) -> None:
        extraction = extract_query_entities("block transfer gan day")
        plan = plan_query("block transfer gan day", PlannerOptions())

        self.assertEqual(extraction.hard_filters, {})
        self.assertIsNone(plan.dataset)
        self.assertFalse(hasattr(plan, "soft_hints"))


if __name__ == "__main__":
    unittest.main()
