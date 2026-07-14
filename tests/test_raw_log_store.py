from __future__ import annotations

import json
import unittest
from io import BytesIO
from typing import Any
from urllib.error import HTTPError

from src.ingestion.raw_log_store import OpenSearchRawLogStore, RawLogStoreError, RawLogStoreSettings


class FakeHttpResponse:
    def __init__(self, payload: dict[str, Any] | None = None, status: int = 200) -> None:
        self.payload = payload or {}
        self.status = status

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class InvalidJsonResponse(FakeHttpResponse):
    def read(self) -> bytes:
        return b"not-json"


class RawLogStoreTest(unittest.TestCase):
    def test_index_log_creates_index_and_writes_document_by_log_id(self) -> None:
        calls: list[dict[str, Any]] = []

        def opener(request: Any, timeout: float = 10) -> FakeHttpResponse:
            body = request.data.decode("utf-8") if request.data else "{}"
            calls.append(
                {
                    "method": request.get_method(),
                    "url": request.full_url,
                    "body": json.loads(body),
                    "timeout": timeout,
                }
            )
            return FakeHttpResponse({"acknowledged": True})

        store = OpenSearchRawLogStore(
            RawLogStoreSettings(base_url="http://opensearch:9200", index_name="semantic-raw-logs"),
            opener=opener,
        )

        store.index_log(
            {
                "log_id": "hdfs:abc",
                "dataset": "hdfs",
                "timestamp": "2026-07-06T10:00:00+07:00",
                "raw_log": "ERROR dfs.DataNode: failed",
                "message": "ERROR dfs.DataNode: failed",
                "level": "ERROR",
                "component": "dfs.DataNode",
            },
            index_status="pending",
        )

        self.assertEqual(calls[0]["method"], "PUT")
        self.assertEqual(calls[0]["url"], "http://opensearch:9200/semantic-raw-logs")
        self.assertEqual(calls[1]["method"], "PUT")
        self.assertEqual(calls[1]["url"], "http://opensearch:9200/semantic-raw-logs/_doc/hdfs%3Aabc")
        self.assertEqual(calls[1]["body"]["index_status"], "pending")
        self.assertEqual(calls[1]["body"]["ingest_status"], "received")

    def test_recent_logs_queries_latest_documents(self) -> None:
        calls: list[dict[str, Any]] = []

        def opener(request: Any, timeout: float = 10) -> FakeHttpResponse:
            body = request.data.decode("utf-8") if request.data else "{}"
            calls.append({"method": request.get_method(), "url": request.full_url, "body": json.loads(body)})
            if request.full_url.endswith("/_search"):
                return FakeHttpResponse(
                    {
                        "hits": {
                            "hits": [
                                {"_source": {"log_id": "new", "timestamp_ms": 2}},
                                {"_source": {"log_id": "old", "timestamp_ms": 1}},
                            ]
                        }
                    }
                )
            return FakeHttpResponse()

        store = OpenSearchRawLogStore(
            RawLogStoreSettings(base_url="http://opensearch:9200", index_name="semantic-raw-logs"),
            opener=opener,
        )

        rows = store.recent_logs(limit=2)

        self.assertEqual([row["log_id"] for row in rows], ["new", "old"])
        self.assertEqual(calls[-1]["method"], "POST")
        self.assertEqual(calls[-1]["url"], "http://opensearch:9200/semantic-raw-logs/_search")
        self.assertEqual(calls[-1]["body"]["size"], 2)
        self.assertEqual(calls[-1]["body"]["sort"][0]["timestamp_ms"]["order"], "desc")

    def test_get_log_uses_http_status_for_not_found(self) -> None:
        def opener(request: Any, timeout: float = 10) -> FakeHttpResponse:
            if request.get_method() == "GET":
                raise HTTPError(
                    request.full_url,
                    404,
                    "Not Found",
                    hdrs=None,
                    fp=BytesIO(b'{"error":"missing document"}'),
                )
            return FakeHttpResponse()

        store = OpenSearchRawLogStore(
            RawLogStoreSettings(base_url="http://opensearch:9200", index_name="semantic-raw-logs"),
            opener=opener,
        )

        self.assertIsNone(store.get_log("missing"))

    def test_invalid_json_response_is_wrapped_as_store_error(self) -> None:
        store = OpenSearchRawLogStore(
            RawLogStoreSettings(base_url="http://opensearch:9200", index_name="semantic-raw-logs"),
            opener=lambda request, timeout=10: InvalidJsonResponse(),
        )

        with self.assertRaisesRegex(RawLogStoreError, "invalid JSON"):
            store.recent_logs()


if __name__ == "__main__":
    unittest.main()
