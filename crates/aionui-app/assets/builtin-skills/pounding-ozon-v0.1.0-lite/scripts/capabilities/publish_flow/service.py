#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import time
from dataclasses import asdict
from typing import Any

from _errors import ValidationError
from capabilities.category_resolution.service import resolve_category
from capabilities.ozon_cache.service import get_category_tree
from capabilities.compare.service import compare_products
from capabilities.image_pipeline.service import build_stub_manifest, execute_image_pipeline, plan_image_pipeline, repair_image_pipeline_slots
from capabilities.image_search.service import search_image
from capabilities.link_search.service import search_link
from capabilities.property_dictionary.service import resolve_property_dictionary
from capabilities.status.service import check_task, wait_for_terminal_status
from capabilities.text_search.service import search_text
from capabilities.upload.service import submit_payload
from lib.config_store import load_config, save_config
from lib.payload_builder import build_payload
from lib.pricing import calculate_listing_price_cny
from lib.progress import emit_progress
from lib.supabase_client import has_supabase_config, resolve_category_from_supabase, sync_category_mapping_safely
from lib.publish_gate import gate_summary
from lib.cache_store import read_category_cache, read_category_tree_cache
from lib.image_manifest_builder import OZON_UPLOAD_SLOT_ORDER, PRIMARY_SLOT, manifest_slot_records
from models.contracts import AssetManifest, CategoryResolution, NormalizedProductDraft, ResolvedAttributeSet, RuntimeConfig
from lib.ozon_wrappers import detect_contract_currency
from lib.ak_1688_client import canonicalize_source_product_url, enrich_product_with_detail
from lib.family_partition import family_partition_summary, partition_families


def _build_metric_gaps(draft: NormalizedProductDraft) -> dict[str, Any] | None:
    weight_grams = draft.attributes.get('weight_grams') or draft.provenance.get('weight_grams')
    dims = draft.attributes.get('dimensions_mm') or draft.provenance.get('dimensions_mm') or {}
    try:
        height = int((dims or {}).get('height') or 0)
        width = int((dims or {}).get('width') or 0)
        depth = int((dims or {}).get('depth') or 0)
    except Exception:
        height = width = depth = 0
    missing = []
    if not weight_grams:
        missing.append('weight_grams')
    if min(height, width, depth) <= 0:
        missing.append('dimensions_mm')
    if not missing:
        return None
    critical_missing = [field for field in missing if field in {'weight_grams', 'dimensions_mm'}]
    non_critical_missing = [field for field in missing if field not in {'weight_grams', 'dimensions_mm'}]
    return {
        'missing_fields': missing,
        'critical_missing_fields': critical_missing,
        'non_critical_missing_fields': non_critical_missing,
        'is_critical': bool(critical_missing),
        'has_weight_grams': bool(weight_grams),
        'has_dimensions_mm': min(height, width, depth) > 0,
        'current_weight_grams': weight_grams,
        'current_dimensions_mm': {'height': height, 'width': width, 'depth': depth} if any([height, width, depth]) else None,
        'agent_action': 'critical_missing_fields 由程序阻断或继续；non_critical_missing_fields 仅返回给 agent 参考，程序不做 LLM 估算',
    }


def _build_required_gap_report(
    _draft: NormalizedProductDraft,
    metric_gaps: dict[str, Any] | None,
    browser_probe: dict[str, Any] | None,
) -> dict[str, Any] | None:
    gaps: list[dict[str, Any]] = []
    if metric_gaps:
        for field in metric_gaps.get('critical_missing_fields') or []:
            gaps.append({
                'field': field,
                'critical': True,
                'source': 'logistics_pricing',
                'reason_code': 'critical_metric_missing',
                'reason_label': '缺少物流定价依赖字段',
            })
        for field in metric_gaps.get('non_critical_missing_fields') or []:
            gaps.append({
                'field': field,
                'critical': False,
                'source': 'product_metadata',
                'reason_code': 'non_critical_metric_missing',
                'reason_label': '非关键字段缺失，允许继续',
            })
    if browser_probe and browser_probe.get('error') == 'no_matching_open_page':
        if metric_gaps and metric_gaps.get('critical_missing_fields'):
            gaps.append({
                'field': 'browser_probe',
                'critical': True,
                'source': 'browser_fallback',
                'reason_code': 'no_matching_open_page',
                'reason_label': '未找到已打开的目标商品页，关键字段回退失败',
            })
    if not gaps:
        return None
    return {
        'required_gap_count': sum(1 for gap in gaps if gap.get('critical')),
        'non_critical_gap_count': sum(1 for gap in gaps if not gap.get('critical')),
        'gaps': gaps,
    }


def _family_partition_stage(draft: NormalizedProductDraft) -> dict[str, Any]:
    partition = partition_families(draft)
    summary = family_partition_summary(partition)
    draft.family_partition = summary
    if summary.get('family_groups'):
        first_group = summary['family_groups'][0]
        draft.family_key = str(first_group.get('family_key') or '') or None
        draft.family_label = str(first_group.get('family_label') or '') or None
    return summary


