from __future__ import annotations

import unittest

from src.rag.answer import DEFAULT_RAG_BASE_URL, DEFAULT_RAG_MODEL


class RagAnswerDefaultsTests(unittest.TestCase):
    def test_answer_llm_defaults_to_cliproxy_endpoint(self) -> None:
        self.assertEqual(DEFAULT_RAG_BASE_URL, "http://localhost:8317/v1")

    def test_answer_llm_keeps_model_configurable(self) -> None:
        self.assertIsInstance(DEFAULT_RAG_MODEL, str)
        self.assertTrue(DEFAULT_RAG_MODEL)


if __name__ == "__main__":
    unittest.main()
