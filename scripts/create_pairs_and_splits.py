"""Create silver qrels, training pairs, and query-level train/dev/test splits."""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.category_rules import score_log, scoring_profile
from src.io_utils import benchmark_dir, ensure_dir, read_jsonl, write_jsonl
from src.query_bank import QUERY_BANK
from src.schema import DATASETS, PairRecord, QrelRecord, validate_dataset, validate_pair_record, validate_qrel_record


MAX_POSITIVES_PER_QUERY = 5
MAX_NEGATIVES_PER_QUERY = 5
MAX_PAIRS_PER_QUERY = 25
TRAIN_RATIO = 0.70
DEV_RATIO = 0.15
TEST_RATIO = 0.15


def query_records(dataset: str) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for index, spec in enumerate(QUERY_BANK[dataset], start=1):
        query_id = f"{dataset}_q{index:03d}"
        records[query_id] = {
            "query_id": query_id,
            "query": spec.query,
            "dataset": dataset,
            "category": spec.category,
            "query_level": spec.query_level,
        }
    return records


def create_qrels_silver(dataset: str, root: Path) -> list[dict[str, Any]]:
    qrels_v2_path = benchmark_dir(dataset, root) / "qrels_v2.jsonl"
    if not qrels_v2_path.exists():
        raise FileNotFoundError(f"Missing qrels_v2: {qrels_v2_path}")

    silver: list[dict[str, Any]] = []
    for qrel in read_jsonl(qrels_v2_path):
        needs_review = bool(qrel["needs_review"]) or not bool(qrel["positive_log_ids"])
        row = QrelRecord(
            query_id=str(qrel["query_id"]),
            positive_log_ids=list(qrel["positive_log_ids"]),
            hard_negative_log_ids=list(qrel["hard_negative_log_ids"]),
            label_source="silver_auto_v2",  # type: ignore[arg-type]
            needs_review=needs_review,
        ).to_dict()
        validate_qrel_record(row)
        silver.append(row)
    return silver


def category_label_for_log(dataset: str, log: dict[str, Any]) -> str | None:
    best_category: str | None = None
    best_score = 0
    for category in (
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
        scored = score_log(dataset, category, log)
        if scored.label(scoring_profile(category)) == "positive" and scored.score > best_score:
            best_score = scored.score
            best_category = category
    return best_category


def fallback_negatives(
    dataset: str,
    logs: dict[str, dict[str, Any]],
    positive_ids: set[str],
    category: str,
    limit: int,
) -> list[str]:
    candidates: list[tuple[int, str]] = []
    for log_id, log in logs.items():
        if log_id in positive_ids:
            continue
        log_category = category_label_for_log(dataset, log)
        if log_category == category:
            continue
        score = 0
        if log_category is not None:
            score += 20
        if log.get("level") in {"ERROR", "WARN", "WARNING"}:
            score += 10
        candidates.append((-score, log_id))
    candidates.sort()
    return [log_id for _, log_id in candidates[:limit]]


def create_pairs(
    dataset: str,
    logs: dict[str, dict[str, Any]],
    qrels: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    queries = query_records(dataset)
    pairs: list[dict[str, Any]] = []
    for qrel in qrels:
        query_id = str(qrel["query_id"])
        query = queries[query_id]
        positive_ids = [log_id for log_id in qrel["positive_log_ids"] if log_id in logs]
        if not positive_ids:
            continue
        positives = positive_ids[:MAX_POSITIVES_PER_QUERY]
        negative_ids = [log_id for log_id in qrel["hard_negative_log_ids"] if log_id in logs and log_id not in set(positives)]
        if not negative_ids:
            negative_ids = fallback_negatives(
                dataset,
                logs,
                set(positives),
                str(query["category"]),
                MAX_NEGATIVES_PER_QUERY,
            )
        negatives = negative_ids[:MAX_NEGATIVES_PER_QUERY]
        pair_count = 0
        for positive_id in positives:
            for negative_id in negatives:
                if positive_id == negative_id:
                    continue
                pair = PairRecord(
                    query_id=query_id,
                    query=str(query["query"]),
                    positive_log=str(logs[positive_id]["message"]),
                    negative_log=str(logs[negative_id]["message"]),
                    positive_log_id=positive_id,
                    negative_log_id=negative_id,
                    dataset=validate_dataset(dataset),
                    category=query["category"],  # type: ignore[arg-type]
                    query_level=query["query_level"],  # type: ignore[arg-type]
                    label_quality="silver",
                ).to_dict()
                validate_pair_record(pair)
                pairs.append(pair)
                pair_count += 1
                if pair_count >= MAX_PAIRS_PER_QUERY:
                    break
            if pair_count >= MAX_PAIRS_PER_QUERY:
                break
    return pairs


def stratified_query_split(dataset: str, pairs: list[dict[str, Any]], seed: int) -> dict[str, set[str]]:
    query_meta = query_records(dataset)
    pair_query_ids = sorted({str(pair["query_id"]) for pair in pairs})
    buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
    for query_id in pair_query_ids:
        meta = query_meta[query_id]
        buckets[(str(meta["category"]), str(meta["query_level"]))].append(query_id)

    rng = random.Random(seed)
    splits = {"train": set(), "dev": set(), "test": set()}
    for bucket_ids in buckets.values():
        rng.shuffle(bucket_ids)
        n = len(bucket_ids)
        if n == 1:
            splits["train"].add(bucket_ids[0])
            continue
        train_n = max(1, round(n * TRAIN_RATIO))
        dev_n = round(n * DEV_RATIO)
        if train_n + dev_n >= n:
            dev_n = max(0, n - train_n - 1)
        test_n = n - train_n - dev_n
        if test_n == 0 and n >= 3:
            test_n = 1
            train_n = max(1, train_n - 1)
        splits["train"].update(bucket_ids[:train_n])
        splits["dev"].update(bucket_ids[train_n:train_n + dev_n])
        splits["test"].update(bucket_ids[train_n + dev_n:])
    all_query_ids = set(pair_query_ids)
    if len(all_query_ids) >= 3:
        rng = random.Random(seed + 1)
        for split_name in ("dev", "test"):
            if splits[split_name]:
                continue
            donor_name = "train" if len(splits["train"]) > 1 else ("test" if split_name == "dev" else "dev")
            if len(splits[donor_name]) <= 1:
                continue
            donor_ids = sorted(splits[donor_name])
            moved = donor_ids[rng.randrange(len(donor_ids))]
            splits[donor_name].remove(moved)
            splits[split_name].add(moved)
    return splits


def split_pairs(dataset: str, pairs: list[dict[str, Any]], seed: int) -> dict[str, list[dict[str, Any]]]:
    query_splits = stratified_query_split(dataset, pairs, seed)
    split_records = {"train": [], "dev": [], "test": []}
    for pair in pairs:
        query_id = str(pair["query_id"])
        for split_name, query_ids in query_splits.items():
            if query_id in query_ids:
                split_records[split_name].append(pair)
                break
    return split_records


def markdown_table(rows: list[list[str]]) -> str:
    if len(rows) == 1:
        return "_None._\n"
    lines = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * len(rows[0])) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines) + "\n"


