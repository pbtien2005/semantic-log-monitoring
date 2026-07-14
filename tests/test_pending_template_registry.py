from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.core.io_utils import write_jsonl
from src.retrieval.pending_template_registry import PendingTemplateRegistry


class PendingTemplateRegistryTest(unittest.TestCase):
    def test_loads_searchable_pending_templates_and_ignores_non_searchable_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(
                root / "data" / "templates" / "pending_templates.jsonl",
                [
                    {
                        "candidate_id": "template::hdfs::serve",
                        "dataset": "hdfs",
                        "template": "<*>Got exception while serving <*> to <*>",
                        "draft_regex": ".*Got exception while serving.*",
                        "occurrences": 4,
                        "status": "pending",
                        "searchable": True,
                    },
                    {
                        "candidate_id": "template::hdfs::disabled",
                        "dataset": "hdfs",
                        "template": "disabled template",
                        "draft_regex": ".*",
                        "occurrences": 10,
                        "status": "disabled",
                        "searchable": False,
                    },
                ],
            )

            registry = PendingTemplateRegistry.load(root)
            hits = registry.search("serving block exception", dataset="hdfs", top_k=5)

        self.assertEqual([hit.candidate_id for hit in hits], ["template::hdfs::serve"])
        self.assertEqual(hits[0].status, "pending")
        self.assertTrue(hits[0].searchable)
        self.assertEqual(hits[0].draft_regex, ".*Got exception while serving.*")

    def test_reload_if_changed_reuses_instance_until_pending_file_mtime_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "data" / "templates" / "pending_templates.jsonl"
            write_jsonl(
                path,
                [
                    {
                        "candidate_id": "template::hdfs::one",
                        "dataset": "hdfs",
                        "template": "first candidate",
                        "draft_regex": "first",
                        "occurrences": 1,
                        "status": "pending",
                        "searchable": True,
                    }
                ],
            )
            registry = PendingTemplateRegistry.load(root)
            same = registry.reload_if_changed()

            write_jsonl(
                path,
                [
                    {
                        "candidate_id": "template::hdfs::two",
                        "dataset": "hdfs",
                        "template": "second candidate",
                        "draft_regex": "second",
                        "occurrences": 2,
                        "status": "pending",
                        "searchable": True,
                    }
                ],
            )
            changed = same.reload_if_changed()

        self.assertIs(registry, same)
        self.assertEqual([record.candidate_id for record in changed.records], ["template::hdfs::two"])


if __name__ == "__main__":
    unittest.main()
