from __future__ import annotations

import unittest
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from infra.scripts.storage.insert_chunks import (
    build_upsert_rows,
    upsert_rows,
)


def chunk(log_id: str, message: str) -> dict[str, Any]:
    return {
        "chunk_id": f"line::{log_id}",
        "log_id": log_id,
        "dataset": "apache",
        "template_id": None,
        "level": "ERROR",
        "component": "mod_jk",
        "timestamp_ms": 1,
        "embed_text": f"dataset: apache\nmessage: {message}",
        "metadata": {
            "raw_log": message,
            "message": message,
            "template": message,
            "intent": ["backend_worker_error"],
            "template_match_status": "miss",
            "template_match_method": "fallback_normalize",
            "template_match_confidence": 0.0,
            "template_slots": {},
            "signals": ["worker_error"],
            "weak_signals": [],
            "line_number": 1,
            "source_file": "test.log",
            "timestamp": "2026-07-06T00:00:00Z",
        },
    }


class MilvusUpsertSafetyTests(unittest.TestCase):
    def test_build_upsert_rows_keeps_only_last_duplicate_log_id(self) -> None:
        rows = build_upsert_rows(
            [
                chunk("apache:1", "old message"),
                chunk("apache:2", "middle message"),
                chunk("apache:1", "new message"),
            ]
        )

        self.assertEqual([row["log_id"] for row in rows], ["apache:2", "apache:1"])
        self.assertEqual(rows[-1]["payload"]["message"], "new message")

    def test_upsert_rows_rejects_incomplete_rows_before_replacing_existing_record(self) -> None:
        class FakeClient:
            def upsert(self, *, collection_name: str, data: list[dict[str, Any]]) -> dict[str, int]:
                raise AssertionError("client.upsert should not be called for invalid rows")

        invalid_row = {
            "log_id": "apache:1",
            "dataset": "apache",
            "payload": {"message": "missing vector and raw_log"},
        }

        with self.assertRaisesRegex(ValueError, "missing required fields"):
            upsert_rows(FakeClient(), "log_line", [invalid_row], batch_size=32)


if __name__ == "__main__":
    unittest.main()
