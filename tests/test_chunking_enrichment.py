from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from infra.scripts.chunking.audit_chunks import quality_metrics
from infra.scripts.storage.insert_chunks import build_log_line_rows
from src.chunking.builders import build_line_chunk, build_template_chunks
from src.chunking.template_matcher import TemplateMatcher, regex_from_template


def log_record(
    *,
    dataset: str,
    message: str,
    raw_log: str | None = None,
    component: str | None = None,
    level: str | None = None,
) -> dict[str, object]:
    return {
        "log_id": f"{dataset}:1",
        "dataset": dataset,
        "raw_log": raw_log or message,
        "message": message,
        "timestamp": None,
        "component": component,
        "level": level,
        "event_id": None,
        "source_file": "test.log",
        "line_number": 1,
    }


class ChunkingEnrichmentTests(unittest.TestCase):
    def test_embed_text_omits_unknown_fields_but_keeps_debug_metadata(self) -> None:
        chunk = build_line_chunk(
            log_record(
                dataset="apache",
                level="ERROR",
                message="mod_jk child workerEnv in error state 6",
                raw_log="[error] mod_jk child workerEnv in error state 6",
            )
        )

        embed_text = chunk["embed_text"]
        metadata = chunk["metadata"]

        self.assertNotIn("component:", embed_text)
        self.assertNotIn("unknown", embed_text)
        self.assertIn("event_type: backend_worker_error", embed_text)
        self.assertIn("event_family: apache_backend", embed_text)
        self.assertIn("template: mod_jk child workerEnv in error state <state_code>", embed_text)
        self.assertIn("message: mod_jk child workerEnv in error state 6", embed_text)
        self.assertIn("backend_down", metadata["signals"])
        self.assertIn("worker_error", metadata["signals"])
        self.assertIn("unknown", metadata["weak_signals"])
        self.assertEqual(metadata["event_type"], "backend_worker_error")

    def test_domain_event_signals_are_added_for_known_patterns(self) -> None:
        chunk = build_line_chunk(
            log_record(
                dataset="apache",
                level="ERROR",
                message="[client 222.166.160.184] Directory index forbidden by rule: /var/www/html/",
            )
        )

        metadata = chunk["metadata"]

        self.assertEqual(metadata["event_type"], "directory_index_forbidden")
        self.assertEqual(metadata["event_family"], "apache_access")
        self.assertIn("directory_forbidden", metadata["signals"])
        self.assertIn("permission_denied", metadata["signals"])
        self.assertNotIn("unknown", chunk["embed_text"])

    def test_contextual_number_normalization_preserves_meaning(self) -> None:
        self.assertEqual(
            build_line_chunk(
                log_record(
                    dataset="apache",
                    level="ERROR",
                    message="mod_jk child workerEnv in error state 6",
                )
            )["metadata"]["template"],
            "mod_jk child workerEnv in error state <state_code>",
        )
        self.assertEqual(
            build_line_chunk(
                log_record(
                    dataset="openstack",
                    component="nova.compute.manager",
                    level="INFO",
                    message="[instance: b9000564-fe1a-409b-b8cc-1e88b294cd1d] Took 12.5 seconds to build instance.",
                )
            )["metadata"]["template"],
            "[instance: <instance_id>] took <duration_slow> seconds to build instance.",
        )

    def test_template_chunks_merge_signals_and_weak_signals(self) -> None:
        lines = [
            build_line_chunk(
                log_record(
                    dataset="apache",
                    level="ERROR",
                    message="mod_jk child workerEnv in error state 6",
                )
            )
        ]

        template = build_template_chunks(lines)[0]

        self.assertIn("backend_down", template["metadata"]["signals"])
        self.assertIn("unknown", template["metadata"]["weak_signals"])
        self.assertIn("event_type: backend_worker_error", template["embed_text"])
        self.assertNotIn("unknown", template["embed_text"])

    def test_quality_metrics_capture_signal_and_template_health(self) -> None:
        line_chunks = [
            build_line_chunk(
                log_record(
                    dataset="apache",
                    level="ERROR",
                    message="mod_jk child workerEnv in error state 6",
                )
            )
        ]
        template_chunks = build_template_chunks(line_chunks)

        metrics = quality_metrics(line_chunks, template_chunks)

        self.assertEqual(metrics["total_logs"], 1)
        self.assertEqual(metrics["total_templates"], 1)
        self.assertEqual(metrics["weak_signal_ratio"], "100.0%")
        self.assertEqual(metrics["unknown_signal_ratio"], "100.0%")
        self.assertIn("avg_embed_text_length", metrics)

    def test_line_chunk_uses_fixed_catalog_template_id(self) -> None:
        matcher = TemplateMatcher.from_records(
            [
                {
                    "template_id": "template::catalog::backend-worker-error",
                    "dataset": "apache",
                    "level": "ERROR",
                    "template": "mod_jk child workerEnv in error state <state_code>",
                    "regex": r"^mod_jk child workerEnv in error state (?P<state_code>-?\d+)$",
                    "event_type": "backend_worker_error",
                    "event_family": "apache_backend",
                    "intent": ["backend_worker_error", "apache_backend"],
                    "priority": 100,
                    "active": True,
                }
            ]
        )

        chunk = build_line_chunk(
            log_record(
                dataset="apache",
                level="ERROR",
                message="mod_jk child workerEnv in error state 6",
            ),
            template_matcher=matcher,
        )

        self.assertEqual(chunk["template_id"], "template::catalog::backend-worker-error")
        self.assertEqual(chunk["metadata"]["template_match_status"], "matched")
        self.assertEqual(chunk["metadata"]["template_match_method"], "regex")
        self.assertEqual(chunk["metadata"]["template_slots"]["state_code"], "6")
        self.assertEqual(chunk["metadata"]["intent"], ["backend_worker_error", "apache_backend"])
        self.assertEqual(chunk["metadata"]["event_type"], "backend_worker_error")

    def test_catalog_miss_is_explicit_but_keeps_dynamic_template_id(self) -> None:
        matcher = TemplateMatcher.from_records(
            [
                {
                    "template_id": "template::catalog::other",
                    "dataset": "apache",
                    "level": "ERROR",
                    "template": "other template",
                    "regex": r"^other template$",
                    "intent": ["other"],
                }
            ]
        )

        chunk = build_line_chunk(
            log_record(
                dataset="apache",
                level="ERROR",
                message="mod_jk child workerEnv in error state 6",
            ),
            template_matcher=matcher,
        )

        self.assertTrue(str(chunk["template_id"]).startswith("template::apache::"))
        self.assertEqual(chunk["metadata"]["template_id"], chunk["template_id"])
        self.assertEqual(chunk["metadata"]["template_match_status"], "miss")
        self.assertEqual(chunk["metadata"]["template_match_method"], "fallback_normalize")

    def test_milvus_rows_keep_catalog_template_id(self) -> None:
        matcher = TemplateMatcher.from_records(
            [
                {
                    "template_id": "template::catalog::backend-worker-error",
                    "dataset": "apache",
                    "level": "ERROR",
                    "template": "mod_jk child workerEnv in error state <state_code>",
                    "regex": r"^mod_jk child workerEnv in error state (?P<state_code>-?\d+)$",
                    "intent": ["backend_worker_error"],
                }
            ]
        )
        chunk = build_line_chunk(
            log_record(
                dataset="apache",
                level="ERROR",
                message="mod_jk child workerEnv in error state 6",
            ),
            template_matcher=matcher,
        )

        rows = build_log_line_rows([chunk])

        self.assertEqual(rows[0]["template_id"], "template::catalog::backend-worker-error")
        self.assertEqual(rows[0]["payload"]["template_id"], "template::catalog::backend-worker-error")

    def test_template_matcher_picks_highest_priority_and_exposes_slots(self) -> None:
        matcher = TemplateMatcher.from_records(
            [
                {
                    "template_id": "hdfs::generic_block",
                    "dataset": "hdfs",
                    "template": "generic block",
                    "regex": r"^.*block (?P<block_id>blk_-?\d+).*$",
                    "intent": ["generic_block"],
                    "priority": 10,
                },
                {
                    "template_id": "hdfs::served_block",
                    "dataset": "hdfs",
                    "template": "<*>:<*> Served block blk_<*> to /<*>",
                    "regex": r"^(?P<src_host>[^:\s]+):(?P<src_port>\d+) Served block (?P<block_id>blk_-?\d+) to /(?P<dest>\S+)$",
                    "intent": ["served_block", "block_transfer", "hdfs_block_lifecycle"],
                    "priority": 100,
                },
            ]
        )

        result = matcher.match(
            dataset="hdfs",
            message="10.251.42.16:50010 Served block blk_-1608999687919862906 to /10.251.214.225",
        )

        self.assertTrue(result.matched)
        self.assertEqual(result.template_id, "hdfs::served_block")
        self.assertEqual(result.slots["src_host"], "10.251.42.16")
        self.assertEqual(result.slots["block_id"], "blk_-1608999687919862906")

    def test_loghub_wildcard_template_can_generate_regex(self) -> None:
        regex = regex_from_template("<*>Served block<*>to<*>")
        matcher = TemplateMatcher.from_records(
            [
                {
                    "template_id": "hdfs::E3",
                    "dataset": "hdfs",
                    "template": "<*>Served block<*>to<*>",
                    "regex": regex,
                    "intent": ["served_block"],
                    "priority": 100,
                }
            ]
        )

        result = matcher.match(
            dataset="hdfs",
            message="10.251.42.16:50010 Served block blk_-1608999687919862906 to /10.251.214.225",
        )

        self.assertTrue(result.matched)
        self.assertEqual(result.template_id, "hdfs::E3")
        self.assertIn("wildcard", result.slots)

    def test_template_normalization_removes_real_ids(self) -> None:
        chunk = build_line_chunk(
            log_record(
                dataset="hdfs",
                component="dfs.DataNode$DataXceiver",
                level="INFO",
                message=(
                    "10.0.0.5:50010 Served block blk_123 to "
                    "/var/www/html/index.html for request req-d7bc29d0-7b99-4aeb-a356-89975043ab5e "
                    "instance d7bc29d0-7b99-4aeb-a356-89975043ab5e"
                ),
            )
        )

        template = chunk["metadata"]["template"]

        self.assertNotIn("10.0.0.5", template)
        self.assertNotIn("blk_123", template)
        self.assertNotIn("req-d7bc", template)
        self.assertNotIn("/var/www/html/index.html", template)


if __name__ == "__main__":
    unittest.main()
