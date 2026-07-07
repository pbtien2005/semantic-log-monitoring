from __future__ import annotations

import unittest

import numpy as np

from src.retrieval.template_registry import TemplateRegistry


class TemplateRegistryTests(unittest.TestCase):
    def test_search_uses_component_fallback_when_exact_component_has_no_templates(self) -> None:
        registry = TemplateRegistry.from_records(
            [
                {
                    "template_id": "template::openstack::1",
                    "dataset": "openstack",
                    "component": "nova.compute",
                    "level": "INFO",
                    "template": "Instance build completed",
                    "search_text": "compute lifecycle instance build completed",
                    "signals": ["instance_state"],
                    "occurrences": 3,
                    "sample_messages": ["Took 1.0 seconds to build instance."],
                }
            ],
            np.array([[1.0, 0.0]], dtype=np.float32),
        )

        hits = registry.search(
            np.array([1.0, 0.0], dtype=np.float32),
            dataset="openstack",
            component="nova.compute.manager",
            level="INFO",
            top_k=1,
        )

        self.assertEqual([hit.template_id for hit in hits], ["template::openstack::1"])
        self.assertEqual(hits[0].filter_mode, "fallback_without_component")

    def test_search_returns_empty_when_top_score_is_below_threshold(self) -> None:
        registry = TemplateRegistry.from_records(
            [
                {
                    "template_id": "template::hdfs::1",
                    "dataset": "hdfs",
                    "component": "dfs.DataNode$DataXceiver",
                    "level": "WARN",
                    "template": "Exception serving block",
                    "search_text": "block transfer exception",
                    "signals": ["storage"],
                    "occurrences": 1,
                    "sample_messages": [],
                }
            ],
            np.array([[0.1, 0.0]], dtype=np.float32),
        )

        hits = registry.search(
            np.array([1.0, 0.0], dtype=np.float32),
            dataset="hdfs",
            top_k=1,
            min_score=0.5,
        )

        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
