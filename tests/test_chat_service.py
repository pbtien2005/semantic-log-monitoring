from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from app.chat_service import (
    ChatSettings,
    answer_chat_query,
    clear_rag_dependency_caches,
    get_embedding_model,
    get_milvus_client,
    get_pending_template_registry,
    get_template_registry,
    normalize_query_text,
    run_rag_pipeline,
)
from src.retrieval.milvus_search import RetrievalResponse
from src.retrieval.query_plan import RetrievalPlan


class ChatServiceTest(unittest.TestCase):
    def test_query_text_normalization_uses_shared_query_normalizer(self) -> None:
        self.assertEqual(normalize_query_text("  Gần\u200b   đây có lỗi  "), "gan day co loi")

    def test_recent_query_goes_through_rag_pipeline(self) -> None:
        with patch("app.chat_service.run_rag_pipeline") as run_rag_pipeline:
            run_rag_pipeline.return_value = ({"logs": []}, "day la cac log moi nhat")

            result = answer_chat_query(
                "cho toi log moi nhat trong 1 tieng gan day",
                settings=ChatSettings(enable_rag=True),
            )

        self.assertEqual(result["source"], "rag")
        self.assertIn("log moi nhat", result["answer"])
        run_rag_pipeline.assert_called_once()

    def test_recent_query_without_rag_uses_general_fallback(self) -> None:
        result = answer_chat_query(
            "cho tôi log mới nhất trong 1 tiếng gần đây",
            settings=ChatSettings(enable_rag=False),
        )

        self.assertEqual(result["source"], "fallback")
        self.assertIn("RAG", result["answer"])
        self.assertIn("log mới nhất", result["answer"])

    def test_general_query_uses_rag_pipeline(self) -> None:
        with patch("app.chat_service.run_rag_pipeline") as run_rag_pipeline:
            run_rag_pipeline.return_value = ({"rows": []}, "nova-api lỗi do timeout HDFS")

            result = answer_chat_query(
                "Tại sao nova-api lỗi?",
                dataset="openstack",
                component="nova-api",
                levels=["ERROR"],
                settings=ChatSettings(enable_rag=True),
            )

        self.assertEqual(result["source"], "rag")
        self.assertEqual(result["answer"], "nova-api lỗi do timeout HDFS")
        run_rag_pipeline.assert_called_once()

    def test_general_query_falls_back_to_local_logs_when_rag_unavailable(self) -> None:
        with patch("app.chat_service.run_rag_pipeline") as run_rag_pipeline:
            run_rag_pipeline.side_effect = ModuleNotFoundError("sentence_transformers")

            result = answer_chat_query(
                "Tại sao nova-api lỗi?",
                dataset="openstack",
                levels=["ERROR"],
                settings=ChatSettings(enable_rag=True),
            )

        self.assertEqual(result["source"], "local")
        self.assertIn("RAG semantic chưa khả dụng", result["answer"])

    def test_local_fallback_honors_query_level_and_terms_over_stale_ui_filters(self) -> None:
        with patch("app.chat_service.run_rag_pipeline") as run_rag_pipeline:
            run_rag_pipeline.side_effect = ModuleNotFoundError("sentence_transformers")

            result = answer_chat_query(
                "Tìm các lỗi ERROR liên quan đến workerEnv hoặc mod_jk",
                dataset="openstack",
                levels=["INFO"],
                settings=ChatSettings(enable_rag=True),
            )

        self.assertEqual(result["source"], "local")
        self.assertIn("ERROR", result["answer"])
        self.assertIn("workerEnv", result["answer"])
        self.assertIn("mod_jk", result["answer"])
        self.assertNotIn("nova.osapi_compute", result["answer"])

    def test_rca_query_uses_context_logs_and_ranks_prior_evidence(self) -> None:
        context_logs = [
            {
                "log_id": "hdfs:start",
                "dataset": "hdfs",
                "timestamp": "2026-07-06T02:08:00+07:00",
                "timestamp_ms": 1_000,
                "level": "INFO",
                "service": "dfs.DataNode",
                "message": "Starting thread to transfer block blk_4292382298896622412",
            },
            {
                "log_id": "hdfs:slow",
                "dataset": "hdfs",
                "timestamp": "2026-07-06T02:08:15+07:00",
                "timestamp_ms": 15_000,
                "level": "WARN",
                "service": "dfs.DataNode",
                "message": "Slow BlockReceiver write packet for block blk_4292382298896622412 took 28500 ms",
                "anomaly_score": 0.68,
            },
            {
                "log_id": "hdfs:incident",
                "dataset": "hdfs",
                "timestamp": "2026-07-06T02:08:30+07:00",
                "timestamp_ms": 30_000,
                "level": "ERROR",
                "service": "dfs.DataNode",
                "message": "IOException while serving block blk_4292382298896622412: Connection reset by peer",
                "anomaly_score": 0.94,
            },
        ]

        with patch("app.chat_service.generate_answer", return_value="LLM RCA [L01]") as generate_answer:
            result = answer_chat_query(
                "RCA 30 minutes log_id=hdfs:incident",
                context_logs=context_logs,
                settings=ChatSettings(enable_rag=True),
            )

        self.assertEqual(result["source"], "rca")
        self.assertEqual(result["answer"], "LLM RCA [L01]")
        rca_context = generate_answer.call_args.args[0]
        self.assertEqual(rca_context["plan"]["answer_mode"], "root_cause")
        self.assertEqual(rca_context["rca"]["lookback_ms"], 30 * 60 * 1000)
        self.assertTrue(all(row.get("line_id") for row in rca_context["logs"]))
        self.assertIn("hdfs:slow", [row.get("log_id") for row in rca_context["logs"]])
        self.assertIn("hdfs:incident", [row.get("log_id") for row in rca_context["logs"]])
        self.assertEqual(result["context"]["incident_log_id"], "hdfs:incident")
        self.assertGreaterEqual(result["context"]["candidate_count"], 1)
        self.assertIn("candidate_details", result["context"])
        self.assertIn("ranking_components", result["context"]["candidate_details"][0])
        self.assertEqual(result["context"]["lookback_ms"], 30 * 60 * 1000)
        self.assertIn("request_id", result["context"]["entity_keys_used"])

    def test_rca_query_uses_semantic_retrieval_when_context_has_no_evidence(self) -> None:
        incident = {
            "log_id": "hdfs:incident",
            "dataset": "hdfs",
            "timestamp": "2026-07-06T02:08:30+07:00",
            "timestamp_ms": 30_000,
            "level": "ERROR",
            "service": "dfs.DataNode",
            "message": "IOException while serving block blk_4292382298896622412: Connection reset by peer",
            "anomaly_score": 0.94,
        }
        semantic_candidate = {
            "log_id": "hdfs:semantic",
            "dataset": "hdfs",
            "timestamp": "2026-07-06T02:08:15+07:00",
            "timestamp_ms": 15_000,
            "level": "WARN",
            "service": "dfs.DataNode",
            "message": "Slow BlockReceiver write packet for block blk_4292382298896622412 took 28500 ms",
            "anomaly_score": 0.71,
        }

        with (
            patch("app.chat_service.load_local_logs", return_value=[]),
            patch("app.chat_service.run_rca_semantic_retrieval", return_value=[semantic_candidate]) as semantic,
            patch("app.chat_service.generate_answer", return_value="Semantic RCA [L01]"),
        ):
            result = answer_chat_query(
                "RCA log_id=hdfs:incident",
                incident_log=incident,
                context_logs=[],
                settings=ChatSettings(enable_rag=True),
            )

        semantic.assert_called_once()
        self.assertEqual(result["answer"], "Semantic RCA [L01]")
        self.assertIn("hdfs:semantic", result["context"]["candidate_log_ids"])
        self.assertEqual(result["context"]["retrieval_mode"], "semantic_fallback")

    def test_rca_query_loads_online_logs_when_context_is_empty(self) -> None:
        online_logs = [
            {
                "log_id": "hdfs:online-slow",
                "dataset": "hdfs",
                "timestamp": "260709 103041",
                "timestamp_ms": 1_783_573_241_000,
                "level": "ERROR",
                "component": "dfs.DataNode$DataXceiver",
                "message": "Got exception while serving blk_9000000000000000420 to /10.251.25.237",
                "block_id": "blk_9000000000000000420",
                "template_id": "hdfs::dynamic-error",
            },
            {
                "log_id": "hdfs:online-incident",
                "dataset": "hdfs",
                "timestamp": "260709 103050",
                "timestamp_ms": 1_783_573_250_000,
                "level": "ERROR",
                "component": "dfs.DataNode$DataXceiver",
                "message": "Got exception while serving blk_9000000000000000420 to /10.251.25.237",
                "block_id": "blk_9000000000000000420",
                "template_id": "hdfs::dynamic-error",
            },
        ]

        with (
            patch("app.chat_service.load_online_rca_logs", return_value=online_logs) as online,
            patch("app.chat_service.load_local_logs", return_value=[]) as local,
            patch("app.chat_service.generate_answer", return_value="Online RCA [L01]"),
        ):
            result = answer_chat_query(
                "RCA log_id=hdfs:online-incident trong dataset hdfs",
                context_logs=[],
                settings=ChatSettings(enable_rag=True),
            )

        online.assert_called_once()
        local.assert_not_called()
        self.assertEqual(result["source"], "rca")
        self.assertEqual(result["context"]["retrieval_mode"], "online")
        self.assertIn("hdfs:online-slow", result["context"]["candidate_log_ids"])

    def test_vietnamese_rca_query_with_bare_log_id_routes_to_rca(self) -> None:
        online_logs = [
            {
                "log_id": "hdfs:online-slow",
                "dataset": "hdfs",
                "timestamp": "260709 103041",
                "timestamp_ms": 1_783_573_241_000,
                "level": "ERROR",
                "component": "dfs.DataNode$DataXceiver",
                "message": "Got exception while serving blk_9000000000000000420 to /10.251.25.237",
                "block_id": "blk_9000000000000000420",
                "template_id": "hdfs::dynamic-error",
            },
            {
                "log_id": "hdfs:online-incident",
                "dataset": "hdfs",
                "timestamp": "260709 103050",
                "timestamp_ms": 1_783_573_250_000,
                "level": "ERROR",
                "component": "dfs.DataNode$DataXceiver",
                "message": "Got exception while serving blk_9000000000000000420 to /10.251.25.237",
                "block_id": "blk_9000000000000000420",
                "template_id": "hdfs::dynamic-error",
            },
        ]

        with (
            patch("app.chat_service.load_online_rca_logs", return_value=online_logs),
            patch("app.chat_service.generate_answer", return_value="Vietnamese RCA"),
        ):
            result = answer_chat_query(
                "Giải thích nguyên nhân lỗi của log hdfs:online-incident trong dataset hdfs",
                context_logs=[],
                settings=ChatSettings(enable_rag=True),
            )

        self.assertEqual(result["source"], "rca")
        self.assertEqual(result["context"]["incident_log_id"], "hdfs:online-incident")

    def test_rag_dependency_factories_cache_expensive_objects(self) -> None:
        counters = {"milvus": 0, "embedding": 0}

        class FakeMilvusClient:
            def __init__(self, *, uri: str) -> None:
                counters["milvus"] += 1
                self.uri = uri

        class FakeSentenceTransformer:
            def __init__(self, model_name: str) -> None:
                counters["embedding"] += 1
                self.model_name = model_name

        fake_pymilvus = types.SimpleNamespace(MilvusClient=FakeMilvusClient)
        fake_sentence_transformers = types.SimpleNamespace(
            SentenceTransformer=FakeSentenceTransformer,
        )

        with (
            patch.dict(
                sys.modules,
                {
                    "pymilvus": fake_pymilvus,
                    "sentence_transformers": fake_sentence_transformers,
                },
            ),
            patch("app.chat_service.TemplateRegistry.load") as load_registry,
            patch("app.chat_service.PendingTemplateRegistry.load") as load_pending_registry,
        ):
            load_registry.return_value = object()
            load_pending_registry.return_value = object()
            clear_rag_dependency_caches()

            first_client = get_milvus_client("http://milvus:19530")
            second_client = get_milvus_client("http://milvus:19530")
            first_model = get_embedding_model("test-model")
            second_model = get_embedding_model("test-model")
            first_registry = get_template_registry()
            second_registry = get_template_registry()
            first_pending_registry = get_pending_template_registry()
            second_pending_registry = get_pending_template_registry()

        self.assertIs(first_client, second_client)
        self.assertIs(first_model, second_model)
        self.assertIs(first_registry, second_registry)
        self.assertIs(first_pending_registry, second_pending_registry)
        self.assertEqual(counters["milvus"], 1)
        self.assertEqual(counters["embedding"], 1)
        load_registry.assert_called_once()
        load_pending_registry.assert_called_once()
        clear_rag_dependency_caches()

    def test_rag_pipeline_uses_cached_dependency_factories(self) -> None:
        plan = RetrievalPlan(
            raw_query="find hdfs errors",
            normalized_query="find hdfs errors",
            semantic_query="hdfs errors",
            dataset="hdfs",
            top_k=24,
            use_vector_search=True,
        )
        response = RetrievalResponse(
            mode="filtered_vector",
            filter_expr='dataset == "hdfs"',
            log_lines=[],
            templates=[],
        )

        with (
            patch("app.chat_service.plan_query", return_value=plan) as plan_query,
            patch("app.chat_service.get_milvus_client", return_value="client") as get_client,
            patch("app.chat_service.get_embedding_model", return_value="model") as get_model,
            patch("app.chat_service.get_template_registry", return_value="registry") as get_registry,
            patch("app.chat_service.get_pending_template_registry", return_value="pending_registry") as get_pending_registry,
            patch("app.chat_service.execute_plan", return_value=response) as execute_plan,
            patch("app.chat_service.build_retrieval_context", return_value={"logs": []}),
            patch("app.chat_service.generate_answer", return_value="ok"),
        ):
            context, answer = run_rag_pipeline(
                query="find hdfs errors",
                dataset="hdfs",
                component=None,
                level=None,
                settings=ChatSettings(
                    milvus_uri="http://milvus:19530",
                    embedding_model="test-model",
                ),
            )

        self.assertEqual(context, {"logs": []})
        self.assertEqual(answer, "ok")
        plan_query.assert_called_once()
        get_client.assert_called_once_with("http://milvus:19530")
        get_model.assert_called_once_with("test-model")
        get_registry.assert_called_once_with()
        get_pending_registry.assert_called_once_with()
        execute_plan.assert_called_once_with(
            client="client",
            model="model",
            plan=plan,
            template_k=8,
            template_registry="registry",
            pending_template_registry="pending_registry",
        )


if __name__ == "__main__":
    unittest.main()
