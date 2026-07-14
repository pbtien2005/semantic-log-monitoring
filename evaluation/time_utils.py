"""Timestamp helpers for deterministic evaluation datasets."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta


def parse_iso_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def isoformat_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def timestamp_sequence(
    start: datetime,
    count: int,
    *,
    step: timedelta = timedelta(seconds=1),
) -> Iterator[str]:
    if count < 0:
        raise ValueError("count must be non-negative")
    current = start.astimezone(UTC) if start.tzinfo is not None else start.replace(tzinfo=UTC)
    for _ in range(count):
        yield isoformat_z(current)
        current += step
