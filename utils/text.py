"""Lightweight text utilities used by agents."""

from __future__ import annotations

import re
from typing import Iterable, List, Tuple


def clean_text(text: str) -> str:
    """Normalize whitespace and remove spurious characters."""
    text = text.replace("\r", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    max_tokens: int = 1000,
    overlap: int = 120,
) -> List[str]:
    """
    Chunk text using a simple token approximation.

    Tokens are approximated as words. Overlap keeps context continuity.
    """
    words = text.split()
    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end == len(words):
            break
        start = end - overlap
    return chunks


def abstract_text(text: str, max_words: int = 140) -> str:
    """Generate a light-weight abstract by taking the leading content."""
    words = text.split()
    return " ".join(words[:max_words])


def find_sections(text: str) -> Iterable[Tuple[str, str]]:
    """
    Yield (heading, body) pairs based on a section-like pattern.

    This is intentionally lightweight for offline usage.
    """
    pattern = re.compile(r"(?P<heading>Section\s+\d+(?:\.\d+)*)[:\s-]*(?P<body>[^S]*)", re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if not matches:
        yield ("RFP", text)
        return

    for idx, match in enumerate(matches):
        start = match.start("body")
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        heading = match.group("heading").strip()
        body = text[start:end].strip()
        yield (heading, body)


