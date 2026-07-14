"""Print the structured retrieval plan for a user query."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))

from src.core.schema import DATASETS
from src.retrieval.query_planner import PlannerOptions, plan_query

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--dataset", choices=DATASETS)
    parser.add_argument("--level")
    parser.add_argument("--component")
    parser.add_argument("--top-k", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = plan_query(
        args.query,
        PlannerOptions(
            dataset=args.dataset,
            level=args.level,
            component=args.component,
            top_k=args.top_k,
        ),
    )
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
