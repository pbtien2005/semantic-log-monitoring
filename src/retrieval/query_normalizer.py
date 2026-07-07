"""Lightweight query normalization helpers for retrieval planning."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\ufeff"
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class NormalizedQuery:
    raw_text: str
    clean_text: str
    lower_text: str
    accentless_text: str


def remove_zero_width(text: str) -> str:
    return text.translate({ord(char): None for char in ZERO_WIDTH_CHARS})


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", remove_zero_width(text))


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def remove_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return unicodedata.normalize("NFC", stripped)


def normalize_query(query: str) -> NormalizedQuery:
    clean = normalize_whitespace(normalize_unicode(query))
    lower = clean.casefold()
    accentless = remove_accents(lower)
    return NormalizedQuery(
        raw_text=query,
        clean_text=clean,
        lower_text=lower,
        accentless_text=accentless,
    )
