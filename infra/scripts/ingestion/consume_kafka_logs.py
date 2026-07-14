"""Consume logs.raw from Kafka and upsert semantic log rows into Milvus."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

sys.path.append(str(Path(__file__).resolve().parents[3]))

from infra.scripts.storage.insert_chunks import (
    DEFAULT_MODEL,
    DEFAULT_URI,
    LOG_LINE_COLLECTION,
    build_upsert_rows,
    embed_rows,
    load_dependencies,
    upsert_rows,
)
from src.anomaly.enrichment import attach_anomaly, attach_missing_baseline
from src.anomaly.persistence import load_baseline
from src.anomaly.schema import AnomalyBaseline
from src.anomaly.scoring import score_log_record
from src.anomaly.state import OnlineAnomalyState
from src.chunking.builders import build_line_chunk
from src.chunking.template_discovery import upsert_pending_template_candidates
from src.chunking.template_matcher import TemplateMatcher
from src.core.schema import DATASETS
from src.ingestion.kafka_contract import (
    DEFAULT_CONSUMER_GROUP,
    DEFAULT_FAILED_TOPIC,
    DEFAULT_RAW_TOPIC,
    build_failed_message,
    normalize_raw_log_payload,
)
from src.ingestion.raw_log_store import OpenSearchRawLogStore, RawLogStoreError


class ConsumerMessage(Protocol):
    value: bytes | str | dict[str, Any]
    topic: str
    partition: int
    offset: int


class Consumer(Protocol):
    def commit(self) -> None: ...


class Producer(Protocol):
    def send(self, topic: str, value: dict[str, Any], key: str | None = None) -> None: ...


@dataclass(frozen=True, slots=True)
class IngestionBatchResult:
    processed: int
    failed: int
    index_updates: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    raw_topic: str = os.getenv("KAFKA_LOGS_RAW_TOPIC", DEFAULT_RAW_TOPIC)
    failed_topic: str = os.getenv("KAFKA_LOGS_FAILED_TOPIC", DEFAULT_FAILED_TOPIC)
    consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", DEFAULT_CONSUMER_GROUP)
    batch_size: int = int(os.getenv("INGESTION_BATCH_SIZE", "100"))
    flush_interval_seconds: float = float(os.getenv("INGESTION_FLUSH_INTERVAL_SECONDS", "2"))
    milvus_uri: str = os.getenv("MILVUS_URI", DEFAULT_URI)
    embedding_model: str = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL)
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    anomaly_enabled: bool = os.getenv("ANOMALY_ENABLED", "false").lower() in {"1", "true", "yes"}
    anomaly_baseline_path: str | None = os.getenv("ANOMALY_BASELINE_PATH") or None
    pending_template_path: str | None = os.getenv(
        "PENDING_TEMPLATE_PATH",
        "data/templates/pending_templates.jsonl",
    )


def decode_message_value(value: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    text = value.decode("utf-8") if isinstance(value, bytes) else value
    decoded = json.loads(text)
    if not isinstance(decoded, dict):
        raise ValueError("Kafka message value must be a JSON object")
    return decoded


def enrich_with_kafka_metadata(message: ConsumerMessage, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "kafka_topic": message.topic,
        "kafka_partition": message.partition,
        "kafka_offset": message.offset,
    }


def process_records(
    records: list[dict[str, Any]],
    *,
    client: Any,
    model: Any,
    batch_size: int,
    anomaly_enabled: bool = False,
    anomaly_baseline: AnomalyBaseline | None = None,
    anomaly_state: OnlineAnomalyState | None = None,
    template_matchers: dict[str, TemplateMatcher] | None = None,
    pending_template_path: Path | None = None,
) -> IngestionBatchResult:
    chunks = [
        build_line_chunk(
            record,
            template_matcher=(template_matchers or {}).get(str(record.get("dataset") or "")),
        )
        for record in records
    ]
    if pending_template_path is not None:
        upsert_pending_template_candidates(chunks, pending_template_path)
    if anomaly_enabled:
        chunks = enrich_chunks_with_anomaly(
            chunks,
            baseline=anomaly_baseline,
            state=anomaly_state,
        )
    rows = build_upsert_rows(chunks)
    embed_rows(rows, model, batch_size)
    upsert_rows(client, LOG_LINE_COLLECTION, rows, batch_size)
    index_updates = {}
    for chunk in chunks:
        metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        log_id = str(chunk.get("log_id") or "")
        if log_id:
            update_fields = {
                "candidate_id": metadata.get("candidate_id"),
                "template_id": metadata.get("template_id"),
                "template": metadata.get("template"),
                "template_match_status": metadata.get("template_match_status"),
                "anomaly": chunk.get("anomaly"),
                "anomaly_score": chunk.get("anomaly_score"),
                "anomaly_level": chunk.get("anomaly_level"),
                "anomaly_decision": chunk.get("anomaly_decision"),
                "anomaly_baseline_status": chunk.get("anomaly_baseline_status"),
                "anomaly_reasons": chunk.get("anomaly_reasons"),
                "anomaly_components": chunk.get("anomaly_components"),
            }
            index_updates[log_id] = {
                key: value for key, value in update_fields.items() if value is not None
            }
    return IngestionBatchResult(processed=len(records), failed=0, index_updates=index_updates)


def enrich_chunks_with_anomaly(
    chunks: list[dict[str, Any]],
    *,
    baseline: AnomalyBaseline | None,
    state: OnlineAnomalyState | None,
) -> list[dict[str, Any]]:
    if baseline is None:
        return [attach_missing_baseline(chunk) for chunk in chunks]

    active_state = state or OnlineAnomalyState(window_size=baseline.config.window_size)
    enriched = []
    for chunk in sorted(chunks, key=lambda item: (item.get("timestamp_ms") or 0, item.get("log_id") or "")):
        score = score_log_record(chunk, baseline, state=active_state)
        enriched.append(attach_anomaly(chunk, score))
    return enriched


def process_kafka_batch(
    messages: list[ConsumerMessage],
    *,
    processor: Any,
    consumer: Consumer,
    dlq_producer: Producer,
    failed_topic: str = DEFAULT_FAILED_TOPIC,
    raw_log_store: Any | None = None,
) -> IngestionBatchResult:
    records: list[dict[str, Any]] = []
    failed = 0

    for message in messages:
        try:
            raw_payload = decode_message_value(message.value)
            records.append(normalize_raw_log_payload(enrich_with_kafka_metadata(message, raw_payload)))
        except Exception as exc:
            failed += 1
            failed_payload = build_failed_message(
                raw_payload={"value": str(message.value)},
                error_reason=str(exc),
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
            )
            dlq_producer.send(failed_topic, failed_payload, key=f"{message.partition}:{message.offset}")

    processed = 0
    if records:
        try:
            result = processor(records)
        except Exception as exc:
            mark_raw_logs(records, raw_log_store, index_status="failed", index_error=str(exc))
            raise
        mark_raw_logs(records, raw_log_store, index_status="indexed", index_updates=result.index_updates)
        processed = int(result.processed)
        failed += int(result.failed)

    consumer.commit()
    return IngestionBatchResult(processed=processed, failed=failed)


def mark_raw_logs(
    records: list[dict[str, Any]],
    raw_log_store: Any | None,
    *,
    index_status: str,
    index_error: str | None = None,
    index_updates: dict[str, dict[str, Any]] | None = None,
) -> None:
    if raw_log_store is None:
        return
    for record in records:
        log_id = str(record.get("log_id") or "")
        if not log_id:
            continue
        try:
            raw_log_store.update_index_status(
                log_id,
                index_status=index_status,
                index_error=index_error,
                extra_fields=(index_updates or {}).get(log_id),
            )
        except RawLogStoreError as exc:
            print(f"raw log status update failed log_id={log_id}: {exc}", file=sys.stderr)


def batched_consume(consumer: Any, settings: WorkerSettings) -> list[ConsumerMessage]:
    messages: list[ConsumerMessage] = []
    deadline = time.monotonic() + settings.flush_interval_seconds
    while len(messages) < settings.batch_size and time.monotonic() < deadline:
        message = next(consumer, None)
        if message is not None:
            messages.append(message)
    return messages


def build_kafka_consumer(settings: WorkerSettings) -> Any:
    try:
        from kafka import KafkaConsumer
    except ModuleNotFoundError as exc:
        raise SystemExit("Missing dependency: kafka-python. Install requirements first.") from exc
    return KafkaConsumer(
        settings.raw_topic,
        bootstrap_servers=settings.bootstrap_servers,
        group_id=settings.consumer_group,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        consumer_timeout_ms=1000,
    )


def load_template_matchers(root: Path) -> dict[str, TemplateMatcher]:
    matchers: dict[str, TemplateMatcher] = {}
    for dataset in DATASETS:
        try:
            matchers[dataset] = TemplateMatcher.load(root, dataset)
        except FileNotFoundError:
            print(f"template catalog not found for dataset={dataset}; using dynamic templates", file=sys.stderr)
    return matchers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-servers", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    parser.add_argument("--raw-topic", default=os.getenv("KAFKA_LOGS_RAW_TOPIC", DEFAULT_RAW_TOPIC))
    parser.add_argument("--failed-topic", default=os.getenv("KAFKA_LOGS_FAILED_TOPIC", DEFAULT_FAILED_TOPIC))
    parser.add_argument("--consumer-group", default=os.getenv("KAFKA_CONSUMER_GROUP", DEFAULT_CONSUMER_GROUP))
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("INGESTION_BATCH_SIZE", "100")))
    parser.add_argument(
        "--flush-interval-seconds",
        type=float,
        default=float(os.getenv("INGESTION_FLUSH_INTERVAL_SECONDS", "2")),
    )
    parser.add_argument("--uri", default=os.getenv("MILVUS_URI", DEFAULT_URI))
    parser.add_argument("--model", default=os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL))
    parser.add_argument("--embedding-batch-size", type=int, default=int(os.getenv("EMBEDDING_BATCH_SIZE", "32")))
    parser.add_argument("--anomaly-enabled", action="store_true", default=os.getenv("ANOMALY_ENABLED", "false").lower() in {"1", "true", "yes"})
    parser.add_argument("--anomaly-baseline-path", default=os.getenv("ANOMALY_BASELINE_PATH"))
    parser.add_argument("--pending-template-path", default=os.getenv("PENDING_TEMPLATE_PATH", "data/templates/pending_templates.jsonl"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = WorkerSettings(
        bootstrap_servers=args.bootstrap_servers,
        raw_topic=args.raw_topic,
        failed_topic=args.failed_topic,
        consumer_group=args.consumer_group,
        batch_size=args.batch_size,
        flush_interval_seconds=args.flush_interval_seconds,
        milvus_uri=args.uri,
        embedding_model=args.model,
        embedding_batch_size=args.embedding_batch_size,
        anomaly_enabled=args.anomaly_enabled,
        anomaly_baseline_path=args.anomaly_baseline_path,
        pending_template_path=args.pending_template_path,
    )
    milvus_client, sentence_transformer = load_dependencies()
    client = milvus_client(uri=settings.milvus_uri)
    model = sentence_transformer(settings.embedding_model)
    anomaly_baseline = None
    if settings.anomaly_enabled and settings.anomaly_baseline_path:
        baseline_path = Path(settings.anomaly_baseline_path)
        if baseline_path.exists():
            anomaly_baseline = load_baseline(baseline_path)
    anomaly_state = (
        OnlineAnomalyState(window_size=anomaly_baseline.config.window_size)
        if anomaly_baseline is not None
        else None
    )
    template_matchers = load_template_matchers(Path.cwd())

    from src.ingestion.kafka_io import KafkaJsonProducer, KafkaIngestionSettings

    consumer = build_kafka_consumer(settings)
    dlq_producer = KafkaJsonProducer(
        KafkaIngestionSettings(
            bootstrap_servers=settings.bootstrap_servers,
            raw_topic=settings.raw_topic,
            failed_topic=settings.failed_topic,
        )
    )
    raw_log_store = OpenSearchRawLogStore()

    def processor(records: list[dict[str, Any]]) -> IngestionBatchResult:
        return process_records(
            records,
            client=client,
            model=model,
            batch_size=settings.embedding_batch_size,
            anomaly_enabled=settings.anomaly_enabled,
            anomaly_baseline=anomaly_baseline,
            anomaly_state=anomaly_state,
            template_matchers=template_matchers,
            pending_template_path=Path(settings.pending_template_path) if settings.pending_template_path else None,
        )

    print(
        "Kafka semantic ingestion worker started: "
        f"topic={settings.raw_topic} group={settings.consumer_group} batch={settings.batch_size}"
    )
    while True:
        batch = batched_consume(consumer, settings)
        if not batch:
            continue
        result = process_kafka_batch(
            batch,
            processor=processor,
            consumer=consumer,
            dlq_producer=dlq_producer,
            failed_topic=settings.failed_topic,
            raw_log_store=raw_log_store,
        )
        print(f"processed={result.processed} failed={result.failed}")


if __name__ == "__main__":
    main()
