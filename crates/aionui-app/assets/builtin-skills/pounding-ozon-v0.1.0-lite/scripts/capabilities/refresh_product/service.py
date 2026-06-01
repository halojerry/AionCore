#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from _errors import ValidationError
from capabilities.publish_flow.service import orchestrate_publish_flow
from capabilities.text_search.service import search_text
from lib.ak_1688_client import canonicalize_source_product_url
from lib.managed_registry import find_item, list_items, upsert_item
from lib.ozon_wrappers import list_product_infos, list_products
from lib.store_metrics import product_metric_history, write_daily_snapshot
from models.contracts import NormalizedProductDraft


def list_store_products(*, limit: int = 20, last_id: str = '', visibility: str = 'ALL') -> dict[str, Any]:
    payload = list_products(last_id=last_id, limit=limit, visibility=visibility)
    items = list((payload.get('result') or {}).get('items') or [])
    return {
        'items': items,
        'total': ((payload.get('result') or {}).get('total') or 0),
        'last_id': ((payload.get('result') or {}).get('last_id') or ''),
    }


def get_store_product(*, product_id: str | None = None, offer_id: str | None = None) -> dict[str, Any]:
    if product_id:
        infos = list_product_infos(product_ids=[product_id])
    elif offer_id:
        infos = list_product_infos(offer_ids=[offer_id])
    else:
        raise ValidationError('必须提供 product_id 或 offer_id')
    if not infos:
        raise ValidationError('未找到指定 Ozon 商品，无法翻新')
    return infos[0]


def build_refresh_draft(product: dict[str, Any], source_1688_url: str | None = None) -> NormalizedProductDraft:
    images = list(product.get('images') or [])
    if not images:
        primary = list(product.get('primary_image') or [])
        images = primary if primary else []
    product_id = str(product.get('id') or product.get('product_id') or '')
    offer_id = str(product.get('offer_id') or '')
    title = str(product.get('name') or '')
    description = str(product.get('description') or '')
    category_id = str(product.get('description_category_id') or '')
    type_id = str(product.get('type_id') or '')
    category_ids = [category_id] if category_id else []
    registry_item = find_item(product_id=product_id, offer_id=offer_id)
    provenance = {
        'source_type': 'ozon_refresh',
        'ozon_product_id': product_id,
        'ozon_offer_id': offer_id,
    }
    normalized_source_1688_url = (
        canonicalize_source_product_url(source_1688_url)
        or canonicalize_source_product_url((registry_item or {}).get('source_1688_url'))
    )
    if normalized_source_1688_url:
        provenance['detail_url'] = normalized_source_1688_url
    return NormalizedProductDraft(
        source_item_id=product_id or offer_id,
        sku_count=1,
        source_category_ids=category_ids,
        title=title,
        description=description,
        attributes={
            'sku_id': offer_id or product_id,
            'price': product.get('price'),
            'ozon_product_id': product_id,
            'ozon_offer_id': offer_id,
            'ozon_type_id': type_id,
            'ozon_currency_code': product.get('currency_code'),
        },
        source_images=images,
        provenance=provenance,
    )


def _better_supply_candidates(query: str, limit: int = 5) -> dict[str, Any]:
    result = search_text(query, limit=limit)
    candidates = list(result.get('normalized_candidates') or [])
    return {
        'query': query,
        'candidate_count': len(candidates),
        'candidates': candidates,
    }


def refresh_product(
    *,
    product_id: str | None = None,
    offer_id: str | None = None,
    source_1688_url: str | None = None,
    search_better_supply: bool = True,
    poll_status: bool = False,
    correlation_id: str,
    batch_id: str,
) -> dict[str, Any]:
    product = get_store_product(product_id=product_id, offer_id=offer_id)
    draft = build_refresh_draft(product, source_1688_url=source_1688_url)
    supply_candidates = _better_supply_candidates(draft.title, limit=5) if search_better_supply and draft.title else None
    publish_result = orchestrate_publish_flow(
        draft_data=asdict(draft),
        dry_run=False,
        poll_status=poll_status,
        correlation_id=correlation_id,
        batch_id=batch_id,
    )
    final_summary = dict(publish_result.get('final_summary') or {})
    registry_record = upsert_item({
        'product_id': str(product.get('id') or product.get('product_id') or ''),
        'offer_id': str(product.get('offer_id') or ''),
        'source_1688_url': canonicalize_source_product_url(draft.provenance.get('detail_url')),
        'source_item_id': draft.source_item_id,
        'managed_by_us': True,
        'created_via': 'refresh_product',
        'last_refresh_at': final_summary.get('ozon_task_id') or batch_id,
        'last_refresh_result': final_summary.get('classified_outcome'),
    })
    return {
        'mode': 'refresh_product',
        'final_summary': final_summary,
        'source_product': product,
        'refresh_draft': asdict(draft),
        'better_supply_candidates': supply_candidates,
        'publish_result': publish_result,
        'registry_record': registry_record,
    }


def list_managed_products() -> dict[str, Any]:
    items = list_items()
    return {
        'total': len(items),
        'items': items,
    }


