"""Regex-backed fixed template catalog matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.io_utils import read_jsonl
from src.core.schema import validate_dataset
from src.chunking.parsing import normalize_template


DEFAULT_TEMPLATE_DIR = Path("data") / "templates"


@dataclass(frozen=True, slots=True)
class TemplateRule:
    template_id: str
    dataset: str
    template: str
    regex: re.Pattern[str]
    priority: int = 0
    active: bool = True
    component: str | None = None
    level: str | None = None
    raw_regex: str = ""


@dataclass(frozen=True, slots=True)
class TemplateMatch:
    matched: bool
    template_id: str | None
    template: str
    match_method: str
    confidence: float
    slots: dict[str, str]
    component: str | None = None
    level: str | None = None
    candidate_count: int = 0


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def rule_from_record(record: dict[str, Any]) -> TemplateRule:
    template_id = record.get("template_id")
    template = record.get("template")
    regex = record.get("regex")
    if not template_id:
        raise ValueError(f"Template catalog record is missing template_id: {record}")
    if not template:
        raise ValueError(f"Template catalog record is missing template: {record}")
    if not regex:
        raise ValueError(f"Template catalog record is missing regex: {record}")

    return TemplateRule(
        template_id=str(template_id),
        dataset=validate_dataset(str(record["dataset"])),
        template=str(template),
        regex=re.compile(str(regex), re.IGNORECASE),
        raw_regex=str(regex),
        priority=int(record.get("priority") or 0),
        active=bool(record.get("active", True)),
        component=_optional_str(record.get("component")),
        level=_optional_str(record.get("level")),
    )


class TemplateMatcher:
    """Matches parsed log messages against a fixed regex template catalog."""

    def __init__(self, rules: list[TemplateRule]) -> None:
        active_rules = [rule for rule in rules if rule.active]
        self.rules_by_dataset: dict[str, list[TemplateRule]] = {}
        for rule in active_rules:
            self.rules_by_dataset.setdefault(rule.dataset, []).append(rule)
        for dataset, dataset_rules in self.rules_by_dataset.items():
            self.rules_by_dataset[dataset] = sorted(
                dataset_rules,
                key=lambda rule: (-rule.priority, rule.template_id),
            )

    @classmethod
    def from_records(cls, records: list[dict[str, Any]]) -> "TemplateMatcher":
        return cls([rule_from_record(record) for record in records])

    @classmethod
    def load(cls, root: Path, dataset: str, template_dir: Path = DEFAULT_TEMPLATE_DIR) -> "TemplateMatcher":
        dataset = validate_dataset(dataset)
        base = root / template_dir if not template_dir.is_absolute() else template_dir
        path = base / f"{dataset}_templates.jsonl"
        return cls.from_records(list(read_jsonl(path)))

    def match(
        self,
        *,
        dataset: str,
        message: str,
        component: str | None = None,
        level: str | None = None,
    ) -> TemplateMatch:
        dataset = validate_dataset(dataset)
        candidates: list[tuple[TemplateRule, dict[str, str], str, float]] = []
        for rule in self.rules_by_dataset.get(dataset, []):
            if rule.component is not None and rule.component != component:
                continue
            if rule.level is not None and rule.level != level:
                continue
            match = rule.regex.search(message)
            if match:
                candidates.append(
                    (
                        rule,
                        {key: value for key, value in match.groupdict().items() if value is not None},
                        "regex",
                        1.0,
                    )
                )

        if candidates:
            rule, slots, match_method, confidence = candidates[0]
            return TemplateMatch(
                matched=True,
                template_id=rule.template_id,
                template=rule.template,
                match_method=match_method,
                confidence=confidence,
                slots=slots,
                component=rule.component,
                level=rule.level,
                candidate_count=len(candidates),
            )

        normalized_message = normalize_template(message)
        normalized_candidates = [
            rule
            for rule in self.rules_by_dataset.get(dataset, [])
            if (rule.component is None or rule.component == component)
            and (rule.level is None or rule.level == level)
            and rule.template == normalized_message
        ]
        if normalized_candidates:
            rule = normalized_candidates[0]
            return TemplateMatch(
                matched=True,
                template_id=rule.template_id,
                template=rule.template,
                match_method="normalized_template",
                confidence=0.9,
                slots={},
                component=rule.component,
                level=rule.level,
                candidate_count=len(normalized_candidates),
            )

        return TemplateMatch(
            matched=False,
            template_id=None,
            template=normalized_message,
            match_method="fallback_normalize",
            confidence=0.0,
            slots={},
            component=component,
            level=level,
            candidate_count=0,
        )


PLACEHOLDER_PATTERNS: dict[str, str] = {
    "*": r".*?",
    "req_id": r"req-[0-9a-fA-F-]{36}",
    "instance_id": r"[0-9a-fA-F-]{36}",
    "uuid": r"[0-9a-fA-F-]{36}",
    "hex_id": r"[0-9a-fA-F]{32}",
    "block_id": r"blk_-?\d+",
    "block_id_list": r"blk_-?\d+(?:\s+blk_-?\d+)+",
    "ip_port": r"(?:\d{1,3}\.){3}\d{1,3}:\d+",
    "ip": r"(?:\d{1,3}\.){3}\d{1,3}",
    "path": r"/\S+",
    "status_2xx": r"2\d\d",
    "status_3xx": r"3\d\d",
    "status_4xx": r"4\d\d",
    "status_5xx": r"5\d\d",
    "len": r"\d+",
    "duration_normal": r"\d+(?:\.\d+)?",
    "duration_slow": r"\d+(?:\.\d+)?",
    "state_code": r"-?\d+",
    "error_code": r"-?\d+",
    "exit_code": r"-?\d+",
    "retry_count": r"\d+",
    "port": r"\d{2,5}",
    "num": r"-?\d+(?:\.\d+)?",
}


PLACEHOLDER_RE = re.compile(r"<(?P<name>\*|[a-zA-Z0-9_]+)>")


def regex_from_template(template: str) -> str:
    parts: list[str] = []
    position = 0
    counts: dict[str, int] = {}
    for match in PLACEHOLDER_RE.finditer(template):
        parts.append(re.escape(template[position : match.start()]))
        name = match.group("name")
        pattern = PLACEHOLDER_PATTERNS.get(name, r"\S+")
        group_base = "wildcard" if name == "*" else name
        counts[group_base] = counts.get(group_base, 0) + 1
        group_name = group_base if counts[group_base] == 1 else f"{group_base}_{counts[group_base]}"
        parts.append(f"(?P<{group_name}>{pattern})")
        position = match.end()
    parts.append(re.escape(template[position:]))
    return "^" + "".join(parts).replace(r"\ ", r"\s+") + "$"
