"""Check whether LogHub raw data is present for benchmark datasets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
sys.path.append(str(Path(__file__).resolve().parent))

from download_loghub_data import inspect_dataset, print_manual_instructions, print_status
from src.core.schema import DATASETS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=(*DATASETS, "all"), default="all")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    all_ready = True
    for index, dataset in enumerate(datasets):
        if index:
            print()
        status = inspect_dataset(dataset, args.root)
        print_status(status)
        if not status.ready:
            all_ready = False
            print_manual_instructions(dataset, status.destination)
    raise SystemExit(0 if all_ready else 1)


if __name__ == "__main__":
    main()