def build_report(
    dataset: str,
    qrels: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    splits: dict[str, list[dict[str, Any]]],
) -> str:
    queries = query_records(dataset)
    positive_counts = [len(qrel["positive_log_ids"]) for qrel in qrels]
    negative_counts = [len(qrel["hard_negative_log_ids"]) for qrel in qrels]
    no_positive = [qrel for qrel in qrels if not qrel["positive_log_ids"]]
    needs_review = [qrel for qrel in qrels if qrel["needs_review"]]
    pair_query_ids = {str(pair["query_id"]) for pair in pairs}
    categories = Counter(str(queries[qid]["category"]) for qid in pair_query_ids)
    levels = Counter(str(queries[qid]["query_level"]) for qid in pair_query_ids)
    return "\n".join(
        [
            f"# Silver Benchmark Report: {dataset}",
            "",
            "This is a silver benchmark generated from qrels_v2 without manual review.",
            "",
            f"- Queries: {len(qrels)}",
            f"- Queries with positive: {len(qrels) - len(no_positive)}",
            f"- Queries without positive: {len(no_positive)}",
            f"- Queries needs_review=true: {len(needs_review)}",
            f"- Pairs: {len(pairs)}",
            f"- Train/dev/test pairs: train={len(splits['train'])}, dev={len(splits['dev'])}, test={len(splits['test'])}",
            f"- Avg positives/query: {mean(positive_counts) if positive_counts else 0:.2f}",
            f"- Avg hard negatives/query: {mean(negative_counts) if negative_counts else 0:.2f}",
            "",
            "## Category Distribution",
            "",
            markdown_table([["category", "query_count"]] + [[key, str(value)] for key, value in categories.most_common()]),
            "",
            "## Query Level Distribution",
            "",
            markdown_table([["query_level", "query_count"]] + [[key, str(value)] for key, value in levels.most_common()]),
            "",
            "## Queries Without Positive",
            "",
            markdown_table([["query_id"]] + [[str(qrel["query_id"])] for qrel in no_positive]),
        ]
    )


def run_dataset(dataset: str, root: Path, seed: int) -> dict[str, Any]:
    dataset = validate_dataset(dataset)
    bench_dir = benchmark_dir(dataset, root)
    logs = {str(log["log_id"]): log for log in read_jsonl(bench_dir / "logs.jsonl")}
    qrels = create_qrels_silver(dataset, root)
    pairs = create_pairs(dataset, logs, qrels)
    splits = split_pairs(dataset, pairs, seed)

    qrels_path = bench_dir / "qrels_silver.jsonl"
    pairs_path = bench_dir / "pairs.jsonl"
    split_dir = bench_dir / "splits"
    report_path = bench_dir / "analysis" / "silver_benchmark_report.md"
    ensure_dir(split_dir)
    ensure_dir(report_path.parent)
    write_jsonl(qrels_path, qrels)
    write_jsonl(pairs_path, pairs)
    for split_name, records in splits.items():
        write_jsonl(split_dir / f"{split_name}.jsonl", records)
    report_path.write_text(build_report(dataset, qrels, pairs, splits), encoding="utf-8")
    return {
        "qrels": qrels_path,
        "pairs": pairs_path,
        "train": split_dir / "train.jsonl",
        "dev": split_dir / "dev.jsonl",
        "test": split_dir / "test.jsonl",
        "report": report_path,
        "query_count": len(qrels),
        "pair_count": len(pairs),
        "needs_review": sum(1 for qrel in qrels if qrel["needs_review"]),
        "split_counts": {name: len(records) for name, records in splits.items()},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--seed", type=int, default=13)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for index, dataset in enumerate(datasets):
        if index:
            print()
        result = run_dataset(dataset, args.root, args.seed)
        print(f"Dataset: {dataset}")
        print(f"Queries: {result['query_count']}")
        print(f"Pairs: {result['pair_count']}")
        print(f"Needs review: {result['needs_review']}")
        print(f"qrels_silver: {result['qrels']}")
        print(f"pairs: {result['pairs']}")
        print(f"train/dev/test: {result['train']}, {result['dev']}, {result['test']}")
        print(f"split counts: {result['split_counts']}")
        print(f"report: {result['report']}")


if __name__ == "__main__":
    main()
