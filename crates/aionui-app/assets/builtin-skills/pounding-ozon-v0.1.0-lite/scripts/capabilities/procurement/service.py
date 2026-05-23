#!/usr/bin/env python3
from __future__ import annotations

from lib.ak_1688_client import create_procurement_task
from lib.normalizer import normalize_inquiry_request


def create_procurement(offer_name: str, count: str, demand: str) -> dict:
    result = create_procurement_task(offer_name=offer_name, count=count, demand=demand)
    return {
        'reference_result': {
            'success': True,
            'data': {
                'data': result,
            },
        },
        'normalized_inquiry': normalize_inquiry_request(offer_name, count, demand),
    }
