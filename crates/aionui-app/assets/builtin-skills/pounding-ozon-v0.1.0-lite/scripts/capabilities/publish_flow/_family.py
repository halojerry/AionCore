#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from models.contracts import NormalizedProductDraft
from lib.family_partition import family_partition_summary, partition_families


def _family_partition_stage(draft: NormalizedProductDraft) -> dict[str, Any]:
    partition = partition_families(draft)
    summary = family_partition_summary(partition)
    draft.family_partition = summary
    if summary.get('family_groups'):
        first_group = summary['family_groups'][0]
        draft.family_key = str(first_group.get('family_key') or '') or None
        draft.family_label = str(first_group.get('family_label') or '') or None
    return summary


def _family_child_drafts_from_partition(
    draft: NormalizedProductDraft,
    family_partition_stage: dict[str, Any],
) -> list[NormalizedProductDraft]:
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


def _family_result_summary(
    result: dict[str, Any],
    family_group: dict[str, Any],
    draft: NormalizedProductDraft,
) -> dict[str, Any]:
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
