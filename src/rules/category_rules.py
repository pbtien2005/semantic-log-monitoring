"""Dataset-aware category rules for query-bank validation.

These rules are intentionally lightweight. They are used to discover candidate
logs and review risk, not to create final relevance labels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


CATEGORIES: tuple[str, ...] = (
    "timeout",
    "connection",
    "latency",
    "database",
    "permission",
    "storage",
    "network",
    "service_unavailable",
    "unknown",
)


@dataclass(frozen=True, slots=True)
class CategoryRule:
    pattern: str
    reason: str
    weak: bool = False
    regex: bool = False


@dataclass(frozen=True, slots=True)
class RuleMatch:
    category: str
    pattern: str
    reason: str
    weak: bool


@dataclass(frozen=True, slots=True)
class ScoringProfile:
    strong_patterns: tuple[str, ...] = ()
    weak_patterns: tuple[str, ...] = ()
    negative_patterns: tuple[str, ...] = ()
    min_score_for_positive: int = 5
    min_score_for_uncertain: int = 2


@dataclass(slots=True)
class ScoredCategoryResult:
    category: str
    score: int
    matched_strong_patterns: list[str] = field(default_factory=list)
    matched_weak_patterns: list[str] = field(default_factory=list)
    matched_negative_patterns: list[str] = field(default_factory=list)
    numeric_evidence: str | None = None
    reason: str = ""

    @property
    def has_negative_evidence(self) -> bool:
        return bool(self.matched_negative_patterns)

    @property
    def weak_only(self) -> bool:
        return bool(self.matched_weak_patterns) and not self.matched_strong_patterns

    def label(self, profile: ScoringProfile) -> str:
        if self.has_negative_evidence and self.score < profile.min_score_for_positive:
            return "hard_negative"
        if self.score >= profile.min_score_for_positive:
            return "positive"
        if self.score >= profile.min_score_for_uncertain:
            return "uncertain"
        if self.has_negative_evidence:
            return "hard_negative"
        return "none"


GLOBAL_RULES: dict[str, tuple[CategoryRule, ...]] = {
    "timeout": (
        CategoryRule("timeout", "explicit timeout"),
        CategoryRule("timed out", "explicit timeout"),
        CategoryRule("request timed out", "request timeout"),
        CategoryRule("no response", "no response signal"),
        CategoryRule("not responding", "not responding signal"),
        CategoryRule("waiting", "waiting/stall signal", weak=True),
        CategoryRule("wait", "waiting/stall signal", weak=True),
        CategoryRule("stalled", "stall signal"),
    ),
    "connection": (
        CategoryRule("connection refused", "connection failure"),
        CategoryRule("connection failed", "connection failure"),
        CategoryRule("cannot connect", "connection failure"),
        CategoryRule("failed to connect", "connection failure"),
        CategoryRule("connection reset", "connection reset"),
        CategoryRule("reset by peer", "connection reset"),
        CategoryRule("broken pipe", "broken pipe"),
        CategoryRule("client closed connection", "client closed connection"),
    ),
    "latency": (
        CategoryRule("slow", "slow operation"),
        CategoryRule("latency", "latency signal"),
        CategoryRule("took", "duration signal"),
        CategoryRule("delayed", "delay signal"),
        CategoryRule("long time", "long duration"),
        CategoryRule("high response time", "high response time"),
    ),
    "database": (
        CategoryRule("database", "database state"),
        CategoryRule(r"\bdb\b", "database abbreviation", weak=True, regex=True),
        CategoryRule("query", "query/database signal", weak=True),
        CategoryRule("sql", "SQL signal"),
        CategoryRule("connection pool", "connection pool"),
        CategoryRule("deadlock", "deadlock"),
    ),
    "permission": (
        CategoryRule("permission denied", "permission denied"),
        CategoryRule("client denied", "client denied"),
        CategoryRule("access denied", "access denied"),
        CategoryRule("forbidden", "forbidden access"),
        CategoryRule("unauthorized", "unauthorized"),
        CategoryRule("authentication failed", "authentication failure"),
    ),
    "storage": (
        CategoryRule("block", "block/storage signal", weak=True),
        CategoryRule("replica", "replica signal"),
        CategoryRule("datanode", "DataNode signal"),
        CategoryRule("namenode", "NameNode signal"),
        CategoryRule("disk", "disk signal"),
        CategoryRule("file", "file/storage signal", weak=True),
        CategoryRule("pipeline", "pipeline signal"),
        CategoryRule("replication", "replication signal"),
    ),
    "network": (
        CategoryRule("network", "network signal"),
        CategoryRule("socket", "socket signal"),
        CategoryRule("unreachable", "unreachable host/network"),
        CategoryRule("host down", "host down"),
        CategoryRule("route", "routing signal", weak=True),
        CategoryRule("packet", "packet signal", weak=True),
    ),
    "service_unavailable": (
        CategoryRule("unavailable", "service unavailable"),
        CategoryRule("failed to start", "startup failure"),
        CategoryRule("stopped", "service stopped"),
        CategoryRule("crashed", "crash signal"),
        CategoryRule("down", "down signal"),
        CategoryRule("not available", "not available signal"),
    ),
    "unknown": (
        CategoryRule("exception", "exception signal"),
        CategoryRule("traceback", "traceback signal"),
        CategoryRule("critical", "critical signal"),
        CategoryRule("alert", "alert signal"),
        CategoryRule(r"\berror\b", "error-level text", regex=True),
        CategoryRule(r"\bwarn(?:ing)?\b", "warning-level text", regex=True),
    ),
}


DATASET_RULES: dict[str, dict[str, tuple[CategoryRule, ...]]] = {
    "apache": {
        "permission": (
            CategoryRule("directory index forbidden", "directory access forbidden"),
            CategoryRule("client denied", "Apache client denied"),
            CategoryRule("permission denied", "Apache permission denied"),
        ),
        "service_unavailable": (
            CategoryRule("error state", "Apache worker in error state"),
            CategoryRule("mod_jk", "Apache mod_jk worker connector"),
            CategoryRule("file does not exist", "missing file"),
            CategoryRule("not found", "missing resource", weak=True),
            CategoryRule("unable to serve", "unable to serve resource"),
            CategoryRule("failed to open", "failed to open resource"),
            CategoryRule("script not found", "missing script"),
        ),
        "connection": (
            CategoryRule("connection reset", "connection reset"),
            CategoryRule("broken pipe", "broken pipe"),
            CategoryRule("client closed connection", "client closed connection"),
            CategoryRule("socket", "socket signal"),
        ),
        "network": (
            CategoryRule("connection reset", "connection reset"),
            CategoryRule("broken pipe", "broken pipe"),
            CategoryRule("socket", "socket signal"),
        ),
    },
    "openstack": {
        "connection": (
            CategoryRule("rpc timeout", "RPC timeout"),
            CategoryRule("messaging timeout", "messaging timeout"),
            CategoryRule("failed to connect", "backend connection failure"),
            CategoryRule("connection refused", "connection refused"),
        ),
        "timeout": (
            CategoryRule("timeout", "OpenStack timeout"),
            CategoryRule("timed out", "OpenStack timeout"),
            CategoryRule("waiting", "waiting/stall signal", weak=True),
        ),
        "service_unavailable": (
            CategoryRule("service down", "service down"),
            CategoryRule("unavailable", "service unavailable"),
            CategoryRule("failed to start", "service start failure"),
            CategoryRule("no valid host", "scheduler capacity failure"),
            CategoryRule("instance failed", "instance failure"),
        ),
        "latency": (
            CategoryRule("took", "operation duration"),
            CategoryRule("scheduling delay", "scheduler delay"),
        ),
        "permission": (
            CategoryRule("policy", "policy authorization signal", weak=True),
            CategoryRule("token", "token/auth signal", weak=True),
            CategoryRule("authentication", "authentication signal"),
            CategoryRule("unauthorized", "unauthorized"),
            CategoryRule("forbidden", "forbidden"),
        ),
        "network": (
            CategoryRule("neutron", "Neutron network signal"),
            CategoryRule("network-vif", "VIF network event"),
            CategoryRule("vif", "VIF signal"),
            CategoryRule("binding", "port binding signal"),
            CategoryRule("port", "port/network signal", weak=True),
            CategoryRule(r"\bip\b", "IP/network signal", weak=True, regex=True),
        ),
        "storage": (
            CategoryRule("imagecache", "Nova image cache"),
            CategoryRule("image cache", "Nova image cache"),
            CategoryRule("base file", "Nova base file"),
            CategoryRule("_base", "Nova base image path", weak=True),
        ),
        "database": (
            CategoryRule("database", "database/hypervisor state comparison"),
            CategoryRule("hypervisor", "hypervisor state comparison", weak=True),
        ),
        "unknown": (),
    },
    "hdfs": {
        "storage": (
            CategoryRule("blk_", "HDFS block id"),
            CategoryRule("blockmap", "HDFS blockMap"),
            CategoryRule("addstoredblock", "stored block update"),
            CategoryRule("packetresponder", "PacketResponder block handling"),
            CategoryRule("fsdataset", "FSDataset storage operation"),
            CategoryRule("block scanner", "block scanner"),
        ),
        "connection": (
            CategoryRule("socket", "socket signal"),
            CategoryRule("connection", "connection signal"),
            CategoryRule("host", "host signal", weak=True),
            CategoryRule("broken pipe", "broken pipe"),
        ),
        "network": (
            CategoryRule("socket", "socket signal"),
            CategoryRule("host", "host signal", weak=True),
            CategoryRule("packet", "packet signal", weak=True),
            CategoryRule(r"\d+\.\d+\.\d+\.\d+:\d+", "HDFS host:port endpoint", weak=True, regex=True),
        ),
        "service_unavailable": (
            CategoryRule("exception while serving", "DataNode serving exception"),
            CategoryRule("got exception while serving", "DataNode serving exception"),
            CategoryRule("datanode dead", "dead DataNode"),
            CategoryRule("node down", "node down"),
            CategoryRule("failed", "failure signal"),
            CategoryRule("exception", "exception signal"),
        ),
        "unknown": (
            CategoryRule("exception", "exception signal"),
            CategoryRule("warn", "warning text"),
            CategoryRule("error", "error text"),
        ),
    },
}


NORMAL_LIFECYCLE_PATTERNS = (
    "vm stopped",
    "vm started",
    "vm paused",
    "vm resumed",
    "lifecycle event",
    "completed successfully",
    "created successfully",
    "successfully",
    "deallocate network",
    "destroy instance",
)


SCORING_PROFILES: dict[str, ScoringProfile] = {
    "timeout": ScoringProfile(
        strong_patterns=("timeout", "timed out", "request timed out", "no response", "not responding", "stalled"),
        weak_patterns=("waiting", "wait"),
        negative_patterns=NORMAL_LIFECYCLE_PATTERNS,
    ),
    "connection": ScoringProfile(
        strong_patterns=("connection refused", "connection failed", "cannot connect", "failed to connect", "connection reset", "reset by peer", "broken pipe", "socket error", "unreachable"),
        weak_patterns=("connection", "socket"),
        negative_patterns=("connection established", "connected successfully", "successful connection"),
    ),
    "latency": ScoringProfile(
        strong_patterns=("slow", "high latency", "delayed", "scheduling delay"),
        weak_patterns=("took", "seconds", "duration"),
        negative_patterns=NORMAL_LIFECYCLE_PATTERNS,
        min_score_for_positive=6,
        min_score_for_uncertain=2,
    ),
    "database": ScoringProfile(
        strong_patterns=("database", "sql", "connection pool", "deadlock"),
        weak_patterns=("db", "query", "hypervisor"),
        negative_patterns=NORMAL_LIFECYCLE_PATTERNS,
    ),
    "permission": ScoringProfile(
        strong_patterns=("permission denied", "client denied", "access denied", "forbidden", "unauthorized", "authentication failed"),
        weak_patterns=("auth", "policy", "token"),
        negative_patterns=("access granted", "authorized", "authenticated successfully"),
        min_score_for_positive=4,
    ),
    "storage": ScoringProfile(
        strong_patterns=("replica", "datanode", "namenode", "disk", "pipeline", "replication", "imagecache", "image cache", "base file", "blockmap", "addstoredblock", "packetresponder", "fsdataset"),
        weak_patterns=("block", "blk_", "file", "_base"),
        negative_patterns=("verification succeeded", "completed successfully"),
        min_score_for_positive=5,
        min_score_for_uncertain=2,
    ),
    "network": ScoringProfile(
        strong_patterns=("network-vif", "neutron", "connection reset", "broken pipe", "socket error", "unreachable", "host down", "binding failed"),
        weak_patterns=("network", "socket", "host", "route", "packet", "port", "vif", "ip"),
        negative_patterns=("network allocated", "connection established", "plugged", "successful"),
    ),
    "service_unavailable": ScoringProfile(
        strong_patterns=("unavailable", "failed to start", "crashed", "not available", "no valid host", "instance failed", "exception while serving", "got exception while serving", "datanode dead", "node down", "error state", "file does not exist", "unable to serve", "failed to open", "script not found", "cannot serve", "refused"),
        weak_patterns=("down", "stopped", "closed", "exception", "failed", "not found"),
        negative_patterns=NORMAL_LIFECYCLE_PATTERNS + ("closed normally", "stopped by request"),
        min_score_for_positive=4,
        min_score_for_uncertain=2,
    ),
    "unknown": ScoringProfile(
        strong_patterns=("traceback", "critical", "alert", "corrupt", "fatal"),
        weak_patterns=("error", "warn", "warning", "exception"),
        negative_patterns=("verification succeeded", "completed successfully", "lifecycle event"),
        min_score_for_positive=6,
        min_score_for_uncertain=2,
    ),
}


def log_text(log: dict[str, Any]) -> str:
    parts = (
        log.get("raw_log"),
        log.get("message"),
        log.get("component"),
        log.get("level"),
        log.get("event_id"),
    )
    return " ".join(str(part) for part in parts if part is not None).lower()


def rules_for(dataset: str, category: str) -> tuple[CategoryRule, ...]:
    return (
        GLOBAL_RULES.get(category, ())
        + DATASET_RULES.get(dataset, {}).get(category, ())
    )


def rule_matches(text: str, rule: CategoryRule) -> bool:
    if rule.regex:
        return re.search(rule.pattern, text, re.IGNORECASE) is not None
    return rule.pattern.lower() in text


def match_log(dataset: str, category: str, log: dict[str, Any]) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    if category == "unknown" and log.get("level") in {"ERROR", "WARN", "WARNING"}:
        matches.append(
            RuleMatch(
                category=category,
                pattern=f"level={log.get('level')}",
                reason="abnormal log level fallback",
                weak=False,
            )
        )

    text = log_text(log)
    for rule in rules_for(dataset, category):
        if rule_matches(text, rule):
            matches.append(
                RuleMatch(
                    category=category,
                    pattern=rule.pattern,
                    reason=rule.reason,
                    weak=rule.weak,
                )
            )
    return matches


def scoring_profile(category: str) -> ScoringProfile:
    return SCORING_PROFILES[category]


def _contains(text: str, pattern: str) -> bool:
    if pattern == "slow":
        return re.search(r"\bslow\b", text, re.IGNORECASE) is not None
    return pattern.lower() in text


def extract_took_seconds(text: str) -> float | None:
    match = re.search(r"\btook\s+([0-9]+(?:\.[0-9]+)?)\s+seconds?\b", text, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1))


def _base_score(category: str, text: str) -> ScoredCategoryResult:
    profile = scoring_profile(category)
    result = ScoredCategoryResult(category=category, score=0)

    for pattern in profile.strong_patterns:
        if _contains(text, pattern):
            result.matched_strong_patterns.append(pattern)
            result.score += 4
    for pattern in profile.weak_patterns:
        if _contains(text, pattern):
            result.matched_weak_patterns.append(pattern)
            result.score += 1
    for pattern in profile.negative_patterns:
        if _contains(text, pattern):
            result.matched_negative_patterns.append(pattern)
            result.score -= 5
    return result


def _apply_latency_numeric(result: ScoredCategoryResult, text: str) -> None:
    seconds = extract_took_seconds(text)
    if seconds is None:
        return
    if seconds >= 10:
        result.score += 7
        result.matched_strong_patterns.append("took>=10s")
        result.numeric_evidence = f"latency duration {seconds:.2f}s >= 10s"
    elif seconds >= 5:
        result.score += 2
        result.numeric_evidence = f"latency duration {seconds:.2f}s between 5s and 10s"
    else:
        result.score -= 6
        result.matched_negative_patterns.append("took<5s")
        result.numeric_evidence = f"duration {seconds:.2f}s below latency threshold"


def _apply_storage_context(dataset: str, result: ScoredCategoryResult, text: str) -> None:
    if dataset != "hdfs":
        return
    has_block = "blk_" in text or "block" in text
    has_issue = any(
        marker in text
        for marker in (
            "exception",
            "failed",
            "missing",
            "corrupt",
            "pipeline error",
            "replica",
            "datanode dead",
        )
    )
    if has_block and has_issue:
        result.score += 5
        if "block+issue" not in result.matched_strong_patterns:
            result.matched_strong_patterns.append("block+issue")
    elif has_block and not has_issue:
        result.score = min(result.score, 3)
        if "block-only" not in result.matched_weak_patterns:
            result.matched_weak_patterns.append("block-only")
        result.numeric_evidence = "HDFS block-only signal without failure context"


def _apply_service_context(result: ScoredCategoryResult, text: str) -> None:
    if any(pattern in text for pattern in NORMAL_LIFECYCLE_PATTERNS):
        if not any(
            marker in text
            for marker in (
                "failed",
                "unavailable",
                "crashed",
                "exception",
                "no valid host",
                "error state",
                "refused",
                "cannot serve",
            )
        ):
            result.score -= 6
            if "normal lifecycle event" not in result.matched_negative_patterns:
                result.matched_negative_patterns.append("normal lifecycle event")


def _apply_category_adjustments(
    dataset: str,
    category: str,
    log: dict[str, Any],
    text: str,
    result: ScoredCategoryResult,
) -> None:
    if category == "latency":
        _apply_latency_numeric(result, text)
    elif category == "storage":
        _apply_storage_context(dataset, result, text)
    elif category == "service_unavailable":
        _apply_service_context(result, text)
    elif category == "unknown" and log.get("level") in {"ERROR", "WARN", "WARNING"}:
        result.score += 2
        result.matched_weak_patterns.append(f"level={log.get('level')}")


def _positive_reason(category: str, result: ScoredCategoryResult) -> str:
    if result.numeric_evidence and category == "latency":
        return f"positive: {result.numeric_evidence}"
    if category == "storage" and "block+issue" in result.matched_strong_patterns:
        return "positive: storage pattern block + exception/failure context"
    patterns = result.matched_strong_patterns or result.matched_weak_patterns
    return "positive: matched strong pattern " + ", ".join(patterns[:3])


def _uncertain_reason(result: ScoredCategoryResult) -> str:
    if result.numeric_evidence:
        return f"uncertain: {result.numeric_evidence}"
    if result.weak_only:
        return "uncertain: weak pattern only"
    return "uncertain: below positive threshold"


def _score_reason(category: str, result: ScoredCategoryResult) -> str:
    profile = scoring_profile(category)
    if result.matched_negative_patterns and result.score < profile.min_score_for_positive:
        return "hard_negative: " + ", ".join(result.matched_negative_patterns[:3])
    label = result.label(profile)
    if label == "positive":
        return _positive_reason(category, result)
    if label == "uncertain":
        return _uncertain_reason(result)
    if category == "latency" and result.numeric_evidence:
        return f"hard_negative: {result.numeric_evidence}"
    return "no category evidence above threshold"


def score_log(dataset: str, category: str, log: dict[str, Any]) -> ScoredCategoryResult:
    text = log_text(log)
    result = _base_score(category, text)
    _apply_category_adjustments(dataset, category, log, text, result)
    result.reason = _score_reason(category, result)
    return result
