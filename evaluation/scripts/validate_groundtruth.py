"""Validate generated ground-truth dataset artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.paths import dataset_dir
from evaluation.validation import validate_dataset_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=dataset_dir())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = validate_dataset_dir(args.dataset_dir)
    print(f"Dataset: {report.dataset_dir}")
    print(
        "Counts: "
        + ", ".join(f"{key}={value}" for key, value in sorted(report.counts.items()))
    )
    if report.passed:
        print("Validation: PASS")
        return
    print("Validation: FAIL")
    for error in report.errors:
        print(f"- {error}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
