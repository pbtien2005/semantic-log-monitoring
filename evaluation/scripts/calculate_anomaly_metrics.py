"""Calculate anomaly detection metrics from prediction JSONL."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.io import read_jsonl, write_json
from evaluation.metrics import calculate_anomaly_metrics
from evaluation.paths import dataset_dir, reports_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--groundtruth", type=Path, default=dataset_dir() / "anomalies.jsonl")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--threshold",
        type=float,
        help="Use score >= threshold when prediction rows do not include a boolean anomaly flag.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or reports_dir() / f"{args.predictions.stem}_anomaly_metrics.json"
    metrics = write_anomaly_metrics_report(
        groundtruth_path=args.groundtruth,
        predictions_path=args.predictions,
        output_path=output,
        threshold=args.threshold,
    )
    print(f"Wrote anomaly metrics to {output}")
    print(f"Evaluated: {metrics['evaluated_count']}")
    print(f"Precision: {metrics['precision']}")
    print(f"Recall: {metrics['recall']}")
    print(f"F1: {metrics['f1']}")


def write_anomaly_metrics_report(
    *,
    groundtruth_path: Path,
    predictions_path: Path,
    output_path: Path,
    threshold: float | None = None,
) -> dict[str, object]:
    metrics = calculate_anomaly_metrics(
        groundtruth=list(read_jsonl(groundtruth_path)),
        predictions=list(read_jsonl(predictions_path)),
        threshold=threshold,
    )
    write_json(output_path, metrics)
    return metrics


if __name__ == "__main__":
    main()
