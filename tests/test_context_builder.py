from __future__ import annotations

import unittest
from typing import Any

from src.rag.answer import build_answer_prompt
from src.retrieval.context_builder import build_retrieval_context, format_context_for_prompt
from src.retrieval.milvus_search import RetrievalResponse, RetrievalResult
from src.retrieval.query_plan import RetrievalPlan


def log_result(
    log_id: str,
    *,
    template_id: str,
    timestamp_ms: int | None,
    raw_log: str,
    score: float = 0.8,
) -> RetrievalResult:
    return RetrievalResult(
        collection="log_line",
        primary_id=log_id,
        score=score,
        semantic_score=score,
        source="template_filtered",
        entity={
            "log_id": log_id,
            "dataset": "openstack",
            "template_id": template_id,
            "level": "ERROR",
            "component": "nova.compute.manager",
            "timestamp_ms": timestamp_ms,
            "payload": {
                "raw_log": raw_log,
                "template_id": template_id,
                "line_number": 42,
            },
        },
    )


def template_result(template_id: str, template: str) -> RetrievalResult:
    return RetrievalResult(
        collection="template",
        primary_id=template_id,
        score=0.9,
        semantic_score=0.9,
        source="template_registry",
        entity={
            "template_id": template_id,
            "dataset": "openstack",
            "level": "ERROR",
            "component": "nova.compute.manager",
            "occurrences": 10,
            "payload": {
                "template": template,
                "signals": ["compute_lifecycle"],
                "sample_messages": ["sample message"],
            },
        },
    )


def pending_template_result(candidate_id: str, template: str) -> RetrievalResult:
    return RetrievalResult(
        collection="template",
        primary_id=candidate_id,
        score=0.7,
        semantic_score=0.7,
        source="pending_template_registry",
        entity={
            "template_id": candidate_id,
            "candidate_id": candidate_id,
            "dataset": "payment-prod",
            "occurrences": 5,
            "payload": {
                "template": template,
                "draft_regex": "checkout failed.*",
                "status": "pending",
                "searchable": True,
            },
        },
    )


