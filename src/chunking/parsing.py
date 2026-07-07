"""Parsing and normalization helpers for log chunking."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


UUID_PATTERN = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
REQ_ID_RE = re.compile(rf"\breq-{UUID_PATTERN}\b")
INSTANCE_RE = re.compile(rf"\[instance:\s*(?P<instance_id>{UUID_PATTERN})\]", re.IGNORECASE)
INSTANCE_WORD_RE = re.compile(rf"\binstance\s+(?P<instance_id>{UUID_PATTERN})\b", re.IGNORECASE)
UUID_RE = re.compile(rf"\b{UUID_PATTERN}\b")
HEX_ID_RE = re.compile(r"\b[0-9a-fA-F]{32}\b")
BLOCK_ID_RE = re.compile(r"\bblk_-?\d+\b")
IP_PORT_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d+\b")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
HTTP_RE = re.compile(
    r'"(?P<method>[A-Z]+)\s+(?P<route>\S+)\s+HTTP/(?P<version>[^"]+)"'
)
HTTP_STATUS_RE = re.compile(r"\bstatus:\s*(?P<status>\d{3})\b", re.IGNORECASE)
RESPONSE_LEN_RE = re.compile(r"\blen:\s*(?P<length>\d+)\b", re.IGNORECASE)
TIME_SECONDS_RE = re.compile(r"\btime:\s*(?P<seconds>\d+(?:\.\d+)?)\b", re.IGNORECASE)
TOOK_SECONDS_RE = re.compile(r"\btook\s+(?P<seconds>\d+(?:\.\d+)?)\s+seconds?\b", re.IGNORECASE)
ERROR_STATE_RE = re.compile(r"\berror state\s+(?P<code>-?\d+)\b", re.IGNORECASE)
ERROR_CODE_RE = re.compile(r"\berror code\s+(?P<code>-?\d+)\b", re.IGNORECASE)
EXIT_CODE_RE = re.compile(r"\bexit code\s+(?P<code>-?\d+)\b", re.IGNORECASE)
RETRY_COUNT_RE = re.compile(r"\bretry\s+(?P<count>\d+)\b", re.IGNORECASE)
PORT_RE = re.compile(r"\bport\s+(?P<port>\d{2,5})\b", re.IGNORECASE)
SOURCE_LOG_RE = re.compile(r"^(?P<source_log>\S+\.log(?:\.\S+)?)\s+\d{4}-\d{2}-\d{2}\s+")
PATH_RE = re.compile(r"(?<!\w)/(?:[A-Za-z0-9._@%+=:,~-]+/)*[A-Za-z0-9._@%+=:,~-]+")
NUMBER_RE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
WHITESPACE_RE = re.compile(r"\s+")
BLOCK_ID_LIST_RE = re.compile(r"(?:<block_id>\s+){2,}<block_id>")


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def first(values: list[Any]) -> Any | None:
    return values[0] if values else None


def normalize_space(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def parse_timestamp_ms(timestamp: str | None, dataset: str) -> int | None:
    if not timestamp:
        return None

    formats = {
        "openstack": ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"),
        "apache": ("%a %b %d %H:%M:%S %Y",),
        "hdfs": ("%y%m%d %H%M%S",),
    }
    for fmt in formats.get(dataset, ()):
        try:
            parsed = datetime.strptime(timestamp, fmt).replace(tzinfo=timezone.utc)
            return int(parsed.timestamp() * 1000)
        except ValueError:
            continue
    return None


def parse_int(pattern: re.Pattern[str], text: str, group: str) -> int | None:
    match = pattern.search(text)
    if not match:
        return None
    return int(match.group(group))


def parse_duration_ms(text: str) -> float | None:
    for pattern in (TIME_SECONDS_RE, TOOK_SECONDS_RE):
        match = pattern.search(text)
        if match:
            return float(match.group("seconds")) * 1000
    return None


def parse_source_log(raw_log: str) -> str | None:
    match = SOURCE_LOG_RE.search(raw_log)
    return match.group("source_log") if match else None


def normalize_api_route(route: str) -> str:
    route = UUID_RE.sub("<uuid>", route)
    route = HEX_ID_RE.sub("<hex_id>", route)
    return route


def normalize_api_route_for_template(route: str) -> str:
    route = normalize_api_route(route).strip("/")
    return route.replace("/", " ") or "<api_route>"


def normalize_http_request(match: re.Match[str]) -> str:
    method = match.group("method")
    route = normalize_api_route_for_template(match.group("route"))
    return f'"{method} route:{route} HTTP/<version>"'


def bucket_http_status(match: re.Match[str]) -> str:
    status = int(match.group("status"))
    return f"status: <status_{status // 100}xx>"


def bucket_time_duration(match: re.Match[str]) -> str:
    seconds = float(match.group("seconds"))
    bucket = "duration_slow" if seconds >= 5 else "duration_normal"
    return f"time: <{bucket}>"


def bucket_took_duration(match: re.Match[str]) -> str:
    seconds = float(match.group("seconds"))
    bucket = "duration_slow" if seconds >= 5 else "duration_normal"
    return f"took <{bucket}> seconds"


def parse_http(text: str) -> dict[str, Any]:
    match = HTTP_RE.search(text)
    if not match:
        return {"http_method": None, "api_route": None, "http_version": None}
    return {
        "http_method": match.group("method"),
        "api_route": normalize_api_route(match.group("route")),
        "http_version": match.group("version"),
    }


def extract_entities(log: dict[str, Any]) -> dict[str, list[str]]:
    raw_log = str(log.get("raw_log") or "")
    message = str(log.get("message") or "")
    text = f"{raw_log} {message}"
    instance_ids = [match.group("instance_id") for match in INSTANCE_RE.finditer(text)]
    instance_ids.extend(match.group("instance_id") for match in INSTANCE_WORD_RE.finditer(text))
    request_ids = REQ_ID_RE.findall(text)
    block_ids = BLOCK_ID_RE.findall(text)
    ip_ports = IP_PORT_RE.findall(text)
    ips = IP_RE.findall(text)
    paths = PATH_RE.findall(text)
    uuids = [
        value
        for value in UUID_RE.findall(text)
        if value not in instance_ids and f"req-{value}" not in request_ids
    ]
    hex_ids = HEX_ID_RE.findall(text)

    return {
        "request_id": unique(request_ids),
        "instance_id": unique(instance_ids),
        "uuid": unique(uuids),
        "hex_id": unique(hex_ids),
        "block_id": unique(block_ids),
        "ip_port": unique(ip_ports),
        "ip": unique(ips),
        "path": unique(paths),
    }


def normalize_template(text: str) -> str:
    template = text
    template = HTTP_RE.sub(normalize_http_request, template)
    template = REQ_ID_RE.sub("<req_id>", template)
    template = INSTANCE_RE.sub("[instance: <instance_id>]", template)
    template = INSTANCE_WORD_RE.sub("instance <instance_id>", template)
    template = BLOCK_ID_RE.sub("<block_id>", template)
    template = IP_PORT_RE.sub("<ip_port>", template)
    template = IP_RE.sub("<ip>", template)
    template = UUID_RE.sub("<uuid>", template)
    template = HEX_ID_RE.sub("<hex_id>", template)
    template = PATH_RE.sub("<path>", template)
    template = HTTP_STATUS_RE.sub(bucket_http_status, template)
    template = RESPONSE_LEN_RE.sub("len: <len>", template)
    template = TIME_SECONDS_RE.sub(bucket_time_duration, template)
    template = TOOK_SECONDS_RE.sub(bucket_took_duration, template)
    template = ERROR_STATE_RE.sub("error state <state_code>", template)
    template = ERROR_CODE_RE.sub("error code <error_code>", template)
    template = EXIT_CODE_RE.sub("exit code <exit_code>", template)
    template = RETRY_COUNT_RE.sub("retry <retry_count>", template)
    template = PORT_RE.sub("port <port>", template)
    template = NUMBER_RE.sub("<num>", template)
    template = BLOCK_ID_LIST_RE.sub("<block_id_list>", template)
    return normalize_space(template)


def sanitize_message_for_embedding(text: str, *, max_length: int = 240) -> str:
    message = HTTP_RE.sub(normalize_http_request, text)
    message = REQ_ID_RE.sub("<req_id>", message)
    message = INSTANCE_RE.sub("[instance: <instance_id>]", message)
    message = INSTANCE_WORD_RE.sub("instance <instance_id>", message)
    message = BLOCK_ID_RE.sub("<block_id>", message)
    message = IP_PORT_RE.sub("<ip_port>", message)
    message = IP_RE.sub("<ip>", message)
    message = UUID_RE.sub("<uuid>", message)
    message = HEX_ID_RE.sub("<hex_id>", message)
    message = PATH_RE.sub("<path>", message)
    message = normalize_space(message)
    if len(message) <= max_length:
        return message
    return message[: max_length - 3].rstrip() + "..."


def infer_task_state(message: str) -> str | None:
    match = re.search(r"pending task \((?P<state>[^)]+)\)", message, re.IGNORECASE)
    return match.group("state") if match else None


def infer_apache_module(message: str) -> str | None:
    match = re.search(r"\b(?P<module>mod_[A-Za-z0-9_]+)\b", message)
    if match:
        return match.group("module")
    if "workerEnv" in message:
        return "workerEnv"
    return None
