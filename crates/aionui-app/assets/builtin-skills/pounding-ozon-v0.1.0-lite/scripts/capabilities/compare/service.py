#!/usr/bin/env python3
from __future__ import annotations

from lib.ak_1688_client import compare_products as run_compare_products
from lib.normalizer import normalize_product_candidates


def compare_products(image: str | None = None, url: str | None = None, limit: int = 3) -> dict:
    result = run_compare_products(image=image, url=url, limit=limit)
    products = result.get('compare_products', [])
    return {
        'reference_result': {
            'success': True,
            'data': {
                'data': result,
            },
        },
        'normalized_candidates': normalize_product_candidates(products),
    }
