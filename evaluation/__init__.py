"""Evaluation-only tooling for Semantic Log Monitoring.

This package must stay out of production request paths. It contains dataset
generation, validation, metrics, and experiment helpers for controlled evals.
"""

__all__ = [
    "checksums",
    "config",
    "ids",
    "io",
    "paths",
    "time_utils",
]
