"""Create anomaly-enriched dashboard JSONL files from chunked log lines."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.anomaly.enrichment import attach_anomaly, attach_missing_baseline
from src.anomaly.persistence import load_baseline, save_baseline
from src.anomaly.schema import AnomalyBaseline, AnomalyConfig
from src.anomaly.scoring import build_baseline, score_log_record
from src.anomaly.state import OnlineAnomalyState
from src.core.io_utils import chunking_dir, read_jsonl, write_jsonl
from src.core.schema import DATASETS, validate_dataset


def load_line_chunks(dataset: str, root: Path, limit: int | None) -> list[dict[str, Any]]:
    rows = list(read_jsonl(chunking_dir(dataset, root) / "log_lines.jsonl"))
    return rows[:limit] if limit is not None else rows


def load_or_build_baseline(
    *,
    dataset: str,
    records: list[dict[str, Any]],
    baseline_path: Path,
    config: AnomalyConfig,
    build_if_missing: bool,
) -> AnomalyBaseline | None:
    if baseline_path.exists():
        return load_baseline(baseline_path)
    if not build_if_missing:
        return None

    baseline = build_baseline(records, config=config)
    save_baseline(baseline, baseline_path)
    print(f"{dataset}: built missing baseline at {baseline_path}")
    return baseline


def dashboard_record(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = chunk.get("metadata", {})
    raw_log = metadata.get("raw_log") or chunk.get("raw_log") or metadata.get("message") or ""
    message = metadata.get("message") or chunk.get("message") or raw_log
    service = (
        metadata.get("service")
        or chunk.get("service")
        or chunk.get("component")
        or metadata.get("component")
        or f"{chunk.get('dataset', 'unknown')}-service"
    )
    return {
        "dataset": chunk.get("dataset"),
        "timestamp": metadata.get("timestamp") or chunk.get("timestamp") or "",
        "timestamp_ms": chunk.get("timestamp_ms") or metadata.get("timestamp_ms"),
        "level": chunk.get("level") or metadata.get("level") or "UNKNOWN",
        "service": service,
        "component": chunk.get("component") or metadata.get("component"),
        "message": message,
        "raw_log": raw_log,
        "rawLog": raw_log,
        "log_id": chunk.get("log_id"),
        "line_number": metadata.get("line_number") or chunk.get("line_number"),
        "template_id": chunk.get("template_id") or metadata.get("template_id"),
        "event_type": chunk.get("event_type") or metadata.get("event_type"),
        "event_family": chunk.get("event_family") or metadata.get("event_family"),
        "request_id": chunk.get("request_id") or metadata.get("request_id"),
        "instance_id": chunk.get("instance_id") or metadata.get("instance_id"),
        "block_id": chunk.get("block_id") or metadata.get("block_id"),
        "host": chunk.get("host") or metadata.get("host"),
        "anomaly": chunk.get("anomaly"),
        "anomaly_score": chunk.get("anomaly_score"),
        "anomaly_level": chunk.get("anomaly_level"),
        "anomaly_decision": chunk.get("anomaly_decision"),
        "anomaly_baseline_status": chunk.get("anomaly_baseline_status"),
        "anomaly_reasons": chunk.get("anomaly_reasons"),
        "anomaly_components": chunk.get("anomaly_components"),
    }


def enrich_dataset(
    *,
    dataset: str,
    root: Path,
    baseline_dir: Path,
    output_dir: Path,
    config: AnomalyConfig,
    limit: int | None,
    build_if_missing: bool,
) -> Path:
    dataset = validate_dataset(dataset)
    records = load_line_chunks(dataset, root, limit)
    baseline_path = baseline_dir / dataset / "baseline.json"
    baseline = load_or_build_baseline(
        dataset=dataset,
        records=records,
        baseline_path=baseline_path,
        config=config,
        build_if_missing=build_if_missing,
    )

    if baseline is None:
        enriched = [attach_missing_baseline(record, "baseline_not_found") for record in records]
    else:
        state = OnlineAnomalyState(window_size=baseline.config.window_size)
        enriched = [
            attach_anomaly(record, score_log_record(record, baseline, state=state))
            for record in sorted(records, key=lambda item: (item.get("timestamp_ms") or 0, item.get("log_id") or ""))
        ]

    output_path = output_dir / dataset / "logs.jsonl"
    write_jsonl(output_path, (dashboard_record(record) for record in enriched))
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--baseline-dir", type=Path, default=Path("data/anomaly/baselines"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/anomaly/dashboard"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--build-baseline-if-missing", action="store_true")
    parser.add_argument("--min-logs-per-service", type=int, default=1000)
    parser.add_argument("--min-windows-per-service", type=int, default=50)
    parser.add_argument("--window-size", type=int, default=50)
    parser.add_argument("--window-step", type=int, default=25)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be positive")

    root = args.root.resolve()
    baseline_dir = args.baseline_dir if args.baseline_dir.is_absolute() else root / args.baseline_dir
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    config = AnomalyConfig(
        min_logs_per_service=args.min_logs_per_service,
        min_windows_per_service=args.min_windows_per_service,
        window_size=args.window_size,
        window_step=args.window_step,
    )
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for dataset in datasets:
        output_path = enrich_dataset(
            dataset=dataset,
            root=root,
            baseline_dir=baseline_dir,
            output_dir=output_dir,
            config=config,
            limit=args.limit,
            build_if_missing=args.build_baseline_if_missing,
        )
        print(f"{dataset}: wrote {output_path}")


if __name__ == "__main__":
    main()
