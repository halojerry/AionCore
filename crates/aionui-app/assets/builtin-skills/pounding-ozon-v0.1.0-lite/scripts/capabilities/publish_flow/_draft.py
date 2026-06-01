#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from _errors import ValidationError
from capabilities.compare.service import compare_products
from capabilities.image_search.service import search_image
from capabilities.link_search.service import search_link
from capabilities.text_search.service import search_text
from lib.ak_1688_client import canonicalize_source_product_url
from models.contracts import NormalizedProductDraft


def _select_confirmed_draft(source_result: dict) -> NormalizedProductDraft:
    candidates = list(source_result.get('normalized_candidates') or [])
    if not candidates:
        raise ValidationError('1688 intake 没有返回可用候选，无法继续')
    if len(candidates) != 1:
        raise ValidationError(
            f'1688 intake 返回了 {len(candidates)} 个候选；必须先明确选中 1 个商品，'
            f'再继续类目、属性、制图、上架链路'
        )
    first = candidates[0].get('normalized_draft') or {}
    return NormalizedProductDraft(**first)


def _fallback_draft_from_url(url: str) -> NormalizedProductDraft:
    canonical_url = canonicalize_source_product_url(url)
    if not canonical_url:
        raise ValidationError('1688 intake 没有返回可用候选，且无法从 URL 构造标准商品草稿')
    source_item_id = canonical_url.rsplit('/', 1)[-1].replace('.html', '').strip()
    if not source_item_id:
        raise ValidationError('1688 intake 没有返回可用候选，且无法从 URL 提取商品 ID')
    return NormalizedProductDraft(
        source_item_id=source_item_id,
        sku_count=1,
        source_category_ids=[],
        title='',
        description='',
        attributes={'sku_id': source_item_id},
        source_images=[],
        provenance={
            'detail_url': canonical_url,
            'search_type': 'link_search_fallback',
            'fallback_reason': 'link_search_no_candidates',
        },
        variants=[],
    )


def _backfill_source_images_from_ak_title_search(draft: NormalizedProductDraft) -> dict[str, Any] | None:
    if draft.source_images:
        return None
    query = str(draft.title or '').strip()
    source_item_id = str(draft.source_item_id or '').strip()
    if not query:
        return None
    try:
        result = search_text(query, limit=10)
    except Exception as exc:
        return {'ok': False, 'reason': 'ak_title_search_failed', 'error': str(exc)}
    candidates = list(result.get('normalized_candidates') or [])
    if not candidates:
        return {'ok': False, 'reason': 'ak_title_search_empty'}
    matched = None
    fallback = None
    for item in candidates:
        normalized = dict(item.get('normalized_draft') or {})
        candidate_images = list(normalized.get('source_images') or [])
        if not candidate_images:
            continue
        if fallback is None:
            fallback = normalized
        if str(normalized.get('source_item_id') or '').strip() == source_item_id:
            matched = normalized
            break
    selected = matched or fallback
    if not selected:
        return {'ok': False, 'reason': 'ak_title_search_no_images'}
    draft.source_images = list(selected.get('source_images') or [])
    draft.provenance['source_image_backfill'] = {
        'mode': 'ak_title_search',
        'matched_source_item_id': str(selected.get('source_item_id') or ''),
        'query': query,
        'exact_product_match': str(selected.get('source_item_id') or '').strip() == source_item_id,
    }
    return {
        'ok': True,
        'reason': 'ak_title_search',
        'matched_source_item_id': str(selected.get('source_item_id') or ''),
        'exact_product_match': str(selected.get('source_item_id') or '').strip() == source_item_id,
        'image_count': len(draft.source_images),
    }


def acquire_draft(
    *,
    draft_data: dict | None = None,
    query: str | None = None,
    image: str | None = None,
    url: str | None = None,
    compare_mode: bool = False,
    limit: int = 10,
) -> tuple[NormalizedProductDraft, dict]:
    if draft_data:
        draft = NormalizedProductDraft(**draft_data)
        return draft, {'source': 'draft_file', 'normalized_candidates': [{'normalized_draft': draft_data}]}
    if compare_mode:
        result = compare_products(image=image, url=url, limit=limit)
        return _select_confirmed_draft(result), result
    if query:
        result = search_text(query, limit=limit)
        return _select_confirmed_draft(result), result
    if image:
        result = search_image(image, limit=limit)
        return _select_confirmed_draft(result), result
    if url:
        result = search_link(url, limit=limit)
        candidates = list(result.get('normalized_candidates') or [])
        if candidates:
            return _select_confirmed_draft(result), result
        fallback_draft = _fallback_draft_from_url(url)
        fallback_result = {
            **result,
            'normalized_candidates': [{
                'normalized_draft': {
                    'source_item_id': fallback_draft.source_item_id,
                    'sku_count': fallback_draft.sku_count,
                    'source_category_ids': fallback_draft.source_category_ids,
                    'title': fallback_draft.title,
                    'description': fallback_draft.description,
                    'attributes': fallback_draft.attributes,
                    'source_images': fallback_draft.source_images,
                    'provenance': fallback_draft.provenance,
                    'variants': fallback_draft.variants,
                },
            }],
            'fallback_used': True,
            'fallback_reason': 'link_search_no_candidates',
        }
        return fallback_draft, fallback_result
    raise ValidationError('publish_flow 必须提供 --draft-file 或 query/image/url 来源')