def _browser_probe_reason_label(reason_code: str | None, ready: bool = False) -> str | None:
    if ready:
        return '浏览器补强成功'
    mapping = {
        'failure_cooldown_active': '浏览器抓取冷却中，已自动回退 AK',
        'failure_page': '浏览器命中失败页，已自动回退 AK',
        'captcha_intercepted': '浏览器命中验证码拦截，已自动回退 AK',
        'no_matching_open_page': '浏览器未发现已打开的目标商品页，已自动回退 AK',
        'probe_not_ready': '浏览器未拿到有效商品页，已自动回退 AK',
        'probe_exception': '浏览器抓取异常，已自动回退 AK',
        'login_required': '浏览器仍需登录，已自动回退 AK',
    }
    return mapping.get(str(reason_code or '').strip()) or ('已自动回退 AK' if reason_code else None)


def _resolve_category_with_source(
    draft: NormalizedProductDraft,
    cfg: RuntimeConfig,
) -> tuple[CategoryResolution, str]:
    if not read_category_tree_cache().get('result'):
        try:
            get_category_tree(language='ZH_HANS', force_refresh=False)
        except Exception:
            pass
    category_cache = read_category_cache()
    category = resolve_category(draft, category_cache.get('entries', []), cfg)
    category_source = 'local_cache'
    if category.explanation.get('blocked') and has_supabase_config():
        try:
            remote_category = resolve_category_from_supabase(draft)
        except Exception:
            remote_category = None
        if remote_category and not remote_category.explanation.get('blocked'):
            remote_category.explanation = dict(remote_category.explanation or {})
            remote_category.explanation.setdefault('margin', remote_category.confidence)
            category = remote_category
            category_source = 'supabase_verified'
    return category, category_source


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


def resolve_ozon_currency(config: RuntimeConfig) -> dict:
    current = str(config.ozon_currency or '').strip().upper()
    if current in {'RUB', 'CNY', 'USD', 'EUR'}:
        return {'source': 'config', 'currency_code': current, 'detected': True}
    try:
        detected = detect_contract_currency()
    except Exception as exc:
        return {'source': 'api_probe', 'currency_code': None, 'detected': False, 'error': str(exc)}
    if detected:
        config.ozon_currency = detected
        try:
            save_config(config)
        except Exception:
            pass
        return {'source': 'api_probe', 'currency_code': detected, 'detected': True}
    return {
        'source': 'api_probe',
        'currency_code': None,
        'detected': False,
        'message': '未能从 Ozon API 自动探测到当前店铺币种；若店铺没有可读价格商品，请让用户手动确认一次币种。',
    }

def preflight() -> tuple[RuntimeConfig, list[str]]:
    cfg = load_config()
    missing: list[str] = []
    if not cfg.ali_1688_ak:
        missing.append('1688 AK')
    if not cfg.ozon_client_id or not cfg.ozon_api_key:
        missing.append('Ozon 店铺配置')
    if not cfg.mxou_token:
        missing.append('mxou token')
    return cfg, missing


def _select_confirmed_draft(source_result: dict) -> NormalizedProductDraft:
    candidates = list(source_result.get('normalized_candidates') or [])
    if not candidates:
        raise ValidationError('1688 intake 没有返回可用候选，无法继续')
    if len(candidates) != 1:
        raise ValidationError(f'1688 intake 返回了 {len(candidates)} 个候选；必须先明确选中 1 个商品，再继续类目、属性、制图、上架链路')
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
        attributes={
            'sku_id': source_item_id,
        },
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


def _coerce_assets(
    assets_data: dict | None,
    draft: NormalizedProductDraft,
    use_stub: bool,
    execute_real: bool,
) -> tuple[AssetManifest, dict]:
    if assets_data:
        return AssetManifest(**assets_data), {'mode': 'provided_manifest'}
    if use_stub:
        return build_stub_manifest(draft), {'mode': 'stub_manifest'}
    if execute_real:
        result = execute_image_pipeline(draft)
        return result['manifest'], {
            'mode': 'executed',
            'round_records': result['round_records'],
            'pending_slots': result['pending_slots'],
            'completed_slots': result['completed_slots'],
        }
    plan = plan_image_pipeline(draft)
    return AssetManifest(), {'mode': 'planned_only', 'plan': plan}


def _repair_invalid_asset_slots(
    draft: NormalizedProductDraft,
    assets: AssetManifest,
    result: dict[str, Any],
) -> dict[str, Any] | None:
    invalid_slots = _invalid_remote_image_slots(result, assets)
    if not invalid_slots:
        return None
    repaired = repair_image_pipeline_slots(draft, assets, invalid_slots)
    return {
        'assets_data': asdict(repaired['manifest']),
        'repair_stage': repaired,
        'invalid_slots': invalid_slots,
    }


