"""Query bank definitions for Semantic Log Retrieval benchmarks.

The canonical query bank currently lives in ``scripts.benchmark.generate_queries`` so the
generation CLI and validation tooling share the same deterministic seed data.
"""

from __future__ import annotations

from scripts.benchmark.generate_queries import QUERY_BANK, QuerySpec

__all__ = ["QUERY_BANK", "QuerySpec"]