def _is_three_day_no_growth_candidate(product: dict[str, Any], managed_item: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    statuses = dict(product.get('statuses') or {})
    visibility_details = dict(product.get('visibility_details') or {})
    has_stock = bool((product.get('stocks') or {}).get('has_stock'))
    if has_stock and not visibility_details.get('has_price', True):
        reasons.append('has_stock_but_no_price')
    if has_stock and statuses.get('status_name') == 'Не продается':
        reasons.append('has_stock_but_not_selling')
    if managed_item and managed_item.get('managed_by_us') and managed_item.get('three_day_no_growth'):
        reasons.append('managed_snapshot_three_day_no_growth')
    product_id = str(product.get('id') or product.get('product_id') or '')
    history = product_metric_history(product_id, days=3)
    if len(history) >= 3:
        all_no_stock = all(not bool((item.get('stocks') or {}).get('has_stock')) for item in history)
        same_status = len({str(((item.get('statuses') or {}).get('status_name') or '')) for item in history}) == 1
        same_price = len({str(item.get('price') or '') for item in history}) == 1
        if same_status and same_price and all_no_stock:
            reasons.append('three_day_snapshot_no_growth')
    return bool(reasons), reasons


def snapshot_store_products(*, limit: int = 100, last_id: str = '', visibility: str = 'ALL') -> dict[str, Any]:
    payload = list_products(last_id=last_id, limit=limit, visibility=visibility)
    summaries = list((payload.get('result') or {}).get('items') or [])
    snapshot_items: list[dict[str, Any]] = []
    for summary in summaries:
        product_id = str(summary.get('product_id') or '')
        offer_id = str(summary.get('offer_id') or '')
        try:
            product = get_store_product(product_id=product_id or None, offer_id=offer_id or None)
        except Exception:
            continue
        snapshot_items.append({
            'product_id': product_id,
            'offer_id': offer_id,
            'price': product.get('price'),
            'stocks': product.get('stocks') or {},
            'statuses': product.get('statuses') or {},
            'visibility_details': product.get('visibility_details') or {},
            'updated_at': product.get('updated_at'),
        })
    snapshot = write_daily_snapshot(snapshot_items, meta={
        'visibility': visibility,
        'limit': limit,
        'last_id': ((payload.get('result') or {}).get('last_id') or ''),
        'source_total': ((payload.get('result') or {}).get('total') or 0),
    })
    return snapshot


def find_refresh_candidates(*, limit: int = 50, last_id: str = '', visibility: str = 'ALL', managed_only: bool = False) -> dict[str, Any]:
    store_payload = list_products(last_id=last_id, limit=limit, visibility=visibility)
    summaries = list((store_payload.get('result') or {}).get('items') or [])
    candidates: list[dict[str, Any]] = []
    managed_items = {
        str(item.get('product_id') or item.get('offer_id') or ''): item
        for item in list_items()
    }
    for summary in summaries:
        product_id = str(summary.get('product_id') or '')
        offer_id = str(summary.get('offer_id') or '')
        managed_item = managed_items.get(product_id) or managed_items.get(offer_id)
        if managed_only and not managed_item:
            continue
        try:
            full_product = get_store_product(product_id=product_id or None, offer_id=offer_id or None)
        except Exception as exc:
            candidates.append({
                'product_id': product_id,
                'offer_id': offer_id,
                'candidate': False,
                'reasons': [f'product_info_unavailable:{type(exc).__name__}'],
            })
            continue
        candidate, reasons = _is_three_day_no_growth_candidate(full_product, managed_item=managed_item)
        candidates.append({
            'product_id': product_id,
            'offer_id': offer_id,
            'candidate': candidate,
            'reasons': reasons,
            'managed_item': managed_item,
            'product': full_product,
        })
    return {
        'total': len(candidates),
        'items': candidates,
        'last_id': ((store_payload.get('result') or {}).get('last_id') or ''),
    }


def build_candidate_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    product = dict(candidate.get('product') or {})
    offer_id = str(candidate.get('offer_id') or product.get('offer_id') or '')
    product_id = str(candidate.get('product_id') or product.get('id') or '')
    title = str(product.get('name') or '')
    price = product.get('price')
    reasons = list(candidate.get('reasons') or [])
    suggested_action = 'review_then_refresh' if candidate.get('candidate') else 'observe'
    return {
        'product_id': product_id,
        'offer_id': offer_id,
        'title': title,
        'price': price,
        'candidate': bool(candidate.get('candidate')),
        'reasons': reasons,
        'suggested_action': suggested_action,
    }


def audit_refresh_candidates(*, limit: int = 50, last_id: str = '', visibility: str = 'ALL', managed_only: bool = False, write_snapshot: bool = True) -> dict[str, Any]:
    snapshot = snapshot_store_products(limit=limit, last_id=last_id, visibility=visibility) if write_snapshot else None
    candidate_result = find_refresh_candidates(limit=limit, last_id=last_id, visibility=visibility, managed_only=managed_only)
    actionable = [item for item in list(candidate_result.get('items') or []) if item.get('candidate')]
    return {
        'snapshot': snapshot,
        'candidate_result': candidate_result,
        'actionable_count': len(actionable),
        'actionable_summaries': [build_candidate_summary(item) for item in actionable],
        'agent_guidance': {
            'mode': 'review_first',
            'instruction': '先把 actionable_summaries 返回给 Agent/用户确认，再决定是否执行 refresh_product run。',
        },
    }
