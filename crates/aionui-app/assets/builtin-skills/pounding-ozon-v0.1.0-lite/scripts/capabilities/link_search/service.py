#!/usr/bin/env python3
from __future__ import annotations

from lib.ak_1688_client import link_search as run_link_search
from lib.normalizer import normalize_product_candidates


def search_link(url: str, limit: int = 10, sort: str | None = None, image: str | None = None) -> dict:
    result = run_link_search(url=url, limit=limit, sort_type=sort, image=image)
    products = result.get('similar_products', [])
    return {
        'reference_result': {
            'success': bool(result.get('success', True)),
            'data': {
                'data': result,
            },
        },
        'normalized_candidates': normalize_product_candidates(products),
    }
