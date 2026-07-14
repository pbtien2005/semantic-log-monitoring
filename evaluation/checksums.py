"""Checksum helpers for dataset manifests."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    file_path = Path(path)
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_for_files(paths: Iterable[str | Path], *, base_dir: str | Path | None = None) -> dict[str, dict[str, str]]:
    base = Path(base_dir).resolve() if base_dir is not None else None
    manifest: dict[str, dict[str, str]] = {}
    for raw_path in paths:
        path = Path(raw_path)
        key = path.name if base is None else path.resolve().relative_to(base).as_posix()
        manifest[key] = {"sha256": sha256_file(path)}
    return manifest
