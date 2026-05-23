#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from dataclasses import asdict
from typing import Any

from _errors import ValidationError
from lib.attribute_resolver import resolve_attributes
from lib.cache_store import (
    cache_record_fresh,
    dictionary_cache_path,
    property_cache_path,
    read_cache_record,
    write_cache_record,
)
from lib.ozon_wrappers import query_dictionary_values, query_ozon_properties
from models.contracts import CategoryResolution, NormalizedProductDraft, ResolvedAttributeSet


def _dictionary_mode(search: str | None) -> str:
    if not search:
        return 'list'
    digest = hashlib.sha1(search.strip().lower().encode('utf-8')).hexdigest()[:12]
    return f'search-{digest}'


def _get_properties(description_category_id: str, type_id: str, force_refresh: bool = False) -> dict[str, Any]:
    path = property_cache_path(description_category_id, type_id)
    cached = read_cache_record(path)
    if cached and not force_refresh and cache_record_fresh(cached):
        return {'source': 'cache', **cached}
    data = query_ozon_properties(description_category_id, type_id)
    record = write_cache_record(path, data)
    return {'source': 'live', **record}


def _get_dictionary_values(
    attribute_id: str,
    description_category_id: str,
    type_id: str,
    search: str | None = None,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    mode = _dictionary_mode(search)
    path = dictionary_cache_path(attribute_id, description_category_id, type_id, mode)
    cached = read_cache_record(path)
    if cached and not force_refresh and cache_record_fresh(cached):
        return list(cached.get('data') or [])
    try:
        data = query_dictionary_values(
            int(attribute_id),
            int(description_category_id),
            int(type_id),
            search=search,
            limit=50,
        )
    except Exception:
        return list(cached.get('data') or []) if cached else []
    write_cache_record(path, data)
    return data


def resolve_property_dictionary(
    draft: NormalizedProductDraft,
    category: CategoryResolution,
    force_refresh: bool = False,
) -> dict[str, Any]:
    if not category.description_category_id or not category.type_id:
        raise ValidationError('缺少有效类目解析结果，不能进入属性/字典值解析')
    prop_record = _get_properties(
        str(category.description_category_id),
        str(category.type_id),
        force_refresh=force_refresh,
    )
    properties = list(prop_record.get('data') or [])

    def lookup(attribute_id: str, search: str | None) -> list[dict[str, Any]]:
        try:
            return _get_dictionary_values(
                attribute_id,
                str(category.description_category_id),
                str(category.type_id),
                search=search,
                force_refresh=force_refresh,
            )
        except Exception:
            return []

    enriched_draft = NormalizedProductDraft(
        source_item_id=draft.source_item_id,
        sku_count=draft.sku_count,
        source_category_ids=list(draft.source_category_ids),
        title=draft.title,
        description=draft.description,
        attributes={
            **dict(draft.attributes or {}),
            'ozon_type_id': str(category.type_id),
            'ozon_description_category_id': str(category.description_category_id),
        },
        source_images=list(draft.source_images or []),
        provenance={
            **dict(draft.provenance or {}),
            'ozon_type_id': str(category.type_id),
            'ozon_description_category_id': str(category.description_category_id),
        },
    )

    resolved: ResolvedAttributeSet = resolve_attributes(enriched_draft, properties, lookup)
    return {
        'properties_source': prop_record.get('source'),
        'properties_count': len(properties),
        'resolved_attributes': asdict(resolved),
    }
