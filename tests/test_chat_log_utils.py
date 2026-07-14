from __future__ import annotations

import logging

from app.chat_log_utils import filter_rca_scope
from app.chat_log_utils import load_online_rca_logs
from src.ingestion.raw_log_store import RawLogStoreError


def test_filter_rca_scope_applies_selected_levels() -> None:
    logs = [
        {"log_id": "error-1", "level": "ERROR"},
        {"log_id": "warn-1", "level": "WARN"},
        {"log_id": "info-1", "level": "INFO"},
    ]

    result = filter_rca_scope(
        logs,
        dataset=None,
        component=None,
        levels=["ERROR", "WARNING"],
    )

    assert [log["log_id"] for log in result] == ["error-1", "warn-1"]


def test_load_online_rca_logs_records_store_fallback(caplog: object) -> None:
    class FailingStore:
        def search_logs(self, **_: object) -> list[dict[str, object]]:
            raise RawLogStoreError("OpenSearch unavailable")

    with caplog.at_level(logging.WARNING, logger="app.chat_log_utils"):  # type: ignore[attr-defined]
        result = load_online_rca_logs("RCA incident", dataset="hdfs", store=FailingStore())  # type: ignore[arg-type]

    assert result == []
    assert "Falling back from online RCA logs" in caplog.text  # type: ignore[attr-defined]
