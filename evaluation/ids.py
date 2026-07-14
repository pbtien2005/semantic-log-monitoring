"""Deterministic identifier helpers for synthetic evaluation data."""

from __future__ import annotations

import hashlib


def stable_id(prefix: str, *parts: object, length: int = 16) -> str:
    if length <= 0:
        raise ValueError("length must be positive")
    payload = "\x1f".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}:{digest}"


def sequence_id(prefix: str, index: int, *, width: int = 6) -> str:
    if index < 0:
        raise ValueError("index must be non-negative")
    if width <= 0:
        raise ValueError("width must be positive")
    return f"{prefix}:{index:0{width}d}"


def scenario_id(index: int, *, width: int = 3) -> str:
    if index <= 0:
        raise ValueError("scenario index must be positive")
    return f"incident-{index:0{width}d}"


def query_id(index: int, *, width: int = 3) -> str:
    if index <= 0:
        raise ValueError("query index must be positive")
    return f"q{index:0{width}d}"
