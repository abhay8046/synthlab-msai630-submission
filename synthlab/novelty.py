"""Cheap, deterministic lexical screens for repeated model generations.

Used as a conservative generation-time filter. Does not replace the
independent downstream diversity and near-copy evaluations.
"""
from __future__ import annotations
from difflib import SequenceMatcher
import re

def normalized(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(text).casefold()))

def most_similar(text: str, references, *, threshold: float = .88):
    """Return (flagged, highest_ratio); exact duplicates always trigger.

    Ratios describe textual form only, not semantic similarity.
    """
    if not 0 <= threshold <= 1:
        raise ValueError("Invalid duplicate similarity threshold")
    candidate = normalized(text)
    if not candidate:
        return True, 1.0
    best = 0.0
    for item in references:
        ref = normalized(item)
        if not ref:
            continue
        if candidate == ref:
            return True, 1.0
        # Quick same-string morphology check; n<=few hundred for weekend study.
        ratio = SequenceMatcher(None, candidate, ref, autojunk=False).ratio()
        best = max(best, ratio)
        if ratio >= threshold:
            return True, best
    return False, best
