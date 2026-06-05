#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from lib.ozon_wrappers import import_products
from lib.upload_ledger import find_by_payload_hash, upsert_record
from models.contracts import OzonImportPayload


def submit_payload(payload: OzonImportPayload, correlation_id: str, batch_id: str) -> dict[str, Any]:
    existing = find_by_payload_hash(payload.payload_hash)
    if existing and existing.get('status') in {'pending', 'ambiguous'}:
        return {'deduplicated': True, 'record': existing}

    task_id = import_products({'items': payload.items})
    record = {
        'correlation_id': correlation_id,
        'payload_hash': payload.payload_hash,
        'batch_id': batch_id,
        'task_id': task_id,
        'attempt_number': (existing.get('attempt_number', 0) + 1) if existing else 1,
        'status': 'pending' if task_id else 'blocked_failure',
    }
    upsert_record(record)
    return {'deduplicated': False, 'record': record}
