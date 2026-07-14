"""Load generated evaluation logs through the ingestion pipeline."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from evaluation.loader import DirectModeUnavailable, LoadOptions, load_evaluation_logs
from evaluation.paths import dataset_dir


DEFAULT_BASE_URL = "http://localhost:8000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=dataset_dir() / "logs.jsonl")
    parser.add_argument("--mode", choices=("api", "direct"), default="api")
    parser.add_argument(
        "--base-url",
        default=os.getenv("EVALUATION_API_URL", DEFAULT_BASE_URL),
        help="Base URL of the running API. Defaults to EVALUATION_API_URL or http://localhost:8000.",
    )
    parser.add_argument("--endpoint", default="/api/ingest/logs")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    options = LoadOptions(
        dataset_path=args.dataset,
        mode=args.mode,
        base_url=args.base_url,
        endpoint=args.endpoint,
        batch_size=args.batch_size,
        timeout_seconds=args.timeout_seconds,
        delay_seconds=args.delay_seconds,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    try:
        summary = load_evaluation_logs(options)
    except DirectModeUnavailable as exc:
        print(f"Direct mode unavailable: {exc}")
        raise SystemExit(2) from exc

    print(json.dumps(summary.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    if summary.failed_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
