"""Retrieval and RCA metric calculations for evaluation artifacts."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any

JsonObject = dict[str, Any]


def calculate_retrieval_metrics(
    *,
    results: Sequence[JsonObject],
    queries: Sequence[JsonObject],
    incidents: Sequence[JsonObject],
    ks: Sequence[int] = (5, 10, 24),
) -> JsonObject:
    if not results:
        raise ValueError("results must not be empty")
    normalized_ks = tuple(sorted(set(int(k) for k in ks)))
    if not normalized_ks or any(k < 1 for k in normalized_ks):
        raise ValueError("ks must contain positive integers")

    query_by_id = {str(query.get("query_id")): query for query in queries}
    incident_by_id = {str(incident.get("incident_id")): incident for incident in incidents}
    experiments = sorted({str(row.get("experiment") or "unknown") for row in results})
    per_query = []

    for row in results:
        query_id = str(row.get("query_id"))
        if query_id not in query_by_id:
            raise ValueError(f"Result references unknown query_id: {query_id}")
        query = query_by_id[query_id]
        incident = incident_by_id.get(str(query.get("incident_id")))
        per_query.append(
            score_query(
                result=row,
                query=query,
                incident=incident,
                ks=normalized_ks,
            )
        )

    return {
        "experiment": experiments[0] if len(experiments) == 1 else "mixed",
        "experiments": experiments,
        "query_count": len(per_query),
        "retrieval": aggregate_retrieval(per_query, normalized_ks),
        "rca": aggregate_rca(per_query, normalized_ks),
    }


def calculate_anomaly_metrics(
    *,
    groundtruth: Sequence[JsonObject],
    predictions: Sequence[JsonObject],
    threshold: float | None = None,
) -> JsonObject:
    if not groundtruth:
        raise ValueError("groundtruth must not be empty")

    prediction_by_log_id: dict[str, JsonObject] = {}
    for prediction in predictions:
        log_id = optional_id(prediction.get("log_id"))
        if log_id is None:
            raise ValueError("Prediction row is missing log_id")
        if log_id in prediction_by_log_id:
            raise ValueError(f"Duplicate prediction for log_id: {log_id}")
        prediction_by_log_id[log_id] = prediction

    tp = fp = fn = tn = 0
    score_range_matches = 0
    severity_matches = 0
    severity_denominator = 0
    signal_overlaps: list[float] = []

    for expected_row in groundtruth:
        log_id = optional_id(expected_row.get("log_id"))
        if log_id is None:
            raise ValueError("Ground truth anomaly row is missing log_id")
        prediction = prediction_by_log_id.get(log_id, {})
        expected_anomaly = bool(expected_row.get("expected_anomaly"))
        predicted_anomaly = predicted_anomaly_value(prediction, threshold=threshold)

        if expected_anomaly and predicted_anomaly:
            tp += 1
        elif not expected_anomaly and predicted_anomaly:
            fp += 1
        elif expected_anomaly and not predicted_anomaly:
            fn += 1
        else:
            tn += 1

        if score_in_expected_range(prediction_score(prediction), expected_row):
            score_range_matches += 1

        if expected_anomaly:
            signal_overlaps.append(
                jaccard(
                    set(id_list(expected_row.get("signals"))),
                    set(id_list(prediction.get("predicted_signals") or prediction.get("signals"))),
                )
            )

        if expected_anomaly and predicted_anomaly:
            severity_denominator += 1
            if predicted_severity(prediction) == optional_id(expected_row.get("expected_severity")):
                severity_matches += 1

    evaluated_count = len(groundtruth)
    unknown_prediction_count = len(
        set(prediction_by_log_id) - {str(row.get("log_id")) for row in groundtruth}
    )
    return {
        "evaluated_count": evaluated_count,
        "prediction_count": len(predictions),
        "unknown_prediction_count": unknown_prediction_count,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision": round_float(ratio(tp, tp + fp)),
        "recall": round_float(ratio(tp, tp + fn)),
        "f1": round_float(f1(tp, fp, fn)),
        "false_positive_rate": round_float(ratio(fp, fp + tn)),
        "false_negative_rate": round_float(ratio(fn, fn + tp)),
        "accuracy": round_float(ratio(tp + tn, evaluated_count)),
        "severity_agreement": round_float(ratio(severity_matches, severity_denominator)),
        "score_range_agreement": round_float(ratio(score_range_matches, evaluated_count)),
        "signal_overlap": round_float(mean(signal_overlaps)),
    }


def score_query(
    *,
    result: JsonObject,
    query: JsonObject,
    incident: JsonObject | None,
    ks: Sequence[int],
) -> JsonObject:
    retrieved = id_list(result.get("retrieved_log_ids"))
    templates = id_list(result.get("retrieved_template_ids"))
    expected = set(id_list(query.get("expected_log_ids")))
    required = set(id_list(query.get("required_log_ids")))
    relevance = relevance_map(query.get("relevance_judgments"))
    root_cause = root_cause_id(query, incident)
    evidence = set(id_list((incident or {}).get("evidence_log_ids"))) or expected
    incident_log_id = optional_id((incident or {}).get("incident_log_id"))
    scenario_type = str((incident or {}).get("scenario_type") or "")

    retrieval_scores: JsonObject = {
        "query_id": query.get("query_id"),
        "mrr": reciprocal_rank(retrieved, expected),
    }
    rca_scores: JsonObject = {
        "query_id": query.get("query_id"),
        "root_cause_mrr": None if root_cause is None else reciprocal_rank(retrieved, {root_cause}),
        "root_cause_evaluable": root_cause is not None,
        "silent_root_cause": scenario_type == "silent_root_cause" or root_cause is None,
    }

    for k in ks:
        retrieved_at_k = retrieved[:k]
        relevant_hits = unique_hits(retrieved_at_k, expected)
        required_hits = unique_hits(retrieved_at_k, required)
        evidence_hits = unique_hits(retrieved_at_k, evidence)
        retrieval_scores[f"hit@{k}"] = 1.0 if relevant_hits else 0.0
        retrieval_scores[f"recall@{k}"] = ratio(len(relevant_hits), len(expected))
        retrieval_scores[f"required_evidence_recall@{k}"] = ratio(
            len(required_hits),
            len(required),
            empty_value=1.0,
        )
        retrieval_scores[f"precision@{k}"] = len(relevant_hits) / k
        retrieval_scores[f"ndcg@{k}"] = ndcg_at(retrieved, relevance, k)
        retrieval_scores[f"unique_template@{k}"] = unique_template_count(templates[:k])
        retrieval_scores[f"duplicate_template_ratio@{k}"] = duplicate_template_ratio(
            templates[:k]
        )

        rca_scores[f"root_cause_hit@{k}"] = (
            None if root_cause is None else (1.0 if root_cause in retrieved_at_k else 0.0)
        )
        rca_scores[f"evidence_recall@{k}"] = ratio(
            len(evidence_hits),
            len(evidence),
            empty_value=1.0,
        )
        rca_scores[f"causal_chain_completeness@{k}"] = causal_chain_complete(
            retrieved_at_k,
            evidence=evidence,
            incident_log_id=incident_log_id,
            silent_root_cause=bool(rca_scores["silent_root_cause"]),
        )

    return {
        "retrieval": retrieval_scores,
        "rca": rca_scores,
    }


def aggregate_retrieval(per_query: Sequence[JsonObject], ks: Sequence[int]) -> JsonObject:
    retrieval_rows = [row["retrieval"] for row in per_query]
    summary: JsonObject = {"mrr": round_float(mean(row["mrr"] for row in retrieval_rows))}
    for k in ks:
        for name in (
            "hit",
            "recall",
            "required_evidence_recall",
            "precision",
            "ndcg",
            "unique_template",
            "duplicate_template_ratio",
        ):
            key = f"{name}@{k}"
            summary[key] = round_float(mean(row[key] for row in retrieval_rows))
    return summary


def aggregate_rca(per_query: Sequence[JsonObject], ks: Sequence[int]) -> JsonObject:
    rca_rows = [row["rca"] for row in per_query]
    root_rows = [row for row in rca_rows if row["root_cause_evaluable"]]
    summary: JsonObject = {
        "root_cause_evaluable_query_count": len(root_rows),
        "root_cause_excluded_query_count": len(rca_rows) - len(root_rows),
        "root_cause_mrr": round_float(
            mean(row["root_cause_mrr"] for row in root_rows),
        ),
    }
    for k in ks:
        root_hit_key = f"root_cause_hit@{k}"
        summary[root_hit_key] = round_float(mean(row[root_hit_key] for row in root_rows))
        for name in ("evidence_recall", "causal_chain_completeness"):
            key = f"{name}@{k}"
            summary[key] = round_float(mean(row[key] for row in rca_rows))
    return summary


def reciprocal_rank(retrieved_ids: Sequence[str], relevant_ids: Iterable[str]) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    for index, log_id in enumerate(retrieved_ids, start=1):
        if log_id in relevant:
            return 1.0 / index
    return 0.0


def ndcg_at(
    retrieved_ids: Sequence[str],
    relevance_judgments: dict[str, int | float],
    k: int,
) -> float:
    if k < 1:
        raise ValueError("k must be positive")
    positive_relevances = [
        float(value) for value in relevance_judgments.values() if float(value) > 0
    ]
    if not positive_relevances:
        return 0.0

    seen: set[str] = set()
    ranked_relevances = []
    for log_id in retrieved_ids[:k]:
        if log_id in seen:
            ranked_relevances.append(0.0)
            continue
        seen.add(log_id)
        ranked_relevances.append(float(relevance_judgments.get(log_id, 0.0)))

    actual = dcg(ranked_relevances)
    ideal = dcg(sorted(positive_relevances, reverse=True)[:k])
    return 0.0 if ideal == 0 else actual / ideal


def dcg(relevances: Sequence[float]) -> float:
    return sum(relevance / math.log2(rank + 1) for rank, relevance in enumerate(relevances, 1))


def causal_chain_complete(
    retrieved_ids: Sequence[str],
    *,
    evidence: set[str],
    incident_log_id: str | None,
    silent_root_cause: bool,
) -> float:
    if silent_root_cause:
        return 0.0
    required_chain = set(evidence)
    if incident_log_id:
        required_chain.add(incident_log_id)
    if not required_chain:
        return 1.0
    retrieved = set(retrieved_ids)
    return 1.0 if required_chain.issubset(retrieved) else 0.0


def unique_hits(retrieved_ids: Sequence[str], relevant_ids: set[str]) -> set[str]:
    if not relevant_ids:
        return set()
    return {log_id for log_id in retrieved_ids if log_id in relevant_ids}


def unique_template_count(template_ids: Sequence[str]) -> int:
    return len({template_id for template_id in template_ids if template_id})


def duplicate_template_ratio(template_ids: Sequence[str]) -> float:
    non_empty = [template_id for template_id in template_ids if template_id]
    if not non_empty:
        return 0.0
    return 1.0 - unique_template_count(non_empty) / len(non_empty)


def predicted_anomaly_value(prediction: JsonObject, *, threshold: float | None) -> bool:
    for key in ("predicted_anomaly", "is_anomaly", "anomaly"):
        if isinstance(prediction.get(key), bool):
            return bool(prediction[key])
    score = prediction_score(prediction)
    if threshold is not None and score is not None:
        return score >= threshold
    return False


def prediction_score(prediction: JsonObject) -> float | None:
    for key in ("score", "anomaly_score"):
        value = prediction.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
    return None


def predicted_severity(prediction: JsonObject) -> str | None:
    return optional_id(prediction.get("predicted_severity")) or optional_id(
        prediction.get("severity")
    )


def score_in_expected_range(score: float | None, groundtruth_row: JsonObject) -> bool:
    score_range = groundtruth_row.get("expected_score_range")
    if score is None or not isinstance(score_range, list) or len(score_range) != 2:
        return False
    low = numeric(score_range[0])
    high = numeric(score_range[1])
    if low is None or high is None:
        return False
    return float(low) <= score <= float(high)


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def f1(tp: int, fp: int, fn: int) -> float:
    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def root_cause_id(query: JsonObject, incident: JsonObject | None) -> str | None:
    return optional_id((incident or {}).get("root_cause_log_id")) or optional_id(
        query.get("root_cause_log_id")
    )


def relevance_map(value: Any) -> dict[str, int | float]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): numeric_value
        for key, raw_value in value.items()
        if (numeric_value := numeric(raw_value)) is not None
    }


def id_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def optional_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def numeric(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def ratio(numerator: int, denominator: int, *, empty_value: float = 0.0) -> float:
    if denominator == 0:
        return empty_value
    return numerator / denominator


def mean(values: Iterable[float | None]) -> float:
    kept = [value for value in values if value is not None]
    if not kept:
        return 0.0
    return sum(kept) / len(kept)


def round_float(value: float) -> float:
    return round(value, 6)
