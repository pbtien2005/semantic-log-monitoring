"""Fixed RCA demo logs for manual ingestion tests.

The scenario keeps one shared HDFS block id and exactly one ERROR log so RCA can
retrieve nearby WARN/INFO evidence without needing fresh live logs.
"""

from __future__ import annotations

from typing import Any


INCIDENT_LOG_ID = "hdfs:rca-demo-005"
DEMO_BLOCK_ID = "blk_4292382298896622412"
DEMO_SOURCE_ID = "hdfs-datanode-demo-01.log"
DEMO_COMPONENT = "dfs.DataNode$DataXceiver"
HIGH_RCA_INCIDENT_LOG_ID = "hdfs:rca-high-014"
HIGH_RCA_BLOCK_ID = "blk_9000000000000000420"
HIGH_RCA_SOURCE_ID = "hdfs-datanode-high-rca-demo.log"
HIGH_RCA_COMPONENT = "dfs.DataNode$DataXceiver"


RCA_DEMO_LOGS: list[dict[str, Any]] = [
    {
        "log_id": "hdfs:rca-demo-001",
        "dataset": "hdfs",
        "source_id": DEMO_SOURCE_ID,
        "source": "api-demo",
        "service": "hdfs-datanode",
        "component": DEMO_COMPONENT,
        "host": "dn-demo-01",
        "environment": "demo",
        "timestamp": "2026-07-09T10:15:00+07:00",
        "level": "INFO",
        "line_number": 1,
        "message": (
            f"Receiving block {DEMO_BLOCK_ID} src: /10.251.42.16:50010 "
            "dest: /10.251.214.225:50010"
        ),
        "raw_log": (
            f"260709 101500 18421 INFO {DEMO_COMPONENT}: Receiving block "
            f"{DEMO_BLOCK_ID} src: /10.251.42.16:50010 "
            "dest: /10.251.214.225:50010"
        ),
    },
    {
        "log_id": "hdfs:rca-demo-002",
        "dataset": "hdfs",
        "source_id": DEMO_SOURCE_ID,
        "source": "api-demo",
        "service": "hdfs-datanode",
        "component": DEMO_COMPONENT,
        "host": "dn-demo-01",
        "environment": "demo",
        "timestamp": "2026-07-09T10:15:04+07:00",
        "level": "INFO",
        "line_number": 2,
        "message": (
            f"PacketResponder 1 for block {DEMO_BLOCK_ID} started, client "
            "/10.251.214.225:50010"
        ),
        "raw_log": (
            f"260709 101504 18421 INFO {DEMO_COMPONENT}: PacketResponder 1 "
            f"for block {DEMO_BLOCK_ID} started, client /10.251.214.225:50010"
        ),
    },
    {
        "log_id": "hdfs:rca-demo-003",
        "dataset": "hdfs",
        "source_id": DEMO_SOURCE_ID,
        "source": "api-demo",
        "service": "hdfs-datanode",
        "component": DEMO_COMPONENT,
        "host": "dn-demo-01",
        "environment": "demo",
        "timestamp": "2026-07-09T10:15:21+07:00",
        "level": "WARN",
        "line_number": 3,
        "message": (
            f"Slow BlockReceiver write packet for block {DEMO_BLOCK_ID} "
            "took 28500 ms"
        ),
        "raw_log": (
            f"260709 101521 18421 WARN {DEMO_COMPONENT}: Slow BlockReceiver "
            f"write packet for block {DEMO_BLOCK_ID} took 28500 ms"
        ),
    },
    {
        "log_id": "hdfs:rca-demo-004",
        "dataset": "hdfs",
        "source_id": DEMO_SOURCE_ID,
        "source": "api-demo",
        "service": "hdfs-datanode",
        "component": DEMO_COMPONENT,
        "host": "dn-demo-01",
        "environment": "demo",
        "timestamp": "2026-07-09T10:15:34+07:00",
        "level": "WARN",
        "line_number": 4,
        "message": (
            f"PacketResponder 1 for block {DEMO_BLOCK_ID} Exception "
            "java.net.SocketTimeoutException: 30000 millis timeout while "
            "waiting for channel to be ready for read"
        ),
        "raw_log": (
            f"260709 101534 18421 WARN {DEMO_COMPONENT}: PacketResponder 1 "
            f"for block {DEMO_BLOCK_ID} Exception "
            "java.net.SocketTimeoutException: 30000 millis timeout while "
            "waiting for channel to be ready for read"
        ),
    },
    {
        "log_id": INCIDENT_LOG_ID,
        "dataset": "hdfs",
        "source_id": DEMO_SOURCE_ID,
        "source": "api-demo",
        "service": "hdfs-datanode",
        "component": DEMO_COMPONENT,
        "host": "dn-demo-01",
        "environment": "demo",
        "timestamp": "2026-07-09T10:15:39+07:00",
        "level": "ERROR",
        "line_number": 5,
        "message": (
            f"IOException while serving block {DEMO_BLOCK_ID} to "
            "/10.251.214.225: Connection reset by peer"
        ),
        "raw_log": (
            f"260709 101539 18421 ERROR {DEMO_COMPONENT}: IOException while "
            f"serving block {DEMO_BLOCK_ID} to /10.251.214.225: "
            "Connection reset by peer"
        ),
    },
    {
        "log_id": "hdfs:rca-demo-006",
        "dataset": "hdfs",
        "source_id": DEMO_SOURCE_ID,
        "source": "api-demo",
        "service": "hdfs-datanode",
        "component": DEMO_COMPONENT,
        "host": "dn-demo-01",
        "environment": "demo",
        "timestamp": "2026-07-09T10:15:42+07:00",
        "level": "INFO",
        "line_number": 6,
        "message": f"Closing replica for block {DEMO_BLOCK_ID} after client disconnect",
        "raw_log": (
            f"260709 101542 18421 INFO {DEMO_COMPONENT}: Closing replica for "
            f"block {DEMO_BLOCK_ID} after client disconnect"
        ),
    },
]


