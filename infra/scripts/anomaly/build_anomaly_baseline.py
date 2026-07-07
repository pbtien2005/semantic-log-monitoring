"""Build anomaly baselines from chunked log-line artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.anomaly.persistence import save_baseline
from src.anomaly.schema import AnomalyConfig, BaselineMetadata
from src.anomaly.scoring import build_baseline
from src.core.io_utils import chunking_dir, read_jsonl
from src.core.schema import DATASETS, validate_dataset


def load_line_chunks(dataset: str, root: Path, limit: int | None) -> list[dict[str, Any]]:
    path = chunking_dir(dataset, root) / "log_lines.jsonl"
    rows = list(read_jsonl(path))
    return rows[:limit] if limit is not None else rows


def build_dataset_baseline(
    *,
    dataset: str,
    root: Path,
    output_dir: Path,
    config: AnomalyConfig,
    limit: int | None,
) -> Path:
    dataset = validate_dataset(dataset)
    records = load_line_chunks(dataset, root, limit)
    baseline = build_baseline(records, config=config)
    baseline = baseline.__class__(
        service_template_counts=baseline.service_template_counts,
        service_totals=baseline.service_totals,
        transition_counts=baseline.transition_counts,
        previous_template_totals=baseline.previous_template_totals,
        service_template_vocab=baseline.service_template_vocab,
        template_p99_surprise=baseline.template_p99_surprise,
        transition_p99_surprise=baseline.transition_p99_surprise,
        window_profiles=baseline.window_profiles,
        config=baseline.config,
        metadata=BaselineMetadata(
            dataset=dataset,
            mode=config.baseline_mode,
            min_service_events=config.min_logs_per_service,
            min_windows_per_service=config.min_windows_per_service,
            smoothing_alpha=config.alpha,
            thresholds={
                "low": config.low_threshold,
                "medium": config.medium_threshold,
                "high": config.high_threshold,
            },
            scoring_weights={
                "template": config.template_weight,
                "transition": config.transition_weight,
                "window": config.window_weight,
                "service_fallback_transition": config.service_fallback_transition_weight,
                "service_fallback_window": config.service_fallback_window_weight,
                "severity_hint": config.log_level_weight,
            },
        ),
    )
    output_path = output_dir / dataset / "baseline.json"
    save_baseline(baseline, output_path)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/anomaly/baselines"),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--min-logs-per-service", type=int, default=1000)
    parser.add_argument("--min-windows-per-service", type=int, default=50)
    parser.add_argument("--window-size", type=int, default=50)
    parser.add_argument("--window-step", type=int, default=25)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be positive")

    config = AnomalyConfig(
        min_logs_per_service=args.min_logs_per_service,
        min_windows_per_service=args.min_windows_per_service,
        window_size=args.window_size,
        window_step=args.window_step,
    )
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    output_dir = args.output_dir if args.output_dir.is_absolute() else args.root / args.output_dir
    for dataset in datasets:
        output_path = build_dataset_baseline(
            dataset=dataset,
            root=args.root,
            output_dir=output_dir,
            config=config,
            limit=args.limit,
        )
        print(f"{dataset}: {output_path}")


if __name__ == "__main__":
    main()
