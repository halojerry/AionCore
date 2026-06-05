#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import time
from dataclasses import asdict
from typing import Any

from _errors import ValidationError
from capabilities.category_resolution.service import resolve_category
from capabilities.ozon_cache.service import get_category_tree
from capabilities.image_pipeline.service import build_stub_manifest, execute_image_pipeline, plan_image_pipeline, repair_image_pipeline_slots
from capabilities.property_dictionary.service import resolve_property_dictionary
from capabilities.status.service import check_task, wait_for_terminal_status
from capabilities.upload.service import submit_payload
from lib.config_store import load_config, save_config
from lib.payload_builder import build_payload
from lib.pricing import calculate_listing_price_cny
from lib.progress import emit_progress
from lib.supabase_client import has_supabase_config, resolve_category_from_supabase, sync_category_mapping_safely
from lib.publish_gate import gate_summary
from lib.cache_store import read_category_cache, read_category_tree_cache
from lib.image_manifest_builder import OZON_UPLOAD_SLOT_ORDER, PRIMARY_SLOT, manifest_slot_records
from lib.ozon_wrappers import detect_contract_currency
from models.contracts import AssetManifest, CategoryResolution, NormalizedProductDraft, ResolvedAttributeSet, RuntimeConfig
from ._summary import _build_final_summary, _issue_codes, _has_currency_contract_error, _has_retryable_attribute_error, _invalid_remote_image_slots
from ._family import _family_partition_stage, _family_child_drafts_from_partition, _family_source_summary, _family_result_summary


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

    # --- Phase 1: category + property (no image API) ---
    category, category_source = _resolve_category_with_source(draft, cfg)

    metric_gaps = _build_metric_gaps(draft)
    if metric_gaps:
        emit_progress(
            'metric_gaps',
            '当前商品仍缺少可靠重量/尺寸，返回给 agent 自行评估',
            missing_fields=metric_gaps.get('missing_fields'),
            critical_missing_fields=metric_gaps.get('critical_missing_fields'),
            non_critical_missing_fields=metric_gaps.get('non_critical_missing_fields'),
        )
    emit_progress('category_resolution', '类目解析完成', source=category_source, confidence=category.confidence,
                  description_category_id=category.description_category_id, type_id=category.type_id)

    property_result = resolve_property_dictionary(draft, category, force_refresh)
    emit_progress('property_dictionary', '属性解析完成',
                  missing_required_count=len(((property_result.get('resolved_attributes') or {}).get('missing_required_attributes') or [])))

    attrs = ResolvedAttributeSet(**(property_result.get('resolved_attributes') or {}))

    # --- Phase 2: early gate check (empty assets to detect required-attribute issues) ---
    empty_assets = AssetManifest()
    gate = gate_summary(cfg, draft, category, attrs, empty_assets)
    required_gap = _build_required_gap_report(draft, metric_gaps, browser_probe_meta)

    result['stages'].update({
        'category_resolution': asdict(category) | {'source': category_source},
        'metric_gaps': metric_gaps,
        'property_dictionary': property_result,
        'gate': gate,
        'required_gap': required_gap,
    })

    # If gate blocks on required attributes, skip image generation entirely
    early_blocked = gate['blocked'] and bool({'MISSING_REQUIRED_ATTRIBUTES', 'MISSING_REQUIRED_METADATA'} & {str(i.get('code')) for i in (gate.get('issues') or [])})

    if early_blocked or dry_run:
        result['blocked'] = gate['blocked']
        result['dry_run'] = dry_run
        result['stages']['image_pipeline'] = {'mode': 'skipped_early_gate', 'skipped_because': 'required_attributes_missing', 'asset_manifest': asdict(empty_assets)}
        result['stages']['pricing'] = {}
        result['final_summary'] = _build_final_summary(draft, result)
        if required_gap is not None:
            result['final_summary']['required_gap'] = required_gap
        result['timing'] = {'elapsed_seconds': round(time.time() - started_at, 2)}
        return result

    # --- Phase 3: pricing + image generation (parallel, now safe because gate won't block) ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        assets_future = executor.submit(
            _coerce_assets,
            assets_data,
            draft,
            stub_images,
            not dry_run,
        )
        pricing_future = executor.submit(calculate_listing_price_cny, cfg, draft, category)
        assets, image_stage = assets_future.result()
        pricing = pricing_future.result()

    emit_progress('image_pipeline', '图片阶段完成', mode=image_stage.get('mode'), total_assets=getattr(assets, 'total_assets', 0))
    emit_progress('pricing', '定价计算完成', price_cny=pricing.get('price_cny'), currency_code=pricing.get('currency_code'))

    # --- Phase 4: full gate with real assets ---
    gate = gate_summary(cfg, draft, category, attrs, assets)
    emit_progress('gate', '发布门禁检查完成', blocked=bool(gate.get('blocked')),
                  issue_codes=[str(item.get('code') or '') for item in (gate.get('issues') or [])])

    result['stages'].update({
        'image_pipeline': image_stage | {'asset_manifest': asdict(assets)},
        'pricing': pricing,
        'gate': gate,
    })

    if gate['blocked'] or dry_run:
        result['blocked'] = gate['blocked']
        result['dry_run'] = dry_run
        if allow_auto_repair and not dry_run and gate['blocked']:
            codes = _issue_codes(result)
            if 'MISSING_REQUIRED_ATTRIBUTES' in codes and not force_refresh:
                repaired = _execute_post_enrichment_pipeline(
                    draft=draft, cfg=cfg, dry_run=dry_run, stub_images=stub_images,
                    force_refresh=True, poll_status=poll_status, assets_data=assets_data,
                    correlation_id=correlation_id, batch_id=batch_id, allow_auto_repair=False,
                )
                repaired.setdefault('auto_repairs', []).append('force_refresh_property_dictionary')
                return repaired
            if 'INVALID_REMOTE_IMAGE_URLS' in codes and assets_data is not None and not stub_images:
                partial_asset_repair = _repair_invalid_asset_slots(draft, assets, result)
                if partial_asset_repair is not None:
                    repaired = _execute_post_enrichment_pipeline(
                        draft=draft, cfg=cfg, dry_run=dry_run, stub_images=False,
                        force_refresh=force_refresh, poll_status=poll_status,
                        assets_data=partial_asset_repair['assets_data'],
                        correlation_id=correlation_id, batch_id=batch_id, allow_auto_repair=False,
                    )
                    repaired.setdefault('auto_repairs', []).append('repair_invalid_remote_image_slots')
                    repaired.setdefault('repair_context', {})['invalid_image_slots'] = partial_asset_repair['invalid_slots']
                    repaired['repair_context']['image_slot_repair_stage'] = partial_asset_repair['repair_stage']
                    return repaired
                repaired = _execute_post_enrichment_pipeline(
                    draft=draft, cfg=cfg, dry_run=dry_run, stub_images=False,
                    force_refresh=force_refresh, poll_status=poll_status,
                    assets_data=None, correlation_id=correlation_id, batch_id=batch_id,
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
        emit_progress('gate', 'payload 后门禁阻断', blocked=True,
                      issue_codes=[str(item.get('code') or '') for item in (gate.get('issues') or [])])
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
        emit_progress('status_polling', 'Ozon 导入状态轮询完成', task_id=str(task_id),
                      classified_outcome=((result['stages'].get('terminal_status') or {}).get('classified_outcome')))
        if allow_auto_repair and _has_retryable_attribute_error(result) and not force_refresh:
            repaired = _execute_post_enrichment_pipeline(
                draft=draft, cfg=cfg, dry_run=dry_run, stub_images=stub_images,
                force_refresh=True, poll_status=poll_status,
                assets_data=assets_data or asdict(assets),
                correlation_id=correlation_id, batch_id=batch_id, allow_auto_repair=False,
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
                    draft=draft, cfg=cfg, dry_run=dry_run, stub_images=stub_images,
                    force_refresh=force_refresh, poll_status=poll_status,
                    assets_data=assets_data, correlation_id=correlation_id, batch_id=batch_id,
                    allow_auto_repair=False,
                )
                repaired.setdefault('auto_repairs', []).append('retry_after_currency_refresh')
                return repaired
    result['final_summary'] = _build_final_summary(draft, result)
    if required_gap is not None:
        result['final_summary']['required_gap'] = required_gap
    result['timing'] = {'elapsed_seconds': round(time.time() - started_at, 2)}
    return result
