"""Kafka producer utilities for ingestion API and DLQ writes."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from src.ingestion.kafka_contract import (
    DEFAULT_FAILED_TOPIC,
    DEFAULT_RAW_TOPIC,
    normalize_raw_log_payload,
    partition_key_for_log,
)


@dataclass(frozen=True, slots=True)
class KafkaIngestionSettings:
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    raw_topic: str = os.getenv("KAFKA_LOGS_RAW_TOPIC", DEFAULT_RAW_TOPIC)
    failed_topic: str = os.getenv("KAFKA_LOGS_FAILED_TOPIC", DEFAULT_FAILED_TOPIC)
    send_timeout_seconds: float = float(os.getenv("KAFKA_SEND_TIMEOUT_SECONDS", "10"))


class KafkaPublishError(RuntimeError):
    """Raised when a log cannot be published to Kafka."""


class KafkaJsonProducer:
    def __init__(self, settings: KafkaIngestionSettings | None = None) -> None:
        self.settings = settings or KafkaIngestionSettings()
        self._producer: Any | None = None

    def _load_producer(self) -> Any:
        if self._producer is None:
            try:
                from kafka import KafkaProducer
            except ModuleNotFoundError as exc:
                raise KafkaPublishError(
                    "Missing dependency: kafka-python. Install requirements-api.txt first."
                ) from exc
            self._producer = KafkaProducer(
                bootstrap_servers=self.settings.bootstrap_servers,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                key_serializer=lambda value: value.encode("utf-8") if isinstance(value, str) else value,
            )
        return self._producer

    def send(self, topic: str, value: dict[str, Any], key: str | None = None) -> None:
        producer = self._load_producer()
        future = producer.send(topic, key=key, value=value)
        future.get(timeout=self.settings.send_timeout_seconds)

    def close(self) -> None:
        if self._producer is not None:
            self._producer.close()


def publish_ingest_log(
    payload: dict[str, Any],
    *,
    settings: KafkaIngestionSettings | None = None,
    producer: KafkaJsonProducer | None = None,
) -> dict[str, str]:
    settings = settings or KafkaIngestionSettings()
    normalized = normalize_raw_log_payload(payload)
    key = partition_key_for_log(normalized)
    kafka_producer = producer or KafkaJsonProducer(settings)
    kafka_producer.send(settings.raw_topic, normalized, key=key)
    return {"topic": settings.raw_topic, "key": key, "log_id": str(normalized["log_id"])}
