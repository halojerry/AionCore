#!/usr/bin/env python3
from __future__ import annotations

from models.contracts import NormalizedProductDraft


def summarize_candidates(normalized_candidates: list[dict]) -> dict:
    first = normalized_candidates[0] if normalized_candidates else None
    return {
        'candidate_count': len(normalized_candidates),
        'first_candidate': first,
        'ready_for_next_stage': bool(first),
        'next_stage': 'category_resolution' if first else None,
    }
