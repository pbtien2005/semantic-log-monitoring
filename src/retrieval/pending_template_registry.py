"""Searchable pending template candidates for online-discovered patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.io_utils import read_jsonl
from src.chunking.template_discovery import candidate_id_for_template


PENDING_TEMPLATE_FILE = Path("data") / "templates" / "pending_templates.jsonl"


@dataclass(frozen=True, slots=True)
class PendingTemplateRecord:
    candidate_id: str
    dataset: str
    template: str
    draft_regex: str
    occurrences: int
    status: str = "pending"
    searchable: bool = True


@dataclass(frozen=True, slots=True)
class PendingTemplateHit:
    candidate_id: str
    score: float
    dataset: str
    template: str
    draft_regex: str
    occurrences: int
    status: str
    searchable: bool


def record_from_dict(record: dict[str, Any]) -> PendingTemplateRecord:
    candidate_id = str(record.get("candidate_id") or "")
    dataset = str(record.get("dataset") or "")
    template = str(record.get("template") or "")
    if not candidate_id and dataset and template:
        candidate_id = candidate_id_for_template(dataset, template)
    if not candidate_id:
        raise ValueError(f"Pending template record is missing candidate_id: {record}")
    if not dataset:
        raise ValueError(f"Pending template record is missing dataset: {record}")
    if not template:
        raise ValueError(f"Pending template record is missing template: {record}")
    return PendingTemplateRecord(
        candidate_id=candidate_id,
        dataset=dataset,
        template=template,
        draft_regex=str(record.get("draft_regex") or record.get("regex") or ""),
        occurrences=int(record.get("occurrences") or 0),
        status=str(record.get("status") or "pending"),
        searchable=bool(record.get("searchable", True)),
    )


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_.$:-]+", text.lower())
        if token and token != "*"
    }


def lexical_score(query: str, record: PendingTemplateRecord) -> float:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0.0
    text_tokens = tokenize(f"{record.dataset} {record.template} {record.draft_regex}")
    overlap = len(query_tokens & text_tokens)
    if overlap == 0:
        return 0.0
    coverage = overlap / len(query_tokens)
    occurrence_bonus = min(record.occurrences, 20) / 200.0
    return min(1.0, coverage + occurrence_bonus)


def hit_from_record(record: PendingTemplateRecord, *, score: float) -> PendingTemplateHit:
    return PendingTemplateHit(
        candidate_id=record.candidate_id,
        score=score,
        dataset=record.dataset,
        template=record.template,
        draft_regex=record.draft_regex,
        occurrences=record.occurrences,
        status=record.status,
        searchable=record.searchable,
    )


class PendingTemplateRegistry:
    def __init__(
        self,
        records: list[PendingTemplateRecord],
        *,
        path: Path | None = None,
        mtime_ns: int | None = None,
    ) -> None:
        self.records = [record for record in records if record.searchable and record.status == "pending"]
        self.path = path
        self.mtime_ns = mtime_ns
        self.by_id = {record.candidate_id: record for record in self.records}

    @classmethod
    def from_records(cls, records: list[dict[str, Any] | PendingTemplateRecord]) -> "PendingTemplateRegistry":
        typed_records = [
            record if isinstance(record, PendingTemplateRecord) else record_from_dict(record)
            for record in records
        ]
        return cls(typed_records)

    @classmethod
    def load(cls, root: Path, path: Path = PENDING_TEMPLATE_FILE) -> "PendingTemplateRegistry":
        pending_path = root / path if not path.is_absolute() else path
        if not pending_path.exists():
            return cls([], path=pending_path, mtime_ns=None)
        records = [record_from_dict(record) for record in read_jsonl(pending_path)]
        return cls(records, path=pending_path, mtime_ns=pending_path.stat().st_mtime_ns)

    def reload_if_changed(self) -> "PendingTemplateRegistry":
        if self.path is None:
            return self
        current_mtime = self.path.stat().st_mtime_ns if self.path.exists() else None
        if current_mtime == self.mtime_ns:
            return self
        root = self.path.parent.parent.parent
        relative = self.path.relative_to(root)
        return self.load(root, relative)

    def get(self, candidate_id: str) -> PendingTemplateRecord | None:
        return self.by_id.get(candidate_id)

    def get_many(self, candidate_ids: list[str]) -> list[PendingTemplateRecord]:
        return [record for candidate_id in candidate_ids if (record := self.get(candidate_id)) is not None]

    def search(
        self,
        query: str,
        *,
        dataset: str | None = None,
        top_k: int = 8,
        min_score: float | None = None,
    ) -> list[PendingTemplateHit]:
        hits = []
        for record in self.records:
            if dataset and record.dataset != dataset:
                continue
            score = lexical_score(query, record)
            if score <= 0.0:
                continue
            if min_score is not None and score < min_score:
                continue
            hits.append(hit_from_record(record, score=score))
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:top_k]
