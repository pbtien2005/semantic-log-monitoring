"""Rule-based hard entity extraction for retrieval planning."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field

from src.retrieval.query_normalizer import NormalizedQuery, normalize_query


REQUEST_ID_RE = re.compile(r"\breq-[0-9a-f-]{8,}\b", re.IGNORECASE)
BLOCK_ID_RE = re.compile(r"\bblk_-?\d+\b", re.IGNORECASE)
IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
INSTANCE_UUID_RE = re.compile(
    r"\b(?:instance|vm|server|may ao|may chu)\s*(?:id|uuid)?\s*[:=]?\s*"
    r"(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b",
    re.IGNORECASE,
)
HTTP_STATUS_RE = re.compile(
    r"\b(?:http\s+status|status\s+code|response\s+code|status|http|ma loi|error\s+code|code)"
    r"\s*[:=]?\s*(?P<status>[1-5]\d{2})\b",
    re.IGNORECASE,
)
PATH_RE = re.compile(r"(?<!\w)/(?:[A-Za-z0-9._@%+=:,~-]+/)*[A-Za-z0-9._@%+=:,~-]+")

@dataclass(slots=True)
class QueryEntityExtraction:
    hard_filters: dict[str, str | int | float] = field(default_factory=dict)


def _extract_hard_ids(query: NormalizedQuery, extraction: QueryEntityExtraction) -> None:
    if match := REQUEST_ID_RE.search(query.clean_text):
        extraction.hard_filters["request_id"] = match.group(0)

    if match := BLOCK_ID_RE.search(query.clean_text):
        extraction.hard_filters["block_id"] = match.group(0)


def _extract_uuid(query: NormalizedQuery, extraction: QueryEntityExtraction) -> None:
    for match in INSTANCE_UUID_RE.finditer(query.accentless_text):
        value = match.group("uuid")
        extraction.hard_filters["instance_id"] = value


def _extract_ip(query: NormalizedQuery, extraction: QueryEntityExtraction) -> None:
    for match in IP_RE.finditer(query.clean_text):
        value = match.group(0)
        try:
            ipaddress.ip_address(value)
        except ValueError:
            continue
        extraction.hard_filters["ip"] = value
        return


def _extract_context_values(query: NormalizedQuery, extraction: QueryEntityExtraction) -> None:
    if match := HTTP_STATUS_RE.search(query.accentless_text):
        extraction.hard_filters["http_status"] = int(match.group("status"))

    if match := PATH_RE.search(query.clean_text):
        extraction.hard_filters["path"] = match.group(0)


def extract_query_entities(query: str | NormalizedQuery) -> QueryEntityExtraction:
    normalized = normalize_query(query) if isinstance(query, str) else query
    extraction = QueryEntityExtraction()
    _extract_hard_ids(normalized, extraction)
    _extract_uuid(normalized, extraction)
    _extract_ip(normalized, extraction)
    _extract_context_values(normalized, extraction)
    return extraction