class ContextBuilderTests(unittest.TestCase):
    def build_context(self) -> dict[str, Any]:
        plan = RetrievalPlan(
            raw_query="vi sao vm spawn timeout",
            normalized_query="vi sao vm spawn timeout",
            semantic_query="openstack vm spawn timeout root cause",
            dataset="openstack",
            level="ERROR",
            top_k=24,
            applied_template_filter=True,
            fallback_used=False,
            candidate_template_ids=["tpl-b", "tpl-a"],
        )
        response = RetrievalResponse(
            mode="filtered_vector",
            filter_expr='dataset == "openstack" and template_id in ["tpl-b", "tpl-a"]',
            log_lines=[
                log_result(
                    "log-late",
                    template_id="tpl-b",
                    timestamp_ms=3000,
                    raw_log="ERROR retry failed after vm spawn timeout",
                    score=0.7,
                ),
                log_result(
                    "log-early",
                    template_id="tpl-a",
                    timestamp_ms=1000,
                    raw_log="ERROR No valid host was found",
                    score=0.95,
                ),
                log_result(
                    "log-middle",
                    template_id="tpl-b",
                    timestamp_ms=2000,
                    raw_log="ERROR instance build aborted",
                    score=0.85,
                ),
            ],
            templates=[
                template_result("tpl-b", "Retry failed after <event>"),
                template_result("tpl-a", "No valid host was found"),
            ],
        )
        return build_retrieval_context(query=plan.raw_query, plan=plan, response=response)

    def test_context_assigns_stable_line_and_template_refs_sorted_by_time(self) -> None:
        context = self.build_context()

        self.assertEqual(
            [(log["line_id"], log["log_id"], log["template_ref"]) for log in context["logs"]],
            [("L01", "log-early", "T02"), ("L02", "log-middle", "T01"), ("L03", "log-late", "T01")],
        )
        self.assertEqual(
            [(template["template_ref"], template["template_id"]) for template in context["template_map"]],
            [("T01", "tpl-b"), ("T02", "tpl-a")],
        )

    def test_prompt_format_exposes_timeline_template_map_and_answer_rules(self) -> None:
        prompt = format_context_for_prompt(self.build_context())

        self.assertIn("[QUERY]", prompt)
        self.assertIn("[RETRIEVAL]", prompt)
        self.assertIn("[TEMPLATE_MAP]", prompt)
        self.assertIn("[LOGS_SORTED_BY_TIME]", prompt)
        self.assertIn("[ANSWER_RULES]", prompt)
        self.assertLess(prompt.index("[L01]"), prompt.index("[L02]"))
        self.assertLess(prompt.index("[L02]"), prompt.index("[L03]"))
        self.assertIn("[L01] ts=1000 | T02 | ERROR | component=nova.compute.manager", prompt)
        self.assertIn("T02 | template_id=tpl-a", prompt)
        self.assertIn("Cite line_id", prompt)

    def test_answer_prompt_requires_line_id_citations(self) -> None:
        prompt = build_answer_prompt(self.build_context())

        self.assertIn("Answer in Vietnamese", prompt)
        self.assertIn("cite line_id", prompt.lower())
        self.assertIn("[L01]", prompt)
        self.assertIn("Do not cite template refs as evidence unless no log line supports the claim", prompt)

    def test_context_keeps_dynamic_template_text_from_log_payload(self) -> None:
        plan = RetrievalPlan(
            raw_query="loi moi",
            normalized_query="loi moi",
            semantic_query="new error",
            dataset="openstack",
            top_k=5,
        )
        response = RetrievalResponse(
            mode="filtered_vector",
            filter_expr='dataset == "openstack"',
            log_lines=[
                RetrievalResult(
                    collection="log_line",
                    primary_id="log-new",
                    score=0.8,
                    semantic_score=0.8,
                    source="vector",
                    entity={
                        "log_id": "log-new",
                        "dataset": "openstack",
                        "template_id": "template::openstack::new",
                        "level": "ERROR",
                        "component": "nova.compute.manager",
                        "timestamp_ms": 1000,
                        "payload": {
                            "raw_log": "ERROR new scheduler failure",
                            "template_id": "template::openstack::new",
                            "template": "new scheduler failure",
                            "signals": ["scheduler_failure"],
                        },
                    },
                )
            ],
            templates=[],
        )

        context = build_retrieval_context(query=plan.raw_query, plan=plan, response=response)

        self.assertEqual(context["logs"][0]["template_ref"], "T01")
        self.assertEqual(context["template_map"][0]["template_id"], "template::openstack::new")
        self.assertEqual(context["template_map"][0]["template"], "new scheduler failure")
        self.assertNotIn("signals", context["logs"][0])
        self.assertNotIn("signals", context["template_map"][0])

    def test_context_marks_pending_template_candidates(self) -> None:
        candidate_id = "template::payment-prod::checkout"
        plan = RetrievalPlan(
            raw_query="checkout failed",
            normalized_query="checkout failed",
            semantic_query="checkout failed",
            dataset="payment-prod",
            top_k=5,
        )
        response = RetrievalResponse(
            mode="filtered_vector",
            filter_expr='dataset == "payment-prod" and payload["candidate_id"] == "template::payment-prod::checkout"',
            log_lines=[
                RetrievalResult(
                    collection="log_line",
                    primary_id="log-new",
                    score=0.8,
                    semantic_score=0.8,
                    source="candidate_filtered",
                    entity={
                        "log_id": "log-new",
                        "dataset": "payment-prod",
                        "template_id": candidate_id,
                        "timestamp_ms": 1000,
                        "payload": {
                            "candidate_id": candidate_id,
                            "raw_log": "checkout failed for request req-1",
                            "template_id": candidate_id,
                            "template": "checkout failed for request <req_id>",
                        },
                    },
                )
            ],
            templates=[pending_template_result(candidate_id, "checkout failed for request <req_id>")],
        )

        context = build_retrieval_context(query=plan.raw_query, plan=plan, response=response)

        self.assertEqual(context["templates"][0]["template_id"], candidate_id)
        self.assertEqual(context["templates"][0]["candidate_id"], candidate_id)
        self.assertEqual(context["templates"][0]["status"], "pending")
        self.assertEqual(context["templates"][0]["source"], "pending_template_registry")
        self.assertEqual(context["logs"][0]["candidate_id"], candidate_id)
        self.assertEqual(context["template_map"][0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