def _family_child_drafts_from_partition(draft: NormalizedProductDraft, family_partition_stage: dict[str, Any]) -> list[NormalizedProductDraft]:
    family_groups = list(family_partition_stage.get('family_groups') or [])
    if len(family_groups) <= 1:
        return [draft]

    child_drafts: list[NormalizedProductDraft] = []
    for group in family_groups:
        family_key = str(group.get('family_key') or '').strip() or None
        family_label = str(group.get('family_label') or '').strip() or None
        merge_group_value = str(group.get('merge_group_value') or '').strip()
        child_attributes = dict(draft.attributes or {})
        child_attributes.update(dict(group.get('family_level_attribute_hints') or {}))
        if family_key:
            child_attributes['family_key'] = family_key
        if family_label:
            child_attributes['family_label'] = family_label
        if merge_group_value:
            child_attributes['merge_group'] = merge_group_value

        family_source_images = list((group.get('family_level_asset_hints') or {}).get('source_images') or [])
        child_variants: list[dict[str, Any]] = []
        for variant in list(group.get('variants') or []):
            variant_attributes = dict(variant.get('attributes') or {})
            if family_key:
                variant_attributes.setdefault('family_key', family_key)
            if family_label:
                variant_attributes.setdefault('family_label', family_label)
            variant_attributes.setdefault('variant_key', variant.get('variant_key'))
            child_variants.append({
                'variant_key': variant.get('variant_key'),
                'sku_id': variant.get('sku_id'),
                'sku_title': variant.get('sku_title'),
                'price': variant.get('price'),
                'attributes': variant_attributes,
                'source_images': list(variant.get('source_images') or family_source_images or draft.source_images or []),
            })

        child_drafts.append(NormalizedProductDraft(
            source_item_id=draft.source_item_id,
            sku_count=max(len(child_variants), int(draft.sku_count or 0)),
            source_category_ids=list(draft.source_category_ids or []),
            title=draft.title,
            description=draft.description,
            attributes=child_attributes,
            source_images=list(family_source_images or draft.source_images or []),
            provenance=dict(draft.provenance or {}),
            variants=child_variants,
            family_key=family_key,
            family_label=family_label,
            family_partition={
                'source_item_id': draft.source_item_id,
                'family_count': 1,
                'mixed_family': False,
                'split_reason_codes': list(group.get('split_reason_codes') or []),
                'family_groups': [group],
            },
        ))
    return child_drafts



def _family_source_summary(draft: NormalizedProductDraft, family_partition_stage: dict[str, Any]) -> dict[str, Any]:
    family_groups = list(family_partition_stage.get('family_groups') or [])
    total_item_count = sum(len(list(group.get('variants') or [])) for group in family_groups)
    return {
        'source_item_id': draft.source_item_id,
        'family_count': len(family_groups),
        'total_item_count': total_item_count,
        'mixed_family': bool(family_partition_stage.get('mixed_family')),
        'split_reason_codes': list(family_partition_stage.get('split_reason_codes') or []),
    }



def _family_result_summary(result: dict[str, Any], family_group: dict[str, Any], draft: NormalizedProductDraft) -> dict[str, Any]:
    payload_stage = ((result.get('stages') or {}).get('payload_build') or {})
    upload_stage = ((result.get('stages') or {}).get('upload') or {})
    terminal_stage = ((result.get('stages') or {}).get('terminal_status') or {})
    final_summary = dict(result.get('final_summary') or {})
    raw_terminal = (terminal_stage.get('final') or {}).get('raw') or {}
    raw_items = list(((raw_terminal.get('result') or {}).get('items') or []))
    product_ids = [
        str(item.get('product_id') or '').strip()
        for item in raw_items
        if str(item.get('product_id') or '').strip()
    ]
    fallback_product_id = str(final_summary.get('product_id') or '').strip()
    if not product_ids and fallback_product_id:
        product_ids = [fallback_product_id]
    payload_items = list(payload_stage.get('items') or [])
    return {
        'source_item_id': draft.source_item_id,
        'family_key': str(family_group.get('family_key') or draft.family_key or ''),
        'family_label': str(family_group.get('family_label') or draft.family_label or ''),
        'item_count': len(payload_items) or len(list(family_group.get('variants') or [])),
        'merge_group_value': str(family_group.get('merge_group_value') or ''),
        'split_reason_codes': list(family_group.get('split_reason_codes') or []),
        'payload_hash': payload_stage.get('payload_hash'),
        'task_id': (upload_stage.get('record') or {}).get('task_id'),
        'product_ids': product_ids,
        'blocked': bool(result.get('blocked')),
        'publish_status': final_summary.get('publish_status'),
        'classified_outcome': final_summary.get('classified_outcome') or ((result.get('stages') or {}).get('terminal_status') or {}).get('classified_outcome'),
    }



