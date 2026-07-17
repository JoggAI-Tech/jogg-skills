from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List


CAPTION_LINE_COLUMNS = 36
CAPTION_MAX_LINES = 2
CAPTION_CUE_COLUMNS = CAPTION_LINE_COLUMNS * CAPTION_MAX_LINES - 2

_STRONG_BREAKS = frozenset("。！？!?；;")
_SOFT_BREAKS = frozenset("，,、：:")
_CLOSING_PUNCTUATION = frozenset("，。！？；、：,.!?;:)]}）】》〉」』”’％%")
_TRAILING_QUOTES = frozenset("）】》〉」』”’)]}")


def normalize_caption_text(value: Any) -> str:
    """Normalize authored narration without changing its spoken characters."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def caption_display_width(value: Any) -> int:
    """Return terminal-like columns so CJK glyphs count wider than Latin text."""
    width = 0
    for character in str(value or ""):
        if character in "\r\n" or unicodedata.combining(character):
            continue
        width += 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
    return width


def _split_after(text: str, punctuation: frozenset[str]) -> List[str]:
    parts: List[str] = []
    start = 0
    index = 0
    while index < len(text):
        if text[index] not in punctuation:
            index += 1
            continue
        end = index + 1
        while end < len(text) and text[end] in _TRAILING_QUOTES:
            end += 1
        part = text[start:end].strip()
        if part:
            parts.append(part)
        start = end
        index = end
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _prefix_widths(text: str) -> List[int]:
    widths = [0]
    for character in text:
        widths.append(widths[-1] + caption_display_width(character))
    return widths


def _hard_split(text: str, max_columns: int) -> List[str]:
    parts: List[str] = []
    remaining = text.strip()
    while caption_display_width(remaining) > max_columns:
        widths = _prefix_widths(remaining)
        limit = max(index for index, width in enumerate(widths) if width <= max_columns)
        candidates = [
            index
            for index in range(1, limit + 1)
            if remaining[index - 1].isspace() or remaining[index - 1] in _SOFT_BREAKS | _STRONG_BREAKS
        ]
        split_at = candidates[-1] if candidates else limit

        # Do not leave closing punctuation at the start of the following cue.
        if split_at < len(remaining) and remaining[split_at] in _CLOSING_PUNCTUATION:
            if widths[split_at + 1] <= max_columns:
                split_at += 1
            elif split_at > 1:
                split_at -= 1

        part = remaining[:split_at].strip()
        if not part:
            split_at = max(1, limit)
            part = remaining[:split_at].strip()
        parts.append(part)
        remaining = remaining[split_at:].strip()
    if remaining:
        parts.append(remaining)
    return parts


def _caption_atoms(text: str, max_columns: int) -> List[str]:
    atoms: List[str] = []
    for sentence in _split_after(text, _STRONG_BREAKS):
        if caption_display_width(sentence) <= max_columns:
            atoms.append(sentence)
            continue
        for clause in _split_after(sentence, _SOFT_BREAKS):
            if caption_display_width(clause) <= max_columns:
                atoms.append(clause)
            else:
                atoms.extend(_hard_split(clause, max_columns))
    return atoms


def _join_parts(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    separator = " " if left[-1].isascii() and right[0].isascii() and right[0].isalnum() else ""
    return f"{left}{separator}{right}"


def _caption_chunks(text: str) -> List[str]:
    chunks: List[str] = []
    current = ""
    for atom in _caption_atoms(text, CAPTION_CUE_COLUMNS):
        candidate = _join_parts(current, atom)
        if current and caption_display_width(candidate) > CAPTION_CUE_COLUMNS:
            chunks.append(current)
            current = atom
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _line_break_score(text: str, index: int, target_width: float) -> tuple[int, float, int]:
    previous = text[index - 1]
    if previous in _STRONG_BREAKS:
        priority = 0
    elif previous in _SOFT_BREAKS:
        priority = 1
    elif previous.isspace():
        priority = 2
    else:
        priority = 3
    width = caption_display_width(text[:index])
    return priority, abs(width - target_width), -width


def _wrap_caption(text: str) -> str:
    if caption_display_width(text) <= CAPTION_LINE_COLUMNS:
        return text

    widths = _prefix_widths(text)
    total = widths[-1]
    minimum = max(1, total - CAPTION_LINE_COLUMNS)
    candidates = [
        index
        for index in range(1, len(text))
        if minimum <= widths[index] <= CAPTION_LINE_COLUMNS
        and text[index] not in _CLOSING_PUNCTUATION
    ]
    if not candidates:
        candidates = [
            index
            for index in range(1, len(text))
            if minimum <= widths[index] <= CAPTION_LINE_COLUMNS
        ]
    if not candidates:
        return text

    target = total / 2
    split_at = min(candidates, key=lambda index: _line_break_score(text, index, target))
    first = text[:split_at].strip()
    second = text[split_at:].strip()
    return f"{first}\n{second}" if second else first


def build_caption_cues(text: Any, duration_seconds: float) -> List[Dict[str, Any]]:
    """Build deterministic, punctuation-aware cues inside one measured shot."""
    normalized = normalize_caption_text(text)
    duration = max(0.0, float(duration_seconds or 0.0))
    if not normalized or duration <= 0:
        return []

    chunks = _caption_chunks(normalized)
    weights = [max(1, caption_display_width(chunk)) for chunk in chunks]
    total_weight = sum(weights)
    cues: List[Dict[str, Any]] = []
    consumed = 0
    start = 0.0
    for index, (chunk, weight) in enumerate(zip(chunks, weights)):
        consumed += weight
        end = duration if index == len(chunks) - 1 else round(duration * consumed / total_weight, 6)
        cues.append(
            {
                "text": _wrap_caption(chunk),
                "start_seconds": round(start, 6),
                "end_seconds": round(end, 6),
            }
        )
        start = end
    return cues
