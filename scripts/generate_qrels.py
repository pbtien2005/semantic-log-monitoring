"""Generate qrels and review candidates.

Version v1 keeps the original rule-based outputs. Version v2 uses scoring rules
from src.category_rules and writes qrels_v2/review_candidates_v2 only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.category_rules import ScoredCategoryResult, score_log, scoring_profile
from src.io_utils import benchmark_dir, ensure_dir, read_jsonl, write_jsonl
from src.query_bank import QUERY_BANK, QuerySpec
from src.schema import DATASETS, QrelRecord, validate_dataset, validate_qrel_record


MAX_POSITIVES = 20
MAX_UNCERTAIN = 10
MAX_HARD_NEGATIVES = 10
MIN_POSITIVES_NO_REVIEW = 3


@dataclass(slots=True)
class ScoredCandidate:
    log: dict[str, Any]
    score: ScoredCategoryResult
    predicted_label: str

    @property
    def log_id(self) -> str:
        return str(self.log["log_id"])


@dataclass(slots=True)
class GeneratedQuery:
    query_id: str
    spec: QuerySpec
    qrel: dict[str, Any]
    positives: list[ScoredCandidate]
    hard_negatives: list[ScoredCandidate]
    uncertain: list[ScoredCandidate]
    review_reasons: list[str]


def apply_filters(logs: list[dict[str, Any]], spec: QuerySpec) -> list[dict[str, Any]]:
    filtered = logs
    if spec.filters.component is not None:
        filtered = [log for log in filtered if log.get("component") == spec.filters.component]
    if spec.filters.level is not None:
        filtered = [log for log in filtered if log.get("level") == spec.filters.level]
    return filtered


def has_multiple_intents(query: str) -> bool:
    lowered = query.lower()
    return any(marker in lowered for marker in (" và ", " hoặc ", " and ", " or ", "cùng lúc", "trước sau"))


def sort_scored(candidates: list[ScoredCandidate]) -> list[ScoredCandidate]:
    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate.score.score,
            candidate.predicted_label,
            str(candidate.log.get("component") or ""),
            str(candidate.log.get("level") or ""),
            int(candidate.log.get("line_number") or 0),
            candidate.log_id,
        ),
    )


def scored_candidates(dataset: str, spec: QuerySpec, logs: list[dict[str, Any]]) -> list[ScoredCandidate]:
    profile = scoring_profile(spec.category)
    candidates: list[ScoredCandidate] = []
    for log in logs:
        result = score_log(dataset, spec.category, log)
        label = result.label(profile)
        if label == "none":
            continue
        candidates.append(ScoredCandidate(log=log, score=result, predicted_label=label))
    return sort_scored(candidates)


def same_context_score(log: dict[str, Any], positives: list[ScoredCandidate], spec: QuerySpec) -> int:
    score = 0
    positive_components = {item.log.get("component") for item in positives if item.log.get("component")}
    positive_levels = {item.log.get("level") for item in positives if item.log.get("level")}
    if spec.filters.component is not None and log.get("component") == spec.filters.component:
        score += 50
    elif log.get("component") in positive_components:
        score += 35
    if spec.filters.level is not None and log.get("level") == spec.filters.level:
        score += 20
    elif log.get("level") in positive_levels:
        score += 10
    return score


def find_hard_negatives(
    dataset: str,
    spec: QuerySpec,
    logs: list[dict[str, Any]],
    positives: list[ScoredCandidate],
    existing_hard: list[ScoredCandidate],
) -> list[ScoredCandidate]:
    if len(existing_hard) >= MAX_HARD_NEGATIVES:
        return sort_scored(existing_hard)[:MAX_HARD_NEGATIVES]

    positive_ids = {item.log_id for item in positives}
    hard_ids = {item.log_id for item in existing_hard}
    extra: list[ScoredCandidate] = []
    for log in logs:
        log_id = str(log["log_id"])
        if log_id in positive_ids or log_id in hard_ids:
            continue
        current = score_log(dataset, spec.category, log)
        if current.label(scoring_profile(spec.category)) == "positive":
            continue
        context_score = same_context_score(log, positives, spec)
        other_best: ScoredCategoryResult | None = None
        for category in DATASETS and (
            "timeout",
            "connection",
            "latency",
            "database",
            "permission",
            "storage",
            "network",
            "service_unavailable",
            "unknown",
        ):
            if category == spec.category:
                continue
            scored = score_log(dataset, category, log)
            if other_best is None or scored.score > other_best.score:
                other_best = scored
        if context_score <= 0 and (other_best is None or other_best.score < 2):
            continue
        pseudo_score = current
        pseudo_score.score = context_score + (other_best.score if other_best else 0)
        if other_best and other_best.reason:
            pseudo_score.reason = f"hard_negative: same component/level but different category; {other_best.reason}"
        else:
            pseudo_score.reason = "hard_negative: same component or level but below positive threshold"
        extra.append(ScoredCandidate(log=log, score=pseudo_score, predicted_label="hard_negative"))
    needed = MAX_HARD_NEGATIVES - len(existing_hard)
    return sort_scored(existing_hard) + sort_scored(extra)[:needed]


def label_source_for(spec: QuerySpec, positives: list[ScoredCandidate]) -> str:
    if not positives or spec.category == "unknown":
        return "auto_candidate"
    if spec.filters.component is not None or spec.filters.level is not None:
        return "template_rule"
    return "keyword_rule"


def review_reasons(
    spec: QuerySpec,
    positives: list[ScoredCandidate],
    hard_negatives: list[ScoredCandidate],
    uncertain: list[ScoredCandidate],
) -> list[str]:
    reasons: list[str] = []
    if spec.category == "unknown":
        reasons.append("category unknown")
    if spec.query_level == "hard":
        reasons.append("hard query")
    if not positives:
        reasons.append("no positive above v2 threshold")
    if 0 < len(positives) < MIN_POSITIVES_NO_REVIEW:
        reasons.append("too few positives")
    if uncertain:
        reasons.append("has uncertain candidates")
    if len(hard_negatives) < 3:
        reasons.append("too few hard negatives")
    if has_multiple_intents(spec.query):
        reasons.append("multi-clause query")
    if any(item.score.weak_only for item in positives):
        reasons.append("positive contains weak-only evidence")
    return reasons


def generate_dataset_qrels_v2(dataset: str, root: Path) -> list[GeneratedQuery]:
    logs = list(read_jsonl(benchmark_dir(dataset, root) / "logs.jsonl"))
    generated: list[GeneratedQuery] = []
    for index, spec in enumerate(QUERY_BANK[dataset], start=1):
        query_id = f"{dataset}_q{index:03d}"
        filtered = apply_filters(logs, spec)
        candidates = scored_candidates(dataset, spec, filtered)
        positives = [item for item in candidates if item.predicted_label == "positive"][:MAX_POSITIVES]
        uncertain = [item for item in candidates if item.predicted_label == "uncertain"][:MAX_UNCERTAIN]
        direct_hard = [item for item in candidates if item.predicted_label == "hard_negative"][:MAX_HARD_NEGATIVES]
        hard_negatives = find_hard_negatives(dataset, spec, logs, positives, direct_hard)
        reasons = review_reasons(spec, positives, hard_negatives, uncertain)
        qrel = QrelRecord(
            query_id=query_id,
            positive_log_ids=[item.log_id for item in positives],
            hard_negative_log_ids=[item.log_id for item in hard_negatives],
            label_source=label_source_for(spec, positives),  # type: ignore[arg-type]
            needs_review=bool(reasons),
        ).to_dict()
        validate_qrel_record(qrel)
        generated.append(
            GeneratedQuery(
                query_id=query_id,
                spec=spec,
                qrel=qrel,
                positives=positives,
                hard_negatives=hard_negatives,
                uncertain=uncertain,
                review_reasons=reasons,
            )
        )
    return generated


def review_rows(dataset: str, generated: list[GeneratedQuery]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in generated:
        if not item.positives and not item.uncertain:
            rows.append(make_review_row(dataset, item, None, "unsupported", "unsupported: no candidate above uncertain threshold"))
        for label, candidates in (
            ("positive", item.positives),
            ("hard_negative", item.hard_negatives),
            ("uncertain", item.uncertain),
        ):
            for candidate in candidates:
                rows.append(make_review_row(dataset, item, candidate, label, candidate.score.reason))
    return rows


def make_review_row(
    dataset: str,
    item: GeneratedQuery,
    candidate: ScoredCandidate | None,
    label: str,
    reason: str,
) -> dict[str, Any]:
    log = candidate.log if candidate else {}
    score = candidate.score if candidate else None
    return {
        "dataset": dataset,
        "query_id": item.query_id,
        "query": item.spec.query,
        "query_level": item.spec.query_level,
        "category": item.spec.category,
        "intent": item.spec.intent,
        "log_id": log.get("log_id", ""),
        "raw_log": log.get("raw_log", ""),
        "message": log.get("message", ""),
        "predicted_label": label,
        "reason": reason,
        "needs_review": str(item.qrel["needs_review"]).lower(),
        "category_score": score.score if score else "",
        "matched_strong_patterns": ";".join(score.matched_strong_patterns) if score else "",
        "matched_weak_patterns": ";".join(score.matched_weak_patterns) if score else "",
        "matched_negative_patterns": ";".join(score.matched_negative_patterns) if score else "",
        "numeric_evidence": score.numeric_evidence if score else "",
    }


def write_review_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    fieldnames = [
        "dataset",
        "query_id",
        "query",
        "query_level",
        "category",
        "intent",
        "log_id",
        "raw_log",
        "message",
        "predicted_label",
        "reason",
        "needs_review",
        "category_score",
        "matched_strong_patterns",
        "matched_weak_patterns",
        "matched_negative_patterns",
        "numeric_evidence",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_v1_counts(dataset: str, root: Path) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    bench = benchmark_dir(dataset, root)
    qrels_path = bench / "qrels.jsonl"
    review_path = bench / "review" / "review_candidates.csv"
    positive_counts: dict[str, int] = {}
    negative_counts: dict[str, int] = {}
    labels: dict[str, int] = Counter()
    if qrels_path.exists():
        for row in read_jsonl(qrels_path):
            positive_counts[str(row["query_id"])] = len(row["positive_log_ids"])
            negative_counts[str(row["query_id"])] = len(row["hard_negative_log_ids"])
    if review_path.exists():
        with review_path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                labels[row["predicted_label"]] += 1
    return positive_counts, negative_counts, labels


def label_counts(generated: list[GeneratedQuery]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in generated:
        counts["positive"] += len(item.positives)
        counts["hard_negative"] += len(item.hard_negatives)
        counts["uncertain"] += len(item.uncertain)
        if not item.positives and not item.uncertain:
            counts["unsupported"] += 1
    return counts


def escape_cell(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def markdown_table(rows: list[list[str]]) -> str:
    if len(rows) == 1:
        return "_None._\n"
    lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * len(rows[0])) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines) + "\n"


def build_v2_report(dataset: str, root: Path, generated: list[GeneratedQuery]) -> str:
    v1_pos, v1_neg, v1_labels = read_v1_counts(dataset, root)
    v2_labels = label_counts(generated)
    v2_pos = {item.query_id: len(item.positives) for item in generated}
    drops = sorted(
        ((qid, v1_pos.get(qid, 0), v2_pos.get(qid, 0)) for qid in v2_pos),
        key=lambda row: (row[2] - row[1], row[0]),
    )
    no_positive = [item for item in generated if not item.positives]
    needs_review = [item for item in generated if item.qrel["needs_review"]]
    examples = fixed_examples(dataset, root, generated)
    return "\n".join(
        [
            f"# Qrels V2 Generation Report: {dataset}",
            "",
            "## Summary",
            "",
            f"- Positive labels v1 vs v2: {v1_labels.get('positive', 0)} vs {v2_labels.get('positive', 0)}",
            f"- Hard negative labels v1 vs v2: {v1_labels.get('hard_negative', 0)} vs {v2_labels.get('hard_negative', 0)}",
            f"- Uncertain labels v1 vs v2: {v1_labels.get('uncertain', 0)} vs {v2_labels.get('uncertain', 0)}",
            f"- Queries with no positive: {len(no_positive)}",
            f"- Queries needs_review: {len(needs_review)}",
            f"- Avg positives/query v2: {mean(v2_pos.values()) if v2_pos else 0:.2f}",
            "",
            "## Top Positive Count Reductions",
            "",
            markdown_table(
                [["query_id", "v1_positive_count", "v2_positive_count", "delta"]]
                + [[qid, str(v1), str(v2), str(v2 - v1)] for qid, v1, v2 in drops[:15]]
            ),
            "",
            "## Queries With No Positive",
            "",
            markdown_table(
                [["query_id", "category", "query", "review_reasons"]]
                + [[item.query_id, item.spec.category, escape_cell(item.spec.query), escape_cell(", ".join(item.review_reasons))] for item in no_positive]
            ),
            "",
            "## Examples Fixed Or Downgraded",
            "",
            markdown_table([["query_id", "label", "reason", "message"]] + examples),
        ]
    )


def fixed_examples(dataset: str, root: Path, generated: list[GeneratedQuery]) -> list[list[str]]:
    review_path = benchmark_dir(dataset, root) / "review" / "review_candidates.csv"
    if not review_path.exists():
        return []
    v2_by_log: dict[tuple[str, str], tuple[str, str, str]] = {}
    for item in generated:
        for label, candidates in (("positive", item.positives), ("hard_negative", item.hard_negatives), ("uncertain", item.uncertain)):
            for candidate in candidates:
                v2_by_log[(item.query_id, candidate.log_id)] = (label, candidate.score.reason, str(candidate.log.get("message", "")))
    rows: list[list[str]] = []
    with review_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("predicted_label") != "positive":
                continue
            key = (row["query_id"], row["log_id"])
            if key in v2_by_log and v2_by_log[key][0] != "positive":
                label, reason, message = v2_by_log[key]
                rows.append([row["query_id"], label, escape_cell(reason), escape_cell(message[:220])])
            if len(rows) >= 20:
                break
    return rows


def write_outputs_v2(dataset: str, root: Path, generated: list[GeneratedQuery]) -> dict[str, Path]:
    bench = benchmark_dir(dataset, root)
    qrels_path = bench / "qrels_v2.jsonl"
    review_path = bench / "review" / "review_candidates_v2.csv"
    report_path = bench / "analysis" / "qrels_v2_generation_report.md"
    write_jsonl(qrels_path, [item.qrel for item in generated])
    write_review_csv(review_path, review_rows(dataset, generated))
    ensure_dir(report_path.parent)
    report_path.write_text(build_v2_report(dataset, root, generated), encoding="utf-8")
    return {"qrels": qrels_path, "review": review_path, "report": report_path}


def run_v2(dataset: str, root: Path) -> tuple[list[GeneratedQuery], dict[str, Path]]:
    dataset = validate_dataset(dataset)
    generated = generate_dataset_qrels_v2(dataset, root)
    outputs = write_outputs_v2(dataset, root, generated)
    return generated, outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--version", choices=("v2",), default="v2")
    return parser.parse_args()


def print_stats(dataset: str, generated: list[GeneratedQuery], outputs: dict[str, Path]) -> None:
    counts = label_counts(generated)
    needs_review = sum(1 for item in generated if item.qrel["needs_review"])
    high_risk = [
        item.query_id
        for item in generated
        if not item.positives or item.uncertain or len(item.review_reasons) >= 2
    ]
    print(f"Dataset: {dataset}")
    print(f"Positive labels: {counts.get('positive', 0)}")
    print(f"Hard negative labels: {counts.get('hard_negative', 0)}")
    print(f"Uncertain labels: {counts.get('uncertain', 0)}")
    print(f"Needs review: {needs_review}")
    print(f"High-risk queries: {', '.join(high_risk[:20]) or 'none'}")
    if len(high_risk) > 20:
        print(f"High-risk queries remaining: {len(high_risk) - 20}")
    print(f"qrels_v2: {outputs['qrels']}")
    print(f"review_candidates_v2: {outputs['review']}")
    print(f"report: {outputs['report']}")


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for index, dataset in enumerate(datasets):
        if index:
            print()
        generated, outputs = run_v2(dataset, args.root)
        print_stats(dataset, generated, outputs)


if __name__ == "__main__":
    main()