def _execute_post_enrichment_pipeline(
    *,
    draft: NormalizedProductDraft,
    cfg: RuntimeConfig,
    dry_run: bool,
    stub_images: bool,
    force_refresh: bool,
    poll_status: bool,
    assets_data: dict | None,
    correlation_id: str,
    batch_id: str,
    allow_auto_repair: bool = True,
) -> dict[str, Any]:
    started_at = time.time()
    browser_probe_meta = dict(draft.attributes.get('browser_probe') or draft.provenance.get('browser_probe') or {})
    reason_code = str(browser_probe_meta.get('error') or '').strip() or None
    if browser_probe_meta.get('login_required'):
        reason_code = reason_code or 'login_required'
    browser_probe_meta['reason_code'] = 'browser_probe_ready' if browser_probe_meta.get('ready') else reason_code
    browser_probe_meta['reason_label'] = _browser_probe_reason_label(reason_code, ready=bool(browser_probe_meta.get('ready')))
    family_partition_stage = draft.family_partition or _family_partition_stage(draft)
    result: dict[str, Any] = {
        'config_ready': True,
        'stages': {
            'detail_enrichment': {
                'source_item_id': draft.source_item_id,
                'mode': 'browser_probe_enriched' if browser_probe_meta.get('ready') else ('ak_fallback' if browser_probe_meta else 'ak_only'),
                'browser_probe': browser_probe_meta or None,
                'variant_count': len(draft.variants or []),
                'family_partition': family_partition_stage,
                'used_browser_probe': bool(browser_probe_meta.get('ready')),
                'fallback_used': bool(browser_probe_meta) and not bool(browser_probe_meta.get('ready')),
            },
        },
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        category_future = executor.submit(_resolve_category_with_source, draft, cfg)
        assets_future = executor.submit(
            _coerce_assets,
            assets_data,
            draft,
            stub_images,
            not dry_run,
        )

        category, category_source = category_future.result()
        assets, image_stage = assets_future.result()
    metric_gaps = _build_metric_gaps(draft)
    if metric_gaps:
        emit_progress(
            'metric_gaps',
            '当前商品仍缺少可靠重量/尺寸，返回给 agent 自行评估',
            missing_fields=metric_gaps.get('missing_fields'),
            critical_missing_fields=metric_gaps.get('critical_missing_fields'),
            non_critical_missing_fields=metric_gaps.get('non_critical_missing_fields'),
        )
    emit_progress('category_resolution', '类目解析完成', source=category_source, confidence=category.confidence, description_category_id=category.description_category_id, type_id=category.type_id)
    emit_progress('image_pipeline', '图片阶段完成', mode=image_stage.get('mode'), total_assets=getattr(assets, 'total_assets', 0))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        property_future = executor.submit(resolve_property_dictionary, draft, category, force_refresh)
        pricing_future = executor.submit(calculate_listing_price_cny, cfg, draft, category)
        property_result = property_future.result()
        pricing = pricing_future.result()
    emit_progress('property_dictionary', '属性解析完成', missing_required_count=len(((property_result.get('resolved_attributes') or {}).get('missing_required_attributes') or [])))
    emit_progress('pricing', '定价计算完成', price_cny=pricing.get('price_cny'), currency_code=pricing.get('currency_code'))

    attrs = ResolvedAttributeSet(**(property_result.get('resolved_attributes') or {}))
    gate = gate_summary(cfg, draft, category, attrs, assets)
    emit_progress('gate', '发布门禁检查完成', blocked=bool(gate.get('blocked')), issue_codes=[str(item.get('code') or '') for item in (gate.get('issues') or [])])
    required_gap = _build_required_gap_report(draft, metric_gaps, browser_probe_meta)

    result['stages'].update({
        'category_resolution': asdict(category) | {'source': category_source},
        'metric_gaps': metric_gaps,
        'property_dictionary': property_result,
        'image_pipeline': image_stage | {'asset_manifest': asdict(assets)},
        'pricing': pricing,
        'gate': gate,
        'required_gap': required_gap,
    })

    if gate['blocked'] or dry_run:
        result['blocked'] = gate['blocked']
        result['dry_run'] = dry_run
        if allow_auto_repair and not dry_run and gate['blocked']:
            codes = _issue_codes(result)
            if 'MISSING_REQUIRED_ATTRIBUTES' in codes and not force_refresh:
                repaired = _execute_post_enrichment_pipeline(
                    draft=draft,
                    cfg=cfg,
                    dry_run=dry_run,
                    stub_images=stub_images,
                    force_refresh=True,
                    poll_status=poll_status,
                    assets_data=assets_data,
                    correlation_id=correlation_id,
                    batch_id=batch_id,
                    allow_auto_repair=False,
                )
                repaired.setdefault('auto_repairs', []).append('force_refresh_property_dictionary')
                return repaired
            if 'INVALID_REMOTE_IMAGE_URLS' in codes and assets_data is not None and not stub_images:
                partial_asset_repair = _repair_invalid_asset_slots(draft, assets, result)
                if partial_asset_repair is not None:
                    repaired = _execute_post_enrichment_pipeline(
                        draft=draft,
                        cfg=cfg,
                        dry_run=dry_run,
                        stub_images=False,
                        force_refresh=force_refresh,
                        poll_status=poll_status,
                        assets_data=partial_asset_repair['assets_data'],
                        correlation_id=correlation_id,
                        batch_id=batch_id,
                        allow_auto_repair=False,
                    )
                    repaired.setdefault('auto_repairs', []).append('repair_invalid_remote_image_slots')
                    repaired.setdefault('repair_context', {})['invalid_image_slots'] = partial_asset_repair['invalid_slots']
                    repaired['repair_context']['image_slot_repair_stage'] = partial_asset_repair['repair_stage']
                    return repaired
                repaired = _execute_post_enrichment_pipeline(
                    draft=draft,
                    cfg=cfg,
                    dry_run=dry_run,
                    stub_images=False,
                    force_refresh=force_refresh,
                    poll_status=poll_status,
                    assets_data=None,
                    correlation_id=correlation_id,
                    batch_id=batch_id,
                    allow_auto_repair=False,
                )
                repaired.setdefault('auto_repairs', []).append('regenerate_assets_for_invalid_remote_urls')
                return repaired
        result['final_summary'] = _build_final_summary(draft, result)
        if required_gap is not None:
            result['final_summary']['required_gap'] = required_gap
        result['timing'] = {'elapsed_seconds': round(time.time() - started_at, 2)}
        return result

    silent_supabase = sync_category_mapping_safely(draft, category, include_verified=False)
    result['stages']['category_learning'] = silent_supabase

    payload = build_payload(cfg, draft, category, attrs, assets)
    result['stages']['payload_build'] = asdict(payload)
    emit_progress('payload_build', 'payload 构建完成', payload_hash=payload.payload_hash, item_count=len(payload.items or []))
    gate = gate_summary(cfg, draft, category, attrs, assets, payload)
    result['stages']['gate'] = gate
    if gate['blocked']:
        emit_progress('gate', 'payload 后门禁阻断', blocked=True, issue_codes=[str(item.get('code') or '') for item in (gate.get('issues') or [])])
        result['blocked'] = True
        result['final_summary'] = _build_final_summary(draft, result)
        if required_gap is not None:
            result['final_summary']['required_gap'] = required_gap
        result['timing'] = {'elapsed_seconds': round(time.time() - started_at, 2)}
        return result

    upload_result = submit_payload(payload, correlation_id, batch_id)
    result['stages']['upload'] = upload_result
    emit_progress('upload', '已提交 Ozon 导入', task_id=((upload_result.get('record') or {}).get('task_id')))
    result['blocked'] = False

    task_id = ((upload_result.get('record') or {}).get('task_id'))
    if poll_status and task_id:
        emit_progress('status_polling', '开始轮询 Ozon 导入状态', task_id=str(task_id))
        result['stages']['status_polling'] = check_task(str(task_id))
        result['stages']['terminal_status'] = wait_for_terminal_status(str(task_id))
        emit_progress('status_polling', 'Ozon 导入状态轮询完成', task_id=str(task_id), classified_outcome=((result['stages'].get('terminal_status') or {}).get('classified_outcome')))
        if allow_auto_repair and _has_retryable_attribute_error(result) and not force_refresh:
            repaired = _execute_post_enrichment_pipeline(
                draft=draft,
                cfg=cfg,
                dry_run=dry_run,
                stub_images=stub_images,
                force_refresh=True,
                poll_status=poll_status,
                assets_data=assets_data or asdict(assets),
                correlation_id=correlation_id,
                batch_id=batch_id,
                allow_auto_repair=False,
            )
            repaired.setdefault('auto_repairs', []).append('retry_after_attribute_refresh')
            return repaired
        if allow_auto_repair and _has_currency_contract_error(result):
            try:
                detected_currency = detect_contract_currency()
            except Exception:
                detected_currency = None
            if detected_currency in {'CNY', 'RUB', 'USD', 'EUR'}:
                cfg.ozon_currency = detected_currency
                try:
                    save_config(cfg)
                except Exception:
                    pass
                repaired = _execute_post_enrichment_pipeline(
                    draft=draft,
                    cfg=cfg,
                    dry_run=dry_run,
                    stub_images=stub_images,
                    force_refresh=force_refresh,
                    poll_status=poll_status,
                    assets_data=assets_data,
                    correlation_id=correlation_id,
                    batch_id=batch_id,
                    allow_auto_repair=False,
                )
                repaired.setdefault('auto_repairs', []).append('retry_after_currency_refresh')
                return repaired
    result['final_summary'] = _build_final_summary(draft, result)
    if required_gap is not None:
        result['final_summary']['required_gap'] = required_gap
    result['timing'] = {'elapsed_seconds': round(time.time() - started_at, 2)}
    return result


def orchestrate_publish_flow(
    *,
    draft_data: dict | None = None,
    query: str | None = None,
    image: str | None = None,
    url: str | None = None,
    compare_mode: bool = False,
    assets_data: dict | None = None,
    dry_run: bool = False,
    stub_images: bool = False,
    force_refresh: bool = False,
    poll_status: bool = False,
    correlation_id: str,
    batch_id: str,
) -> dict:
    return _orchestrate_publish_flow_internal(
        draft_data=draft_data,
        query=query,
        image=image,
        url=url,
        compare_mode=compare_mode,
        assets_data=assets_data,
        dry_run=dry_run,
        stub_images=stub_images,
        force_refresh=force_refresh,
        poll_status=poll_status,
        correlation_id=correlation_id,
        batch_id=batch_id,
        allow_auto_repair=True,
    )


def _orchestrate_publish_flow_internal(
    *,
    draft_data: dict | None = None,
    query: str | None = None,
    image: str | None = None,
    url: str | None = None,
    compare_mode: bool = False,
    assets_data: dict | None = None,
    dry_run: bool = False,
    stub_images: bool = False,
    force_refresh: bool = False,
    poll_status: bool = False,
    correlation_id: str,
    batch_id: str,
    allow_auto_repair: bool = True,
) -> dict:
    started_at = time.time()
    cfg, missing = preflight()
    if missing:
        raise ValidationError(f'发布流程预检失败，缺少配置: {", ".join(missing)}')

    emit_progress('preflight', '配置预检通过')
    currency_detection = resolve_ozon_currency(cfg)
    emit_progress('currency_detection', '店铺币种探测完成', detected=bool(currency_detection.get('detected')), currency_code=currency_detection.get('currency_code'))

    result: dict = {
        'config_ready': True,
        'stages': {
            'currency_detection': currency_detection,
        },
    }
    if not currency_detection.get('detected'):
        result['blocked'] = True
        result['dry_run'] = dry_run
        return result

    draft, intake = acquire_draft(
        draft_data=draft_data,
        query=query,
        image=image,
        url=url,
        compare_mode=compare_mode,
    )
    emit_progress('intake', '选品 intake 完成', source_item_id=draft.source_item_id, title=draft.title)
    detail_enrichment_stage: dict[str, Any] = {'source_item_id': draft.source_item_id, 'mode': 'not_started'}
    family_partition_stage: dict[str, Any] = draft.family_partition or _family_partition_stage(draft)

    try:
        enriched_product = enrich_product_with_detail({
            'product_id': draft.source_item_id,
            'title': draft.title,
            'price': draft.attributes.get('price'),
            'sku_id': draft.attributes.get('sku_id'),
            'sku_title': draft.attributes.get('sku_title'),
            'detail_url': draft.provenance.get('detail_url'),
            'source_raw': draft.provenance.get('source_raw') or {},
            'ranked_content': draft.attributes.get('ranked_content') or draft.provenance.get('ranked_content') or '',
            'require_logistics_metrics': True,
            'attach_trigger_hints': {
                'packaging_rows': draft.attributes.get('packaging_rows') or draft.provenance.get('packaging_rows') or [],
                'specification': draft.attributes.get('specification') or draft.provenance.get('specification') or '',
                'weight_grams': draft.attributes.get('weight_grams') or draft.provenance.get('weight_grams'),
                'dimensions_mm': draft.attributes.get('dimensions_mm') or draft.provenance.get('dimensions_mm'),
                'variants': draft.variants or draft.provenance.get('detail_variant_candidates') or [],
            },
        })
        if enriched_product.get('title'):
            draft.title = str(enriched_product.get('title') or '').strip() or draft.title
        if enriched_product.get('price') not in (None, '', []):
            draft.attributes['price'] = enriched_product.get('price')
        draft.attributes.update({
            key: value for key, value in {
                'detail_all_info': enriched_product.get('detail_all_info'),
                'detail_parsed': enriched_product.get('detail_parsed'),
                'sku_attributes': enriched_product.get('sku_attributes'),
                'cpv_attributes': enriched_product.get('cpv_attributes'),
                'merchant_info': enriched_product.get('merchant_info'),
                'selected_variant': enriched_product.get('selected_variant'),
                'selected_variant_attributes': enriched_product.get('selected_variant_attributes'),
                'weight_grams': enriched_product.get('weight_grams'),
                'brand': enriched_product.get('brand'),
                'browser_probe': enriched_product.get('browser_probe'),
                'specification': enriched_product.get('specification'),
                'dimensions_mm': enriched_product.get('dimensions_mm'),
                'packaging_rows': enriched_product.get('packaging_rows'),
                'option_groups': enriched_product.get('option_groups'),
            }.items() if value not in (None, '', [], {})
        })
        draft.provenance.update({
            key: value for key, value in {
                'detail_all_info': enriched_product.get('detail_all_info'),
                'detail_parsed': enriched_product.get('detail_parsed'),
                'detail_categories': enriched_product.get('detail_categories'),
                'merchant_info': enriched_product.get('merchant_info'),
                'detail_variant_candidates': enriched_product.get('detail_variant_candidates'),
                'browser_variant_candidates': enriched_product.get('browser_variant_candidates'),
                'browser_attributes': enriched_product.get('browser_attributes'),
                'browser_probe': enriched_product.get('browser_probe'),
                'specification': enriched_product.get('specification'),
                'dimensions_mm': enriched_product.get('dimensions_mm'),
                'packaging_rows': enriched_product.get('packaging_rows'),
                'option_groups': enriched_product.get('option_groups'),
                'source_raw': enriched_product.get('source_raw') or draft.provenance.get('source_raw'),
            }.items() if value not in (None, '', [], {})
        })
        browser_source_images = list(enriched_product.get('source_images') or [])
        if browser_source_images:
            draft.source_images = browser_source_images
        elif not draft.source_images:
            backfill = _backfill_source_images_from_ak_title_search(draft)
            if backfill:
                detail_enrichment_stage['source_image_backfill'] = backfill

        selected_variant_attributes = dict(enriched_product.get('selected_variant_attributes') or {})
        if selected_variant_attributes:
            draft.attributes.update({
                key: value
                for key, value in selected_variant_attributes.items()
                if value not in (None, '', [], {})
            })
        if enriched_product.get('variants'):
            draft.variants = list(enriched_product.get('variants') or [])
            draft.sku_count = max(draft.sku_count, len(draft.variants))
        if enriched_product.get('detail_all_info') and not draft.description:
            draft.description = str(enriched_product.get('detail_all_info') or '')
        family_partition_stage = _family_partition_stage(draft)
        browser_probe_meta = dict(enriched_product.get('browser_probe') or {})
        reason_code = str(browser_probe_meta.get('error') or '').strip() or None
        if browser_probe_meta.get('login_required'):
            reason_code = reason_code or 'login_required'
        browser_probe_meta['reason_code'] = 'browser_probe_ready' if browser_probe_meta.get('ready') else reason_code
        browser_probe_meta['reason_label'] = _browser_probe_reason_label(reason_code, ready=bool(browser_probe_meta.get('ready')))
        detail_enrichment_stage = {
            'source_item_id': draft.source_item_id,
            'mode': 'browser_probe_enriched' if browser_probe_meta.get('ready') else ('ak_fallback' if browser_probe_meta else 'ak_only'),
            'browser_probe': browser_probe_meta or None,
            'variant_count': len(draft.variants or []),
            'family_partition': family_partition_stage,
            'used_browser_probe': bool(browser_probe_meta.get('ready')),
            'fallback_used': bool(browser_probe_meta) and not bool(browser_probe_meta.get('ready')),
        }
        emit_progress('detail_enrichment', '1688 商品详情补全完成', source_item_id=draft.source_item_id, variant_count=len(draft.variants or []))
    except Exception as exc:
        family_partition_stage = draft.family_partition or _family_partition_stage(draft)
        detail_enrichment_stage = {
            'source_item_id': draft.source_item_id,
            'mode': 'error_fallback_current_intake',
            'error': str(exc),
            'fallback_used': True,
            'family_partition': family_partition_stage,
        }
        emit_progress('detail_enrichment', '1688 商品详情补全失败，继续使用当前 intake', source_item_id=draft.source_item_id, error=str(exc))

    result['stages'].update({
        'intake': intake,
        'detail_enrichment': detail_enrichment_stage,
    })

    family_groups = list(family_partition_stage.get('family_groups') or [])
    if len(family_groups) <= 1:
        downstream = _execute_post_enrichment_pipeline(
            draft=draft,
            cfg=cfg,
            dry_run=dry_run,
            stub_images=stub_images,
            force_refresh=force_refresh,
            poll_status=poll_status,
            assets_data=assets_data,
            correlation_id=correlation_id,
            batch_id=batch_id,
            allow_auto_repair=allow_auto_repair,
        )
        result['stages'].update(downstream.get('stages') or {})
        for key in ['blocked', 'dry_run', 'final_summary', 'timing', 'auto_repairs', 'repair_context', 'config_ready']:
            if key in downstream:
                result[key] = downstream[key]
        return result

    child_drafts = _family_child_drafts_from_partition(draft, family_partition_stage)
    family_jobs = [
        {
            'index': index,
            'draft': child_draft,
            'family_group': family_groups[index],
            'correlation_id': f'{correlation_id}-family-{index + 1}',
            'batch_id': f'{batch_id}-family-{index + 1}',
        }
        for index, child_draft in enumerate(child_drafts)
    ]
    max_workers = 1 if len(family_jobs) <= 1 else (2 if len(family_jobs) <= 3 else 3)

    def _run_family(job: dict[str, Any]) -> dict[str, Any]:
        child_draft: NormalizedProductDraft = job['draft']
        family_group = job['family_group']
        try:
            child_result = _execute_post_enrichment_pipeline(
                draft=child_draft,
                cfg=cfg,
                dry_run=dry_run,
                stub_images=stub_images,
                force_refresh=force_refresh,
                poll_status=poll_status,
                assets_data=assets_data,
                correlation_id=job['correlation_id'],
                batch_id=job['batch_id'],
                allow_auto_repair=allow_auto_repair,
            )
            child_result['family_key'] = child_draft.family_key
            child_result['family_label'] = child_draft.family_label
            child_result['family_group'] = family_group
            child_result['source_item_id'] = child_draft.source_item_id
            return {
                'index': job['index'],
                'family_key': child_draft.family_key,
                'family_label': child_draft.family_label,
                'family_group': family_group,
                'result': child_result,
                'summary': _family_result_summary(child_result, family_group, child_draft),
                'blocked': bool(child_result.get('blocked')),
                'success': not bool(child_result.get('blocked')),
            }
        except Exception as exc:
            summary = {
                'source_item_id': child_draft.source_item_id,
                'family_key': child_draft.family_key,
                'family_label': child_draft.family_label,
                'item_count': len(list(family_group.get('variants') or [])),
                'merge_group_value': str(family_group.get('merge_group_value') or ''),
                'split_reason_codes': list(family_group.get('split_reason_codes') or []),
                'payload_hash': None,
                'task_id': None,
                'product_ids': [],
                'blocked': True,
                'publish_status': 'error',
                'classified_outcome': 'blocked',
            }
            return {
                'index': job['index'],
                'family_key': child_draft.family_key,
                'family_label': child_draft.family_label,
                'family_group': family_group,
                'summary': summary,
                'blocked': True,
                'success': False,
                'error': str(exc),
                'error_type': type(exc).__name__,
            }

    family_results: list[dict[str, Any]] = []
    if max_workers == 1:
        for job in family_jobs:
            family_results.append(_run_family(job))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for item in executor.map(_run_family, family_jobs):
                family_results.append(item)
        family_results.sort(key=lambda item: int(item.get('index', 0)))

    family_summaries = [dict(item.get('summary') or {}) for item in family_results]
    source_summary = _family_source_summary(draft, family_partition_stage)
    source_summary['success_count'] = sum(1 for item in family_results if item.get('success'))
    source_summary['blocked_count'] = sum(1 for item in family_results if item.get('blocked'))
    source_summary['family_result_count'] = len(family_results)

    result['family_results'] = [dict(item.get('result') or item) for item in family_results]
    result['family_summaries'] = family_summaries
    result['source_summary'] = source_summary
    result['blocked'] = any(item.get('blocked') for item in family_results)
    result['dry_run'] = dry_run
    result['timing'] = {'elapsed_seconds': round(time.time() - started_at, 2)}
    result['stages']['family_partition'] = family_partition_stage
    return result


def orchestrate_publish_flow_batch(
    *,
    drafts_data: list[dict[str, Any]],
    force_refresh: bool = False,
    poll_status: bool = False,
    correlation_id_prefix: str,
    batch_id: str,
    max_workers: int | None = 0,
) -> dict[str, Any]:
    if not drafts_data:
        raise ValidationError('批量发布至少需要 1 个 draft')

    requested_max_workers = max_workers

    def _resolve_batch_workers(total: int, requested: int | None) -> int:
        if requested not in (None, 0):
            return max(1, min(int(requested), 3))
        if total <= 1:
            return 1
        if total <= 3:
            return 2
        return 3

    max_workers = _resolve_batch_workers(len(drafts_data), requested_max_workers)
    jobs = [
        {
            'index': index,
            'draft_data': draft_data,
            'correlation_id': f'{correlation_id_prefix}-{index + 1}',
            'item_batch_id': f'{batch_id}-{index + 1}',
        }
        for index, draft_data in enumerate(drafts_data)
    ]

    def _run(job: dict[str, Any]) -> dict[str, Any]:
        draft = job['draft_data']
        try:
            result = orchestrate_publish_flow(
                draft_data=draft,
                dry_run=False,
                stub_images=False,
                force_refresh=force_refresh,
                poll_status=poll_status,
                correlation_id=job['correlation_id'],
                batch_id=job['item_batch_id'],
            )
            return {
                'index': job['index'],
                'source_item_id': draft.get('source_item_id'),
                'success': not bool(result.get('blocked')),
                'blocked': bool(result.get('blocked')),
                'queue_status': 'completed' if not bool(result.get('blocked')) else 'blocked',
                'final_summary': result.get('final_summary'),
                'result': result,
            }
        except Exception as exc:
            return {
                'index': job['index'],
                'source_item_id': draft.get('source_item_id'),
                'success': False,
                'blocked': True,
                'queue_status': 'failed',
                'error': str(exc),
                'error_type': type(exc).__name__,
            }

    items: list[dict[str, Any]] = []
    if max_workers == 1:
        for job in jobs:
            items.append(_run(job))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for item in executor.map(_run, jobs):
                items.append(item)
        items.sort(key=lambda item: int(item.get('index', 0)))

    success_count = sum(1 for item in items if item.get('success'))
    blocked_count = sum(1 for item in items if item.get('blocked'))
    return {
        'batch_id': batch_id,
        'total': len(items),
        'success_count': success_count,
        'blocked_count': blocked_count,
        'failed_count': sum(1 for item in items if item.get('queue_status') == 'failed'),
        'queue_mode': 'serial' if max_workers == 1 else 'parallel',
        'max_workers': max_workers,
        'requested_max_workers': requested_max_workers,
        'queue_strategy': 'auto_2_to_3_parallel' if requested_max_workers in (None, 0) else 'manual_clamped',
        'items': items,
    }
