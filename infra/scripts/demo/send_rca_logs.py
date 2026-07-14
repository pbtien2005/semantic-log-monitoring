"""Send the fixed RCA demo logs to the ingest API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[3]))

from infra.scripts.demo.rca_logs import (
    DEMO_SCENARIOS,
    HIGH_RCA_INCIDENT_LOG_ID,
    INCIDENT_LOG_ID,
)


DEFAULT_BASE_URL = "http://localhost:8000"


def build_ingest_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/ingest/logs"


def encode_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def send_log(url: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=encode_payload(payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
        return {
            "status": response.status,
            "body": json.loads(body) if body else {},
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.getenv("RCA_DEMO_API_URL", DEFAULT_BASE_URL),
        help="Base URL of the running API, for example http://localhost:8000.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.2,
        help="Delay between log submissions.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="HTTP request timeout per log.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the payloads instead of sending them.",
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(DEMO_SCENARIOS),
        default="basic",
        help="Which fixed RCA demo payload set to send.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    url = build_ingest_url(args.base_url)
    logs = DEMO_SCENARIOS[args.scenario]
    incident_log_id = HIGH_RCA_INCIDENT_LOG_ID if args.scenario == "high" else INCIDENT_LOG_ID

    if args.dry_run:
        for payload in logs:
            print(json.dumps(payload, ensure_ascii=False))
        print(f"incident_log_id={incident_log_id}")
        return 0

    for index, payload in enumerate(logs, start=1):
        try:
            result = send_log(url, payload, args.timeout_seconds)
        except urllib.error.HTTPError as exc:
            print(
                f"failed log {index}/{len(logs)} {payload['log_id']}: "
                f"HTTP {exc.code} {exc.read().decode('utf-8')}",
                file=sys.stderr,
            )
            return 1
        except urllib.error.URLError as exc:
            print(
                f"failed log {index}/{len(logs)} {payload['log_id']}: {exc}",
                file=sys.stderr,
            )
            return 1

        print(
            f"sent {index}/{len(logs)} {payload['log_id']} "
            f"status={result['status']}"
        )
        if index < len(logs) and args.delay_seconds > 0:
            time.sleep(args.delay_seconds)

    print(f"incident_log_id={incident_log_id}")
    print(
        "demo_query=Giải thích nguyên nhân lỗi của log "
        f"{incident_log_id} trong dataset hdfs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
