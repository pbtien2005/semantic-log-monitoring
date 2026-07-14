from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from evaluation.io import read_jsonl


BLUEPRINT_PATH = Path("evaluation") / "scenarios" / "incident_blueprints.jsonl"


class IncidentBlueprintTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.blueprints = list(read_jsonl(BLUEPRINT_PATH))

    def test_blueprint_count_and_ids(self) -> None:
        self.assertEqual(len(self.blueprints), 15)
        ids = [str(item["incident_id"]) for item in self.blueprints]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [f"incident-{index:03d}" for index in range(1, 16)])

    def test_required_shape(self) -> None:
        for item in self.blueprints:
            with self.subTest(incident_id=item.get("incident_id")):
                self.assertIn(item["scenario_type"], {"explicit_root_cause", "silent_root_cause"})
                self.assertIsInstance(item["description"], str)
                self.assertTrue(item["description"])
                self.assertIn(item["dataset"], {"openstack", "hdfs", "apache"})
                self.assert_non_empty_list(item, "services")
                self.assertIsInstance(item["entities"], dict)
                self.assert_non_empty_list(item, "intermediate_events")
                self.assert_event(item["incident_event"])
                self.assert_noise_plan(item["noise_plan"])

    def test_explicit_and_silent_root_cause_contracts(self) -> None:
        explicit = [item for item in self.blueprints if item["scenario_type"] == "explicit_root_cause"]
        silent = [item for item in self.blueprints if item["scenario_type"] == "silent_root_cause"]
        self.assertEqual(len(explicit), 13)
        self.assertEqual(len(silent), 2)

        for item in explicit:
            with self.subTest(incident_id=item["incident_id"]):
                self.assert_event(item["root_cause_event"])
                self.assertNotIn("hidden_root_cause", item)

        for item in silent:
            with self.subTest(incident_id=item["incident_id"]):
                self.assertIsNone(item["root_cause_event"])
                self.assertIsInstance(item["hidden_root_cause"], dict)
                self.assert_non_empty_list(item["hidden_root_cause"], "expected_signals")

    def test_template_ids_are_unique_enough_for_generation(self) -> None:
        template_ids: set[str] = set()
        for item in self.blueprints:
            root_cause = item.get("root_cause_event")
            if isinstance(root_cause, dict):
                template_ids.add(str(root_cause["template_id"]))
            template_ids.add(str(item["incident_event"]["template_id"]))
            for event in item["intermediate_events"]:
                template_ids.add(str(event["template_id"]))
        self.assertGreaterEqual(len(template_ids), 40)

    def assert_event(self, value: Any) -> None:
        self.assertIsInstance(value, dict)
        for key in ("service", "component", "level", "template_id", "message"):
            self.assertIn(key, value)
            self.assertTrue(value[key])

    def assert_noise_plan(self, value: Any) -> None:
        self.assertIsInstance(value, dict)
        self.assertGreaterEqual(value["interleave_min"], 5)
        self.assertGreaterEqual(value["interleave_max"], value["interleave_min"])
        self.assertGreaterEqual(value["hard_noise_max"], value["interleave_max"])
        self.assert_non_empty_list(value, "noise_types")

    def assert_non_empty_list(self, value: dict[str, Any], key: str) -> None:
        self.assertIn(key, value)
        self.assertIsInstance(value[key], list)
        self.assertTrue(value[key])


if __name__ == "__main__":
    unittest.main()
