#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _const import resolve_input_path
from _errors import SkillError
from _output import print_failure, print_success
from capabilities.category_resolution.service import resolve_category
from lib.cache_store import merge_category_cache_entries, read_category_cache
from lib.product_semantics import detect_product_family
from lib.supabase_client import sync_category_mapping_safely
from models.contracts import CategoryResolution, NormalizedProductDraft

COMMAND_NAME = 'category_resolution'
COMMAND_DESC = '本地 Ozon 类目解析（骨架版）'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='类目解析')
    parser.add_argument('--draft-file', required=True, help='Normalized draft JSON 文件')
    parser.add_argument('--persist-category-file', help='已确认的 CategoryResolution JSON 文件；提供后会把 draft 的 source_category_ids 写入本地映射库')
    parser.add_argument('--persist-confidence', type=float, default=None, help='可选，覆盖持久化映射的 confidence')
    parser.add_argument('--sync-supabase', action='store_true', help='将确认的映射同步到 Supabase observation/verified 表')
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        raw = json.loads(resolve_input_path(parsed.draft_file, must_exist=True).read_text(encoding='utf-8'))
        draft = NormalizedProductDraft(**raw)
        if parsed.persist_category_file:
            category_raw = json.loads(resolve_input_path(parsed.persist_category_file, must_exist=True).read_text(encoding='utf-8'))
            category = CategoryResolution(**category_raw)
            entries = []
            confidence = parsed.persist_confidence if parsed.persist_confidence is not None else category.confidence
            for source_category_id in draft.source_category_ids:
                entries.append({
                    'source_category_id': str(source_category_id),
                    'description_category_id': str(category.description_category_id),
                    'type_id': str(category.type_id),
                    'confidence': float(confidence),
                    'product_family': detect_product_family(draft),
                })
            payload = merge_category_cache_entries(entries)
            supabase_result: dict | None = None
            if parsed.sync_supabase:
                supabase_result = sync_category_mapping_safely(draft, category, include_verified=True)
            print_success('类目映射已写入本地 cache', {
                'written_entries': entries,
                'category_cache_size': len(payload.get('entries') or []),
                'supabase': supabase_result,
            })
            return 0
        cache = read_category_cache()
        resolution = resolve_category(draft, cache.get('entries', []))
        print_success('类目解析完成', {
            'description_category_id': resolution.description_category_id,
            'type_id': resolution.type_id,
            'confidence': resolution.confidence,
            'top_candidates': resolution.top_candidates,
            'explanation': resolution.explanation,
        })
        return 0
    except SkillError as exc:
        print_failure(f'❌ 类目解析失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ 类目解析失败：{exc}', error_code='CATEGORY_RESOLUTION_UNEXPECTED')
        return 1
