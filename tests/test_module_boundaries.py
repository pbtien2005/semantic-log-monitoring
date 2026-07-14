from __future__ import annotations


def test_chat_service_keeps_legacy_utility_exports() -> None:
    from app.chat_log_utils import normalize_query_text as implementation
    from app.chat_service import normalize_query_text as legacy_export

    assert legacy_export is implementation
    assert legacy_export("  Gần\u200b   đây có lỗi  ") == "gan day co loi"


def test_chat_service_keeps_legacy_rca_presenter_exports() -> None:
    from app.chat_service import summarize_rca_context as legacy_export
    from app.rca_presenter import summarize_rca_context as implementation

    assert legacy_export is implementation


def test_milvus_search_keeps_legacy_filter_exports() -> None:
    from src.retrieval.milvus_filters import build_filter as implementation
    from src.retrieval.milvus_search import build_filter as legacy_export

    assert legacy_export is implementation
    assert legacy_export(dataset='demo"set', level="ERROR") == (
        'dataset == "demo\\\"set" and level == "ERROR"'
    )


def test_milvus_search_keeps_legacy_model_and_ranking_exports() -> None:
    from src.retrieval.milvus_models import RetrievalResult as model_implementation
    from src.retrieval.milvus_ranking import merge_results as ranking_implementation
    from src.retrieval.milvus_search import RetrievalResult as legacy_model
    from src.retrieval.milvus_search import merge_results as legacy_ranking

    assert legacy_model is model_implementation
    assert legacy_ranking is ranking_implementation


def test_anomaly_scoring_keeps_legacy_math_exports() -> None:
    from src.anomaly.scoring import clamp01 as legacy_export
    from src.anomaly.scoring_math import clamp01 as implementation

    assert legacy_export is implementation
    assert legacy_export(-1.0) == 0.0
    assert legacy_export(2.0) == 1.0
