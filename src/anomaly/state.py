"""Online state for scoped anomaly scoring."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from src.anomaly.schema import TransitionScope


@dataclass(frozen=True, slots=True)
class StreamKey:
    scope: TransitionScope
    value: str

    @property
    def key(self) -> str:
        return f"{self.scope}:{self.value}"

    @property
    def is_service_fallback(self) -> bool:
        return self.scope == "service"

    @property
    def confidence(self) -> float:
        return 0.45 if self.is_service_fallback else 1.0


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _service_value(record: dict[str, Any]) -> str:
    return (
        _text(record.get("service"))
        or _text(record.get("component"))
        or _text(record.get("logger"))
        or f"{_text(record.get('dataset')) or 'unknown'}-service"
    )


def stream_key_for(record: dict[str, Any]) -> StreamKey:
    scoped_fields: tuple[tuple[TransitionScope, tuple[str, ...]], ...] = (
        ("trace", ("trace_id",)),
        ("request", ("request_id",)),
        ("session", ("session_id",)),
        ("block", ("block_id",)),
        ("instance", ("instance_id",)),
        ("entity", ("entity_id",)),
        ("host", ("host", "pod")),
        ("source", ("source_id",)),
    )
    for scope, names in scoped_fields:
        for name in names:
            value = _text(record.get(name))
            if value:
                return StreamKey(scope=scope, value=value)
    return StreamKey(scope="service", value=_service_value(record))


def service_key_for(record: dict[str, Any]) -> str:
    return _service_value(record)


class OnlineAnomalyState:
    def __init__(self, *, window_size: int) -> None:
        self.window_size = max(1, window_size)
        self._previous_template_by_stream: dict[str, str] = {}
        self._recent_windows: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=self.window_size)
        )

    def get_prev_template(self, stream_key: StreamKey) -> str | None:
        return self._previous_template_by_stream.get(stream_key.key)

    def get_recent_window(self, service: str) -> list[dict[str, Any]]:
        return list(self._recent_windows[service])

    def update(
        self,
        record: dict[str, Any],
        *,
        template_id: str,
        stream_key: StreamKey | None = None,
        service: str | None = None,
    ) -> None:
        active_stream_key = stream_key or stream_key_for(record)
        active_service = service or service_key_for(record)
        self._previous_template_by_stream[active_stream_key.key] = template_id
        self._recent_windows[active_service].append(record)
