"""In-memory template registry used by retrieval strategies."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.core.io_utils import read_jsonl


REGISTRY_DIR = Path("data") / "retrieval" / "template_registry"
REGISTRY_FILE = "template_registry.jsonl"
VECTORS_FILE = "template_vectors.npy"
META_FILE = "registry_meta.json"


@dataclass(frozen=True, slots=True)
class TemplateRecord:
    template_id: str
    dataset: str
    level: str | None
    component: str | None
    template: str
    search_text: str
    occurrences: int
    sample_messages: list[str]
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class TemplateHit:
    template_id: str
    score: float
    dataset: str
    level: str | None
    component: str | None
    template: str
    search_text: str
    occurrences: int
    sample_messages: list[str]
    metadata: dict[str, Any]
    filter_mode: str


def normalize_query_vector(query_vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(query_vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector
    return vector / norm


def record_from_dict(record: dict[str, Any]) -> TemplateRecord:
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    passthrough_metadata = {
        key: record.get(key)
        for key in (
            "regex",
            "priority",
            "active",
            "vector_index",
        )
        if key in record
    }
    template = str(
        record.get("template")
        or metadata.get("template")
        or payload.get("template")
        or ""
    )
    search_text = str(
        record.get("search_text")
        or record.get("embed_text")
        or payload.get("embed_text")
        or template
    )
    sample_messages = (
        record.get("sample_messages")
        or metadata.get("sample_messages")
        or payload.get("sample_messages")
        or []
    )
    occurrences = (
        record.get("occurrences")
        or record.get("occurrence_count")
        or metadata.get("occurrence_count")
        or 0
    )
    return TemplateRecord(
        template_id=str(record.get("template_id") or record.get("chunk_id")),
        dataset=str(record.get("dataset")),
        level=record.get("level"),
        component=record.get("component"),
        template=template,
        search_text=search_text,
        occurrences=int(occurrences),
        sample_messages=[str(message) for message in sample_messages],
        metadata={**payload, **metadata, **passthrough_metadata},
    )


def hit_from_record(record: TemplateRecord, *, score: float, filter_mode: str) -> TemplateHit:
    return TemplateHit(
        template_id=record.template_id,
        score=score,
        dataset=record.dataset,
        level=record.level,
        component=record.component,
        template=record.template,
        search_text=record.search_text,
        occurrences=record.occurrences,
        sample_messages=record.sample_messages,
        metadata=record.metadata,
        filter_mode=filter_mode,
    )


class TemplateRegistry:
    """Small vector index for template records, intended to live in process RAM."""

    def __init__(
        self,
        records: list[TemplateRecord],
        vectors: np.ndarray,
        *,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if len(records) != len(vectors):
            raise ValueError("Template record count must match vector count.")
        self.records = records
        self.vectors = np.asarray(vectors, dtype=np.float32)
        if self.vectors.ndim != 2:
            raise ValueError("Template vectors must be a 2D matrix.")
        self.meta = meta or {}
        self.by_id = {record.template_id: record for record in records}

    @classmethod
    def from_records(
        cls,
        records: list[dict[str, Any] | TemplateRecord],
        vectors: np.ndarray,
        *,
        meta: dict[str, Any] | None = None,
    ) -> "TemplateRegistry":
        typed_records = [
            record if isinstance(record, TemplateRecord) else record_from_dict(record)
            for record in records
        ]
        return cls(typed_records, vectors, meta=meta)

    @classmethod
    def load(cls, root: Path, datasets: list[str] | None = None) -> "TemplateRegistry":
        base = root / REGISTRY_DIR
        if not base.exists():
            raise FileNotFoundError(
                f"Template registry directory not found: {base}. "
                "Run infra/scripts/storage/build_template_registry.py first."
            )
        meta_path = base / META_FILE
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        dataset_dirs = [base / dataset for dataset in datasets] if datasets else [
            path for path in base.iterdir() if path.is_dir()
        ]

        records: list[TemplateRecord] = []
        vector_batches: list[np.ndarray] = []
        for dataset_dir in sorted(dataset_dirs):
            registry_path = dataset_dir / REGISTRY_FILE
            vectors_path = dataset_dir / VECTORS_FILE
            if not registry_path.exists() or not vectors_path.exists():
                continue
            dataset_records = [record_from_dict(record) for record in read_jsonl(registry_path)]
            dataset_vectors = np.load(vectors_path).astype(np.float32)
            if len(dataset_records) != len(dataset_vectors):
                raise ValueError(f"Registry/vector count mismatch in {dataset_dir}")
            records.extend(dataset_records)
            vector_batches.append(dataset_vectors)

        if not records:
            raise FileNotFoundError(f"No template registry artifacts found under {base}")

        vectors = np.vstack(vector_batches) if vector_batches else np.empty((0, 0), dtype=np.float32)
        return cls(records, vectors, meta=meta)

    def get(self, template_id: str) -> TemplateRecord | None:
        return self.by_id.get(template_id)

    def get_many(self, template_ids: list[str]) -> list[TemplateRecord]:
        return [record for template_id in template_ids if (record := self.get(template_id)) is not None]

    def _candidate_mask(
        self,
        *,
        dataset: str | None,
        level: str | None,
        component: str | None,
        mode: str,
    ) -> np.ndarray:
        use_level = mode not in {"fallback_without_level", "fallback_without_component_and_level"}
        use_component = mode not in {"fallback_without_component", "fallback_without_component_and_level"}
        mask = np.ones(len(self.records), dtype=bool)
        for index, record in enumerate(self.records):
            if dataset and record.dataset != dataset:
                mask[index] = False
            if use_level and level and record.level != level:
                mask[index] = False
            if use_component and component and record.component != component:
                mask[index] = False
        return mask

    def _candidate_modes(self, *, level: str | None, component: str | None) -> list[str]:
        modes = ["exact"]
        if component:
            modes.append("fallback_without_component")
        if level:
            modes.append("fallback_without_level")
        if component and level:
            modes.append("fallback_without_component_and_level")
        return modes

    def search(
        self,
        query_vector: np.ndarray,
        *,
        dataset: str | None = None,
        level: str | None = None,
        component: str | None = None,
        top_k: int = 8,
        min_score: float | None = None,
        fallback_if_empty: bool = True,
    ) -> list[TemplateHit]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if not self.records:
            return []

        candidate_modes = self._candidate_modes(level=level, component=component)
        if not fallback_if_empty:
            candidate_modes = ["exact"]

        selected_mask: np.ndarray | None = None
        selected_mode = "exact"
        for mode in candidate_modes:
            mask = self._candidate_mask(
                dataset=dataset,
                level=level,
                component=component,
                mode=mode,
            )
            if bool(mask.any()):
                selected_mask = mask
                selected_mode = mode
                break

        if selected_mask is None:
            return []

        vector = normalize_query_vector(query_vector)
        scores = self.vectors @ vector
        candidate_indexes = np.flatnonzero(selected_mask)
        sorted_indexes = sorted(
            candidate_indexes,
            key=lambda index: float(scores[index]),
            reverse=True,
        )

        hits = [
            hit_from_record(self.records[index], score=float(scores[index]), filter_mode=selected_mode)
            for index in sorted_indexes[:top_k]
        ]
        if min_score is not None:
            hits = [hit for hit in hits if hit.score >= min_score]
        return hits