def _high_rca_log(
    *,
    sequence: int,
    time_part: str,
    iso_time: str,
    level: str,
    message: str,
    component: str = HIGH_RCA_COMPONENT,
    host: str = "dn-rca-hot-01",
) -> dict[str, Any]:
    # Kept in the scenario declaration for human-readable wall-clock alignment.
    _ = iso_time
    return {
        "log_id": f"hdfs:rca-high-{sequence:03d}",
        "dataset": "hdfs",
        "source_id": HIGH_RCA_SOURCE_ID,
        "source": "api-demo",
        "service": "hdfs-datanode",
        "component": component,
        "host": host,
        "environment": "demo",
        "timestamp": f"260709 {time_part}",
        "level": level,
        "line_number": sequence,
        "message": message,
        "raw_log": f"260709 {time_part} {19000 + sequence} {level} {component}: {message}",
    }


HIGH_RCA_DEMO_LOGS: list[dict[str, Any]] = [
    _high_rca_log(
        sequence=1,
        time_part="103000",
        iso_time="2026-07-09T10:30:00+07:00",
        level="INFO",
        message=(
            f"Receiving block {HIGH_RCA_BLOCK_ID} src: /10.251.67.225:39212 "
            "dest: /10.251.67.225:50010"
        ),
    ),
    _high_rca_log(
        sequence=2,
        time_part="103003",
        iso_time="2026-07-09T10:30:03+07:00",
        level="INFO",
        message=(
            f"Received block {HIGH_RCA_BLOCK_ID} src: /10.251.67.225:39212 "
            "dest: /10.251.67.225:50010 of size 67108864"
        ),
    ),
    _high_rca_log(
        sequence=3,
        time_part="103007",
        iso_time="2026-07-09T10:30:07+07:00",
        level="INFO",
        message=(
            f"10.251.67.225:50010 Served block {HIGH_RCA_BLOCK_ID} "
            "to /10.251.25.237"
        ),
    ),
    _high_rca_log(
        sequence=4,
        time_part="103012",
        iso_time="2026-07-09T10:30:12+07:00",
        level="INFO",
        message=(
            f"10.251.67.225:50010 Served block {HIGH_RCA_BLOCK_ID} "
            "to /10.251.25.237"
        ),
    ),
    _high_rca_log(
        sequence=5,
        time_part="103018",
        iso_time="2026-07-09T10:30:18+07:00",
        level="WARN",
        message=(
            f"Slow BlockReceiver write packet for block {HIGH_RCA_BLOCK_ID} "
            "took 31200 ms"
        ),
    ),
    _high_rca_log(
        sequence=6,
        time_part="103021",
        iso_time="2026-07-09T10:30:21+07:00",
        level="WARN",
        message=(
            f"PacketResponder 0 for block {HIGH_RCA_BLOCK_ID} Exception "
            "java.net.SocketTimeoutException: 30000 millis timeout while "
            "waiting for channel to be ready for read"
        ),
    ),
    _high_rca_log(
        sequence=7,
        time_part="103025",
        iso_time="2026-07-09T10:30:25+07:00",
        level="WARN",
        message=(
            f"PacketResponder 0 for block {HIGH_RCA_BLOCK_ID} Exception "
            "java.net.SocketTimeoutException: 30000 millis timeout while "
            "waiting for downstream ack"
        ),
    ),
    _high_rca_log(
        sequence=8,
        time_part="103029",
        iso_time="2026-07-09T10:30:29+07:00",
        level="INFO",
        message=(
            f"10.251.67.225:50010 Served block {HIGH_RCA_BLOCK_ID} "
            "to /10.251.25.237"
        ),
    ),
    _high_rca_log(
        sequence=9,
        time_part="103034",
        iso_time="2026-07-09T10:30:34+07:00",
        level="WARN",
        message=(
            f"Slow BlockReceiver write packet for block {HIGH_RCA_BLOCK_ID} "
            "took 44700 ms"
        ),
    ),
    _high_rca_log(
        sequence=10,
        time_part="103038",
        iso_time="2026-07-09T10:30:38+07:00",
        level="ERROR",
        message=(
            f"10.251.67.225:50010:Got exception while serving "
            f"{HIGH_RCA_BLOCK_ID} to /10.251.25.237:"
        ),
    ),
    _high_rca_log(
        sequence=11,
        time_part="103041",
        iso_time="2026-07-09T10:30:41+07:00",
        level="ERROR",
        message=(
            f"10.251.67.225:50010:Got exception while serving "
            f"{HIGH_RCA_BLOCK_ID} to /10.251.25.237:"
        ),
    ),
    _high_rca_log(
        sequence=12,
        time_part="103044",
        iso_time="2026-07-09T10:30:44+07:00",
        level="ERROR",
        message=(
            f"10.251.67.225:50010:Got exception while serving "
            f"{HIGH_RCA_BLOCK_ID} to /10.251.25.237:"
        ),
    ),
    _high_rca_log(
        sequence=13,
        time_part="103047",
        iso_time="2026-07-09T10:30:47+07:00",
        level="ERROR",
        message=(
            f"10.251.67.225:50010:Got exception while serving "
            f"{HIGH_RCA_BLOCK_ID} to /10.251.25.237:"
        ),
    ),
    _high_rca_log(
        sequence=14,
        time_part="103050",
        iso_time="2026-07-09T10:30:50+07:00",
        level="ERROR",
        message=(
            f"10.251.67.225:50010:Got exception while serving "
            f"{HIGH_RCA_BLOCK_ID} to /10.251.25.237:"
        ),
    ),
    _high_rca_log(
        sequence=15,
        time_part="103053",
        iso_time="2026-07-09T10:30:53+07:00",
        level="WARN",
        message=(
            f"Closing replica for block {HIGH_RCA_BLOCK_ID} because client "
            "10.251.25.237 disconnected during transfer"
        ),
    ),
    _high_rca_log(
        sequence=16,
        time_part="103058",
        iso_time="2026-07-09T10:30:58+07:00",
        level="INFO",
        message=f"PacketResponder 0 for block {HIGH_RCA_BLOCK_ID} terminating",
    ),
]

DEMO_SCENARIOS: dict[str, list[dict[str, Any]]] = {
    "basic": RCA_DEMO_LOGS,
    "high": HIGH_RCA_DEMO_LOGS,
    "all": [*RCA_DEMO_LOGS, *HIGH_RCA_DEMO_LOGS],
}
