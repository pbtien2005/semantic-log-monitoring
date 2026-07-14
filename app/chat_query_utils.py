"""Parse chat intent, filters, identifiers, and time windows."""

from __future__ import annotations

import re
from typing import Any, Sequence

from src.rca.ranking import DEFAULT_LOOKBACK_MS
from src.retrieval.query_normalizer import normalize_query


RECENT_TERMS = ("moi nhat", "gan day", "vua xay ra", "latest", "recent", "newest", "last logs")
RCA_TERMS = (
    "rca",
    "root cause",
    "log_id=",
    "anomaly log",
    "incident log",
    "nguyen nhan",
    "giai thich nguyen nhan",
)
EXPLICIT_LOG_ID_RE = re.compile(r"\blog_id\s*=\s*(?P<log_id>[^\s,;]+)", re.IGNORECASE)
BARE_LOG_ID_RE = re.compile(r"\b(?P<log_id>[a-zA-Z][\w-]*:[\w.-]+)\b")
QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "cac",
    "den",
    "error",
    "errors",
    "find",
    "hoac",
    "lien",
    "log",
    "logs",
    "loi",
    "quan",
    "related",
    "the",
    "tim",
    "to",
    "warn",
    "warning",
    "info",
    "notice",
}
LEVEL_NAMES = {"ERROR", "WARN", "WARNING", "INFO", "NOTICE", "DEBUG"}


def extract_log_id(query: str) -> str | None:
    explicit = EXPLICIT_LOG_ID_RE.search(query)
    if explicit:
        return explicit.group("log_id").strip()
    bare = BARE_LOG_ID_RE.search(query)
    return bare.group("log_id").strip() if bare else None


def is_recent_log_query(query: str) -> bool:
    normalized = normalize_query_text(query)
    return any(term in normalized for term in RECENT_TERMS)


def is_rca_query(
    query: str,
    *,
    mode: str | None = None,
    incident_log: dict[str, Any] | None = None,
) -> bool:
    if mode and mode.lower() == "rca":
        return True
    if incident_log:
        return True
    normalized = normalize_query_text(query)
    if any(term in normalized for term in RCA_TERMS):
        return True
    return bool(extract_log_id(query)) and any(
        term in normalized for term in ("loi", "error", "incident")
    )


def normalize_query_text(query: str) -> str:
    return normalize_query(query).accentless_text


def extract_recent_window_hours(query: str, default: int = 1) -> int:
    match = re.search(
        r"\b(\d{1,3})\s*(?:h|gio|tieng|hour|hours)\b",
        normalize_query_text(query),
    )
    return max(1, int(match.group(1))) if match else default


def extract_rca_lookback_ms(query: str, default: int = DEFAULT_LOOKBACK_MS) -> int:
    normalized = normalize_query_text(query)
    minute_match = re.search(r"\b(\d{1,4})\s*(?:m|min|mins|minute|minutes|phut|p)\b", normalized)
    if minute_match:
        return max(1, int(minute_match.group(1))) * 60 * 1000
    hour_match = re.search(r"\b(\d{1,3})\s*(?:h|hour|hours|gio|tieng)\b", normalized)
    if hour_match:
        return max(1, int(hour_match.group(1))) * 60 * 60 * 1000
    return default


def extract_query_level(query: str) -> str | None:
    upper = query.upper()
    for level_name in LEVEL_NAMES:
        if re.search(rf"\b{re.escape(level_name)}\b", upper):
            return "WARN" if level_name == "WARNING" else level_name
    return None


def extract_query_terms(query: str) -> list[str]:
    normalized = normalize_query_text(query)
    terms: list[str] = []
    for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_.$-]*", normalized):
        lowered = token.lower()
        if len(lowered) < 3 or lowered in QUERY_STOPWORDS:
            continue
        if lowered not in terms:
            terms.append(lowered)
    return terms


def normalize_filter(value: str | None) -> str | None:
    if not value or value in {"all", "Tất cả"}:
        return None
    return value


def single_level(levels: Sequence[str] | None) -> str | None:
    clean_levels = [level_name for level_name in levels or [] if level_name and level_name != "UNKNOWN"]
    return clean_levels[0] if len(clean_levels) == 1 else None
