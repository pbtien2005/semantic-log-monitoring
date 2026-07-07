from __future__ import annotations

import unittest

from src.ingestion.kafka_contract import (
    build_failed_message,
    normalize_raw_log_payload,
    partition_key_for_log,
)


class KafkaIngestionContractTest(unittest.TestCase):
    def test_partition_key_prefers_trace_then_request_then_component(self) -> None:
        self.assertEqual(
            partition_key_for_log(
                {
                    "trace_id": "trace-1",
                    "request_id": "req-1",
                    "component": "nova-api",
                    "service": "compute",
                }
            ),
            "trace-1",
        )
        self.assertEqual(partition_key_for_log({"request_id": "req-1", "component": "nova-api"}), "req-1")
        self.assertEqual(partition_key_for_log({"component": "nova-api", "service": "compute"}), "nova-api")
        self.assertEqual(partition_key_for_log({"service": "compute"}), "compute")
        self.assertEqual(partition_key_for_log({"source_id": "payment-api-01"}), "payment-api-01")

    def test_normalized_payload_has_stable_log_id_for_duplicate_content(self) -> None:
        payload = {
            "dataset": "payment-prod",
            "source_id": "payment-api-01",
            "source": "api",
            "service": "payment-service",
            "component": "checkout",
            "timestamp": "2026-07-04T10:00:00Z",
            "level": "ERROR",
            "raw_log": "checkout failed for request req-123",
        }

        first = normalize_raw_log_payload(payload)
        second = normalize_raw_log_payload({**payload, "kafka_offset": 99})

        self.assertEqual(first["log_id"], second["log_id"])
        self.assertEqual(first["dataset"], "payment-prod")
        self.assertEqual(first["source_id"], "payment-api-01")
        self.assertEqual(first["message"], "checkout failed for request req-123")
        self.assertEqual(first["component"], "checkout")
        self.assertEqual(first["source_file"], "payment-api-01")
        self.assertEqual(first["schema_version"], 1)
        self.assertEqual(first["parser_version"], 1)
        self.assertIn("ingested_at", first)

    def test_normalized_payload_inferrs_openstack_fields_from_raw_log(self) -> None:
        payload = normalize_raw_log_payload(
            {
                "dataset": "openstack",
                "source_id": "compute-node-01",
                "raw_log": (
                    "nova-compute.log 2026-07-07 10:20:00 123 ERROR "
                    "nova.compute.manager Instance build failed: No valid host was found"
                ),
            }
        )

        self.assertEqual(payload["source_id"], "compute-node-01")
        self.assertEqual(payload["source_file"], "nova-compute.log")
        self.assertEqual(payload["timestamp"], "2026-07-07 10:20:00")
        self.assertEqual(payload["level"], "ERROR")
        self.assertEqual(payload["component"], "nova.compute.manager")
        self.assertEqual(payload["service"], "nova.compute.manager")
        self.assertEqual(payload["message"], "Instance build failed: No valid host was found")

    def test_explicit_payload_fields_override_raw_log_inference(self) -> None:
        payload = normalize_raw_log_payload(
            {
                "dataset": "openstack",
                "source_id": "compute-node-01",
                "timestamp": "2026-07-07T10:20:00Z",
                "level": "WARN",
                "service": "manual-service",
                "component": "manual-component",
                "message": "manual message",
                "raw_log": (
                    "nova-compute.log 2026-07-07 10:20:00 123 ERROR "
                    "nova.compute.manager Instance build failed: No valid host was found"
                ),
            }
        )

        self.assertEqual(payload["timestamp"], "2026-07-07T10:20:00Z")
        self.assertEqual(payload["level"], "WARN")
        self.assertEqual(payload["service"], "manual-service")
        self.assertEqual(payload["component"], "manual-component")
        self.assertEqual(payload["message"], "manual message")

    def test_normalized_payload_requires_dataset_and_source_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "dataset is required"):
            normalize_raw_log_payload({"source_id": "payment-api-01", "raw_log": "hello"})
        with self.assertRaisesRegex(ValueError, "source_id is required"):
            normalize_raw_log_payload({"dataset": "payment-prod", "raw_log": "hello"})

    def test_normalized_payload_keeps_source_metadata(self) -> None:
        payload = normalize_raw_log_payload(
            {
                "dataset": "payment-prod",
                "source_id": "payment-api-01",
                "host": "host-01",
                "environment": "prod",
                "raw_log": "ERROR checkout failed",
            }
        )

        self.assertEqual(payload["host"], "host-01")
        self.assertEqual(payload["environment"], "prod")

    def test_normalized_payload_rejects_empty_raw_log(self) -> None:
        with self.assertRaises(ValueError):
            normalize_raw_log_payload({"dataset": "payment-prod", "source_id": "payment-api-01", "raw_log": "   "})

    def test_failed_message_preserves_raw_payload_and_kafka_metadata(self) -> None:
        failed = build_failed_message(
            raw_payload={"raw_log": "broken"},
            error_reason="bad format",
            topic="logs.raw",
            partition=2,
            offset=42,
        )

        self.assertEqual(failed["raw_payload"], {"raw_log": "broken"})
        self.assertEqual(failed["error_reason"], "bad format")
        self.assertEqual(failed["topic"], "logs.raw")
        self.assertEqual(failed["partition"], 2)
        self.assertEqual(failed["offset"], 42)
        self.assertIn("failed_at", failed)


if __name__ == "__main__":
    unittest.main()
