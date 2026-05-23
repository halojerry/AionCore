#!/usr/bin/env python3
from __future__ import annotations

import time
from typing import Any

from lib.ozon_wrappers import get_import_info


def classify_status(result: dict[str, Any]) -> str:
    items = ((result or {}).get('result') or {}).get('items', [])
    if not items:
        return 'ambiguous'
    if any(item.get('errors') for item in items):
        if all(item.get('status') == 'imported' for item in items):
            return 'blocked_failure'
        return 'partial_success'
    statuses = [item.get('status') for item in items]
    if all(status == 'imported' for status in statuses):
        return 'success'
    if any(status == 'imported' for status in statuses):
        return 'partial_success'
    if any(status in {'pending', 'processing'} for status in statuses):
        return 'ambiguous'
    return 'retryable_failure'


def check_task(task_id: str) -> dict[str, Any]:
    result = get_import_info(task_id)
    return {
        'raw': result,
        'classified_outcome': classify_status(result or {}),
    }


def wait_for_terminal_status(
    task_id: str,
    *,
    max_attempts: int = 10,
    interval_seconds: float = 3.0,
) -> dict[str, Any]:
    last: dict[str, Any] | None = None
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, max_attempts + 1):
        current = check_task(task_id)
        current['attempt'] = attempt
        attempts.append(current)
        last = current
        outcome = str(current.get('classified_outcome') or '')
        if outcome in {'success', 'partial_success', 'blocked_failure', 'retryable_failure'}:
            return {
                'task_id': task_id,
                'terminal': True,
                'classified_outcome': outcome,
                'attempts': attempts,
                'final': current,
            }
        if attempt < max_attempts:
            time.sleep(interval_seconds)
    return {
        'task_id': task_id,
        'terminal': False,
        'classified_outcome': str((last or {}).get('classified_outcome') or 'ambiguous'),
        'attempts': attempts,
        'final': last,
    }
