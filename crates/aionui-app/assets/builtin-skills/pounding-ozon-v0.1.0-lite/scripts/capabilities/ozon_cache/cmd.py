#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _const import resolve_input_path
from _errors import SkillError
from _output import print_failure, print_success
from capabilities.ozon_cache.service import (
    compact_shared_dictionary_aliases,
    fetch_all_dictionary_values,
    get_category_cache,
    get_category_tree,
    get_properties,
    get_tree_leaf_pairs,
    merge_category_mappings,
    prewarm_dictionary_values,
    prewarm_all_properties,
    warm_category_cache,
    sync_category_cache_to_supabase,
    export_cache_manifest,
    export_database_seed,
)

COMMAND_NAME = 'ozon_cache'
COMMAND_DESC = '本地 Ozon metadata cache 管理'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='Ozon cache 管理')
    sub = parser.add_subparsers(dest='target')
    sub.add_parser('status')
    p_tree = sub.add_parser('tree')
    p_tree.add_argument('--language', default='ZH_HANS')
    p_tree.add_argument('--force-refresh', action='store_true')
    p_leaf = sub.add_parser('leaf_pairs')
    p_leaf.add_argument('--language', default='ZH_HANS')
    p_leaf.add_argument('--force-refresh-tree', action='store_true')
    p_prewarm = sub.add_parser('prewarm_properties')
    p_prewarm.add_argument('--language', default='ZH_HANS')
    p_prewarm.add_argument('--force-refresh-tree', action='store_true')
    p_prewarm.add_argument('--force-refresh-properties', action='store_true')
    p_prewarm.add_argument('--include-disabled', action='store_true')
    p_prewarm.add_argument('--limit', type=int, default=None)
    p_prewarm.add_argument('--max-workers', type=int, default=8)
    p_prewarm.add_argument('--retries', type=int, default=2)
    p_prewarm_dict = sub.add_parser('prewarm_dictionaries')
    p_prewarm_dict.add_argument('--language', default='ZH_HANS')
    p_prewarm_dict.add_argument('--force-refresh-tree', action='store_true')
    p_prewarm_dict.add_argument('--force-refresh-properties', action='store_true')
    p_prewarm_dict.add_argument('--force-refresh-dictionaries', action='store_true')
    p_prewarm_dict.add_argument('--include-disabled', action='store_true')
    p_prewarm_dict.add_argument('--category-limit', type=int, default=None)
    p_prewarm_dict.add_argument('--dictionary-limit', type=int, default=None)
    p_prewarm_dict.add_argument('--max-workers', type=int, default=8)
    p_prewarm_dict.add_argument('--retries', type=int, default=2)
    p_compact_dict = sub.add_parser('compact_dictionaries')
    p_compact_dict.add_argument('--language', default='ZH_HANS')
    p_warm = sub.add_parser('warm_categories')
    p_warm.add_argument('--file', required=True, help='包含 entries 数组的 JSON 文件')
    p_merge = sub.add_parser('merge_categories')
    p_merge.add_argument('--file', required=True, help='包含 entries 数组的 JSON 文件')
    p_upsert = sub.add_parser('upsert_category')
    p_upsert.add_argument('--source-category-id', required=True)
    p_upsert.add_argument('--description-category-id', required=True)
    p_upsert.add_argument('--type-id', required=True)
    p_upsert.add_argument('--confidence', type=float, default=0.99)
    sub.add_parser('sync_categories_supabase')
    p_manifest = sub.add_parser('export_manifest')
    p_manifest.add_argument('--output', default=None, help='可选，输出 JSON 文件路径')
    p_seed = sub.add_parser('export_database_seed')
    p_seed.add_argument('--output-dir', required=True, help='结构化种子数据导出目录')
    p_props = sub.add_parser('properties')
    p_props.add_argument('--description-category-id', required=True)
    p_props.add_argument('--type-id', required=True)
    p_props.add_argument('--force-refresh', action='store_true')
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        if not parsed.target or parsed.target == 'status':
            print_success('当前 Ozon category cache 状态', get_category_cache())
            return 0
        if parsed.target == 'tree':
            print_success('Ozon 类目树已获取', get_category_tree(parsed.language, parsed.force_refresh))
            return 0
        if parsed.target == 'leaf_pairs':
            print_success('Ozon 叶子类目对已提取', {
                'items': get_tree_leaf_pairs(force_refresh_tree=parsed.force_refresh_tree, language=parsed.language)
            })
            return 0
        if parsed.target == 'prewarm_properties':
            print_success('Ozon 属性全量预热完成', prewarm_all_properties(
                force_refresh_tree=parsed.force_refresh_tree,
                force_refresh_properties=parsed.force_refresh_properties,
                include_disabled=parsed.include_disabled,
                language=parsed.language,
                limit=parsed.limit,
                max_workers=parsed.max_workers,
                retries=parsed.retries,
            ))
            return 0
        if parsed.target == 'prewarm_dictionaries':
            print_success('Ozon 字典值全量预热完成', prewarm_dictionary_values(
                language=parsed.language,
                force_refresh_tree=parsed.force_refresh_tree,
                force_refresh_properties=parsed.force_refresh_properties,
                force_refresh_dictionaries=parsed.force_refresh_dictionaries,
                include_disabled=parsed.include_disabled,
                category_limit=parsed.category_limit,
                dictionary_limit=parsed.dictionary_limit,
                max_workers=parsed.max_workers,
                retries=parsed.retries,
            ))
            return 0
        if parsed.target == 'compact_dictionaries':
            print_success('Ozon 字典缓存压缩完成', compact_shared_dictionary_aliases(
                language=parsed.language,
            ))
            return 0
        if parsed.target == 'warm_categories':
            import json
            payload = json.loads(resolve_input_path(parsed.file, must_exist=True).read_text(encoding='utf-8'))
            print_success('category cache 已写入', warm_category_cache(payload.get('entries', [])))
            return 0
        if parsed.target == 'merge_categories':
            import json
            payload = json.loads(resolve_input_path(parsed.file, must_exist=True).read_text(encoding='utf-8'))
            print_success('category cache 已合并', merge_category_mappings(payload.get('entries', [])))
            return 0
        if parsed.target == 'upsert_category':
            print_success('category cache 单条映射已写入', merge_category_mappings([{
                'source_category_id': parsed.source_category_id,
                'description_category_id': parsed.description_category_id,
                'type_id': parsed.type_id,
                'confidence': parsed.confidence,
            }]))
            return 0
        if parsed.target == 'sync_categories_supabase':
            print_success('category cache 已同步到 Supabase', sync_category_cache_to_supabase())
            return 0
        if parsed.target == 'export_manifest':
            print_success('Ozon cache 资产清单已导出', export_cache_manifest(str(resolve_input_path(parsed.output)) if parsed.output else None))
            return 0
        if parsed.target == 'export_database_seed':
            print_success('Ozon cache 数据库种子已导出', export_database_seed(str(resolve_input_path(parsed.output_dir))))
            return 0
        if parsed.target == 'properties':
            data = get_properties(parsed.description_category_id, parsed.type_id, parsed.force_refresh)
            print_success('Ozon 属性已获取', data)
            return 0
        print_failure('未知 cache 操作', error_code='UNKNOWN_OZON_CACHE_COMMAND')
        return 1
    except SkillError as exc:
        print_failure(f'❌ Ozon cache 失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ Ozon cache 失败：{exc}', error_code='OZON_CACHE_UNEXPECTED')
        return 1
