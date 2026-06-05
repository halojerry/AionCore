#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from lib.ak_1688_client import canonicalize_source_product_url
from lib.image_manifest_builder import OZON_UPLOAD_SLOT_ORDER, PRIMARY_SLOT, manifest_slot_records
from models.contracts import AssetManifest, NormalizedProductDraft


def _build_final_summary(
    draft: NormalizedProductDraft,
    result: dict[str, Any],
) -> dict[str, Any]:
    upload_record = ((result.get('stages') or {}).get('upload') or {}).get('record') or {}
    pricing = ((result.get('stages') or {}).get('pricing') or {})
    status_stage = ((result.get('stages') or {}).get('status_polling') or {})
    terminal = ((result.get('stages') or {}).get('terminal_status') or {})
    final_status = terminal.get('final') or status_stage
    raw_status = final_status.get('raw') if isinstance(final_status, dict) else {}
    items = ((raw_status or {}).get('result') or {}).get('items') or []
    first_item = next((item for item in items if isinstance(item, dict)), {})
    resolved_product_id = (
        first_item.get('product_id')
        or draft.attributes.get('ozon_product_id')
        or final_status.get('product_id')
        or ''
    )
    classified_outcome = (
        terminal.get('classified_outcome')
        or status_stage.get('classified_outcome')
        or ('blocked' if result.get('blocked') else 'unknown')
    )
    success = classified_outcome in {'success', 'partial_success'}
    source_url = (
        canonicalize_source_product_url(draft.provenance.get('detail_url'))
        or canonicalize_source_product_url(draft.source_item_id)
        or canonicalize_source_product_url(draft.attributes.get('sku_id'))
    )
    task_id = upload_record.get('task_id')
    ozon_status_text = classified_outcome
    if final_status:
        ozon_status_text = final_status.get('classified_outcome') or classified_outcome
    detail_enrichment = ((result.get('stages') or {}).get('detail_enrichment') or {})
    browser_probe = dict(detail_enrichment.get('browser_probe') or {})
    return {
        'success': success,
        'classified_outcome': classified_outcome,
        'title': draft.title,
        'source_item_id': draft.source_item_id,
        'offer_id': str(draft.attributes.get('sku_id') or draft.source_item_id),
        'source_url': source_url,
        'source_1688_url': source_url,
        'product_id': str(resolved_product_id),
        'ozon_task_id': task_id,
        'ozon_status': final_status,
        'publish_status': ozon_status_text,
        'currency_code': pricing.get('currency_code') or draft.attributes.get('ozon_currency_code') or 'CNY',
        'procurement_cost': pricing.get('procurement_cost_cny'),
        'profit_margin': pricing.get('target_profit_rate'),
        'suggested_price': pricing.get('price_cny'),
        'pricing': pricing,
        'browser_probe': browser_probe or None,
        'browser_probe_reason_code': browser_probe.get('reason_code'),
        'browser_probe_reason_label': browser_probe.get('reason_label'),
        'detail_enrichment_mode': detail_enrichment.get('mode'),
    }


def _issue_codes(result: dict[str, Any]) -> set[str]:
    issues = (((result.get('stages') or {}).get('gate') or {}).get('issues') or [])
    return {str(item.get('code') or '') for item in issues}


def _has_currency_contract_error(result: dict[str, Any]) -> bool:
    terminal = ((result.get('stages') or {}).get('terminal_status') or {}).get('final') or {}
    raw = terminal.get('raw') or {}
    items = ((raw.get('result') or {}).get('items') or [])
    for item in items:
        for error in item.get('errors') or []:
            if str(error.get('code') or '') == 'currency_differs_from_contract':
                return True
    return False


def _iter_terminal_errors(result: dict[str, Any]) -> list[dict[str, Any]]:
    terminal = ((result.get('stages') or {}).get('terminal_status') or {}).get('final') or {}
    raw = terminal.get('raw') or {}
    items = ((raw.get('result') or {}).get('items') or [])
    errors: list[dict[str, Any]] = []
    for item in items:
        item_status = item.get('status')
        for error in item.get('errors') or []:
            if isinstance(error, dict):
                normalized = dict(error)
                normalized.setdefault('item_status', item_status)
                errors.append(normalized)
    return errors


def _has_retryable_attribute_error(result: dict[str, Any]) -> bool:
    for error in _iter_terminal_errors(result):
        code = str(error.get('code') or '').lower()
        field = str(error.get('field') or '').lower()
        message = str(error.get('message') or '').lower()
        attribute_id = error.get('attribute_id')
        if attribute_id not in (None, '', 0):
            return True
        if 'attribute' in code or 'dictionary' in code:
            return True
        if field.startswith('attributes') or '.attributes' in field:
            return True
        if any(token in message for token in ('attribute', 'dictionary', 'характерист', 'атрибут', 'required value', 'invalid value')):
            return True
    return False


def _invalid_remote_image_slots(result: dict[str, Any], assets: AssetManifest) -> list[str]:
    gate = ((result.get('stages') or {}).get('gate') or {})
    issues = list(gate.get('issues') or [])
    bad_urls = {
        str(item.get('url') or '')
        for issue in issues
        if str(issue.get('code') or '') == 'INVALID_REMOTE_IMAGE_URLS'
        for item in list(issue.get('invalid_urls') or [])
        if str(item.get('url') or '')
    }
    if not bad_urls:
        return []
    slot_records = manifest_slot_records(assets)
    slots: list[str] = []
    for slot in OZON_UPLOAD_SLOT_ORDER:
        record = slot_records.get(slot) or {}
        urls = list(record.get('image_urls') or [])
        if any(url in bad_urls for url in urls):
            slots.append(slot)
    if PRIMARY_SLOT in slots:
        followup_slots = [slot for slot in slots if slot != PRIMARY_SLOT]
        return [PRIMARY_SLOT, *followup_slots]
    return slots
