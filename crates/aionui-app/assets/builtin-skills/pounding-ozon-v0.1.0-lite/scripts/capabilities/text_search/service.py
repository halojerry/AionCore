#!/usr/bin/env python3
from __future__ import annotations

from lib.ak_1688_client import text_search as run_text_search
from lib.normalizer import normalize_product_candidates


def search_text(query: str, limit: int = 10, sort: str | None = None) -> dict:
    result = run_text_search(query=query, limit=limit, sort_type=sort)
    products = result.get('similar_products', [])
    return {
        'reference_result': {
            'success': True,
            'data': {
                'data': result,
            },
        },
        'normalized_candidates': normalize_product_candidates(products),
    }
