#!/usr/bin/env python3
from __future__ import annotations

from lib.ak_1688_client import image_search as run_image_search
from lib.normalizer import normalize_product_candidates


def search_image(image: str, limit: int = 10, sort: str | None = None) -> dict:
    result = run_image_search(image=image, limit=limit, sort_type=sort)
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
