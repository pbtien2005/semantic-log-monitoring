"""Path helpers for evaluation artifacts."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def evaluation_root(root: str | Path | None = None) -> Path:
    return Path(root) if root is not None else repo_root() / "evaluation"


def dataset_dir(root: str | Path | None = None) -> Path:
    return evaluation_root(root) / "datasets"


def scenarios_dir(root: str | Path | None = None) -> Path:
    return evaluation_root(root) / "scenarios"


def results_dir(root: str | Path | None = None) -> Path:
    return evaluation_root(root) / "results"


def reports_dir(root: str | Path | None = None) -> Path:
    return evaluation_root(root) / "reports"


def history_dir(root: str | Path | None = None) -> Path:
    return evaluation_root(root) / "history"
