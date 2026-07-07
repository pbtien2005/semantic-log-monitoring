from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from app.chat_api import create_app


class ChatApiTest(unittest.TestCase):
    def test_chat_endpoint_returns_rag_answer(self) -> None:
        app = create_app()

        with patch("app.chat_api.answer_chat_query") as answer_chat_query:
            answer_chat_query.return_value = {
                "answer": "RAG answer from evidence",
                "source": "rag",
                "context": {"retrieved": 2},
            }

            response = TestClient(app).post(
                "/api/chat",
                content=json.dumps(
                    {
                        "query": "vì sao nova-api lỗi?",
                        "dataset": "openstack",
                        "service": "nova-api",
                        "levels": ["ERROR"],
                        "mode": "rca",
                        "incident_log": {"log_id": "openstack-1"},
                        "context_logs": [{"log_id": "openstack-1"}],
                    }
                ),
                headers={"content-type": "application/json"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "RAG answer from evidence")
        self.assertEqual(response.json()["source"], "rag")
        answer_chat_query.assert_called_once()
        _, kwargs = answer_chat_query.call_args
        self.assertEqual(kwargs["dataset"], "openstack")
        self.assertEqual(kwargs["component"], "nova-api")
        self.assertEqual(kwargs["levels"], ["ERROR"])
        self.assertEqual(kwargs["mode"], "rca")
        self.assertEqual(kwargs["incident_log"], {"log_id": "openstack-1"})
        self.assertEqual(kwargs["context_logs"], [{"log_id": "openstack-1"}])

    def test_chat_endpoint_validates_empty_query(self) -> None:
        response = TestClient(create_app()).post(
            "/api/chat",
            content=json.dumps({"query": "   "}),
            headers={"content-type": "application/json"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
