#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
import time
from pathlib import Path
from typing import Any

from lib.cache_store import (
    cache_record_fresh,
    category_cache_fresh,
    dictionary_cache_path,
    DICTIONARIES_DIR,
    CATEGORY_CACHE_FILE,
    PROPERTIES_DIR,
    TREE_CACHE_FILE,
    property_cache_path,
    PREWARM_REPORTS_DIR,
    read_cache_record,
    read_category_cache,
    read_category_tree_cache,
    merge_category_cache_entries,
    SHARED_DICTIONARIES_DIR,
    write_cache_record,
    write_cache_reference_record,
    write_cache_symlink,
    write_category_cache,
    write_category_tree_cache,
    shared_dictionary_cache_path,
)
from _const import resolve_input_path
from lib.ozon_wrappers import list_dictionary_values_page, query_category_tree, query_ozon_properties
from lib.supabase_client import has_supabase_service_role, upsert_verified_category_entries


def get_category_cache() -> dict[str, Any]:
    return read_category_cache()


def warm_category_cache(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return write_category_cache(entries)


def merge_category_mappings(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return merge_category_cache_entries(entries)


def get_category_tree(language: str = 'ZH_HANS', force_refresh: bool = False) -> dict[str, Any]:
    cached = read_category_tree_cache()
    if cached.get('result') and not force_refresh and cache_record_fresh(cached):
        return {'source': 'cache', **cached}
    result = query_category_tree(language=language)
    record = write_category_tree_cache(result, language=language)
    return {'source': 'live', **record}


def get_properties(description_category_id: str, type_id: str, force_refresh: bool = False) -> dict[str, Any]:
    path = property_cache_path(description_category_id, type_id)
    cached = read_cache_record(path)
    if cached and not force_refresh and cache_record_fresh(cached):
        return {'source': 'cache', **cached}
    data = query_ozon_properties(description_category_id, type_id)
    record = write_cache_record(path, data)
    return {'source': 'live', **record}


def _collect_tree_leaf_pairs(nodes: list[dict[str, Any]], parent_category_id: int | None = None) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for node in nodes or []:
        current_category_id = node.get('description_category_id', parent_category_id)
        current_category_name = node.get('category_name')
        children = node.get('children') or []
        if node.get('type_id') is not None:
            pairs.append({
                'description_category_id': str(parent_category_id if parent_category_id is not None else current_category_id),
                'type_id': str(node.get('type_id')),
                'type_name': node.get('type_name'),
                'category_name': current_category_name,
                'disabled': bool(node.get('disabled')),
            })
        if children:
            pairs.extend(_collect_tree_leaf_pairs(children, current_category_id))
    return pairs


def get_tree_leaf_pairs(force_refresh_tree: bool = False, language: str = 'ZH_HANS') -> list[dict[str, Any]]:
    tree = get_category_tree(language=language, force_refresh=force_refresh_tree)
    pairs = _collect_tree_leaf_pairs(tree.get('result') or [])
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for pair in pairs:
        key = (pair['description_category_id'], pair['type_id'])
        if key in seen:
            continue
        seen.add(key)
        unique.append(pair)
    return unique


def _property_cache_is_usable(description_category_id: str, type_id: str) -> bool:
    path = property_cache_path(description_category_id, type_id)
    return cache_record_fresh(read_cache_record(path))


def _dictionary_cache_is_usable(attribute_id: str, description_category_id: str, type_id: str, language: str) -> bool:
    path = dictionary_cache_path(attribute_id, description_category_id, type_id, _dictionary_cache_mode_all(language))
    return cache_record_fresh(read_cache_record(path))


def _retry_call(fn, retries: int, retry_delay_seconds: float):
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover
            last_exc = exc
            if attempt >= retries:
                raise
            time.sleep(retry_delay_seconds * (attempt + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError('unexpected retry state')


def _write_cache_record_auto(path, data, *, version: int = 1, compress: bool = False):
    try:
        return write_cache_record(path, data, version=version, compress=compress)
    except TypeError:
        return write_cache_record(path, data, version=version)


def _select_property_pairs(
    force_refresh_tree: bool = False,
    include_disabled: bool = False,
    language: str = 'ZH_HANS',
    limit: int | None = None,
) -> list[dict[str, Any]]:
    pairs = get_tree_leaf_pairs(force_refresh_tree=force_refresh_tree, language=language)
    if not include_disabled:
        pairs = [pair for pair in pairs if not pair.get('disabled')]
    if limit is not None:
        pairs = pairs[:limit]
    return pairs


def _load_dictionary_targets_from_property_pairs(
    pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    dictionary_targets: list[dict[str, Any]] = []
    for pair in pairs:
        path = property_cache_path(pair['description_category_id'], pair['type_id'])
        record = read_cache_record(path) or {}
        for attr in (record.get('data') or []):
            dictionary_id = int(attr.get('dictionary_id') or 0)
            if dictionary_id == 0:
                continue
            dictionary_targets.append({
                'description_category_id': pair['description_category_id'],
                'type_id': pair['type_id'],
                'attribute_id': str(attr.get('id')),
                'attribute_name': attr.get('name'),
                'dictionary_id': dictionary_id,
                'category_dependent': bool(attr.get('category_dependent')),
            })
    unique_targets: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for target in dictionary_targets:
        key = (target['description_category_id'], target['type_id'], target['attribute_id'])
        if key in seen:
            continue
        seen.add(key)
        unique_targets.append(target)
    return unique_targets


def _group_dictionary_targets(unique_targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str] | tuple[str, str, str], dict[str, Any]] = {}
    for target in unique_targets:
        if target.get('category_dependent'):
            key: tuple[str, str] | tuple[str, str, str] = (
                target['attribute_id'],
                target['description_category_id'],
                target['type_id'],
            )
        else:
            key = (target['attribute_id'], str(target.get('dictionary_id')))
        bucket = groups.get(key)
        if not bucket:
            bucket = {
                'key': key,
                'attribute_id': target['attribute_id'],
                'attribute_name': target.get('attribute_name'),
                'dictionary_id': target.get('dictionary_id'),
                'category_dependent': bool(target.get('category_dependent')),
                'seed_description_category_id': target['description_category_id'],
                'seed_type_id': target['type_id'],
                'targets': [],
            }
            groups[key] = bucket
        bucket['targets'].append(target)
    return list(groups.values())


def _write_dictionary_alias_records(
    targets: list[dict[str, Any]],
    language: str,
    data: list[dict[str, Any]],
    shared_path: str | None = None,
) -> None:
    mode = _dictionary_cache_mode_all(language)
    for target in targets:
        path = dictionary_cache_path(
            target['attribute_id'],
            target['description_category_id'],
            target['type_id'],
            mode,
        )
        if cache_record_fresh(read_cache_record(path)):
            continue
        if shared_path:
            try:
                write_cache_symlink(path, Path(shared_path))
            except Exception:
                write_cache_reference_record(
                    path,
                    shared_path,
                    extra={
                        'attribute_id': target['attribute_id'],
                        'description_category_id': target['description_category_id'],
                        'type_id': target['type_id'],
                        'mode': mode,
                    },
                )
        else:
            write_cache_record(path, data)


def _write_dictionary_group_cache(
    group: dict[str, Any],
    language: str,
    data: list[dict[str, Any]],
) -> None:
    if not group.get('category_dependent'):
        shared_path = shared_dictionary_cache_path(
            group['attribute_id'],
            str(group.get('dictionary_id')),
            language,
        )
        _write_cache_record_auto(shared_path, data, compress=True)
        _write_dictionary_alias_records(group['targets'], language, data, shared_path=str(shared_path))
        return
    for target in group.get('targets') or []:
        path = dictionary_cache_path(
            target['attribute_id'],
            target['description_category_id'],
            target['type_id'],
            _dictionary_cache_mode_all(language),
        )
        if cache_record_fresh(read_cache_record(path)):
            continue
        _write_cache_record_auto(path, data, compress=True)


def _dictionary_cache_mode_all(language: str) -> str:
    return f'all-{language.lower()}'


def fetch_all_dictionary_values(
    attribute_id: str,
    description_category_id: str,
    type_id: str,
    *,
    language: str = 'ZH_HANS',
    force_refresh: bool = False,
) -> dict[str, Any]:
    mode = _dictionary_cache_mode_all(language)
    path = dictionary_cache_path(attribute_id, description_category_id, type_id, mode)
    cached = read_cache_record(path)
    if cached and not force_refresh and cache_record_fresh(cached):
        return {
            'source': 'cache',
            'data': list(cached.get('data') or []),
            'page_count': 1,
        }

    results: list[dict[str, Any]] = []
    has_next = True
    last_value_id = 0
    page_count = 0
    while has_next:
        page = list_dictionary_values_page(
            attribute_id,
            description_category_id,
            type_id,
            last_value_id=last_value_id,
            limit=2000,
            language=language,
        )
        page_count += 1
        values = list(page.get('result') or [])
        results.extend(values)
        has_next = bool(page.get('has_next'))
        if values:
            last_value_id = int(values[-1].get('id') or last_value_id)
        else:
            has_next = False
    _write_cache_record_auto(path, results, compress=True)
    return {'source': 'live', 'data': results, 'page_count': page_count}


def prewarm_all_properties(
    *,
    force_refresh_tree: bool = False,
    force_refresh_properties: bool = False,
    include_disabled: bool = False,
    language: str = 'ZH_HANS',
    limit: int | None = None,
    max_workers: int = 8,
    retries: int = 2,
    retry_delay_seconds: float = 1.0,
) -> dict[str, Any]:
    started_at = int(time.time())
    pairs = _select_property_pairs(
        force_refresh_tree=force_refresh_tree,
        include_disabled=include_disabled,
        language=language,
        limit=limit,
    )
    pending_pairs = pairs if force_refresh_properties else [
        pair for pair in pairs
        if not _property_cache_is_usable(pair['description_category_id'], pair['type_id'])
    ]

    summary = {
        'started_at': started_at,
        'language': language,
        'limit': limit,
        'total_pairs': len(pairs),
        'pending_pairs': len(pending_pairs),
        'skipped_cached_count': len(pairs) - len(pending_pairs),
        'max_workers': max_workers,
        'retries': retries,
        'success_count': 0,
        'failure_count': 0,
        'items': [],
    }

    def _work(pair: dict[str, Any]) -> dict[str, Any]:
        try:
            result = _retry_call(
                lambda: get_properties(pair['description_category_id'], pair['type_id'], force_refresh=force_refresh_properties),
                retries=retries,
                retry_delay_seconds=retry_delay_seconds,
            )
            return {
                **pair,
                'status': 'ok',
                'source': result.get('source'),
                'property_count': len(result.get('data') or []),
            }
        except Exception as exc:
            return {
                **pair,
                'status': 'error',
                'error': str(exc),
            }

    if max_workers <= 1:
        items = [_work(pair) for pair in pending_pairs]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            items = list(executor.map(_work, pending_pairs))

    for item in items:
        if item.get('status') == 'ok':
            summary['success_count'] += 1
        else:
            summary['failure_count'] += 1
        summary['items'].append(item)

    summary['finished_at'] = int(time.time())
    report_path = PREWARM_REPORTS_DIR / f'properties_prewarm_{summary["finished_at"]}.json'
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    summary['report_path'] = str(report_path)
    return summary


def prewarm_dictionary_values(
    *,
    language: str = 'ZH_HANS',
    force_refresh_tree: bool = False,
    force_refresh_properties: bool = False,
    force_refresh_dictionaries: bool = False,
    include_disabled: bool = False,
    category_limit: int | None = None,
    dictionary_limit: int | None = None,
    max_workers: int = 8,
    retries: int = 2,
    retry_delay_seconds: float = 1.0,
) -> dict[str, Any]:
    started_at = int(time.time())
    property_summary = prewarm_all_properties(
        force_refresh_tree=force_refresh_tree,
        force_refresh_properties=force_refresh_properties,
        include_disabled=include_disabled,
        language=language,
        limit=category_limit,
        max_workers=max_workers,
        retries=retries,
        retry_delay_seconds=retry_delay_seconds,
    )
    pairs = _select_property_pairs(
        force_refresh_tree=False,
        include_disabled=include_disabled,
        language=language,
        limit=category_limit,
    )
    unique_targets = _load_dictionary_targets_from_property_pairs(pairs)
    if dictionary_limit is not None:
        unique_targets = unique_targets[:dictionary_limit]
    pending_targets = unique_targets if force_refresh_dictionaries else [
        target for target in unique_targets
        if not _dictionary_cache_is_usable(
            target['attribute_id'],
            target['description_category_id'],
            target['type_id'],
            language,
        )
    ]
    grouped_targets = _group_dictionary_targets(pending_targets)

    summary = {
        'started_at': started_at,
        'language': language,
        'category_limit': category_limit,
        'dictionary_limit': dictionary_limit,
        'total_targets': len(unique_targets),
        'pending_targets': len(pending_targets),
        'canonical_fetch_targets': len(grouped_targets),
        'skipped_cached_count': len(unique_targets) - len(pending_targets),
        'max_workers': max_workers,
        'retries': retries,
        'success_count': 0,
        'failure_count': 0,
        'items': [],
        'property_report_path': property_summary.get('report_path'),
    }

    def _work(group: dict[str, Any]) -> dict[str, Any]:
        try:
            result = _retry_call(
                lambda: fetch_all_dictionary_values(
                    group['attribute_id'],
                    group['seed_description_category_id'],
                    group['seed_type_id'],
                    language=language,
                    force_refresh=force_refresh_dictionaries,
                ),
                retries=retries,
                retry_delay_seconds=retry_delay_seconds,
            )
            _write_dictionary_group_cache(group, language, list(result.get('data') or []))
            return {
                'attribute_id': group['attribute_id'],
                'attribute_name': group.get('attribute_name'),
                'dictionary_id': group.get('dictionary_id'),
                'category_dependent': group.get('category_dependent'),
                'seed_description_category_id': group['seed_description_category_id'],
                'seed_type_id': group['seed_type_id'],
                'target_count': len(group.get('targets') or []),
                'status': 'ok',
                'source': result.get('source'),
                'value_count': len(result.get('data') or []),
                'page_count': result.get('page_count', 0),
            }
        except Exception as exc:
            return {
                'attribute_id': group['attribute_id'],
                'attribute_name': group.get('attribute_name'),
                'dictionary_id': group.get('dictionary_id'),
                'category_dependent': group.get('category_dependent'),
                'seed_description_category_id': group['seed_description_category_id'],
                'seed_type_id': group['seed_type_id'],
                'target_count': len(group.get('targets') or []),
                'status': 'error',
                'error': str(exc),
            }

    if max_workers <= 1:
        items = [_work(group) for group in grouped_targets]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            items = list(executor.map(_work, grouped_targets))

    for item in items:
        if item.get('status') == 'ok':
            summary['success_count'] += 1
        else:
            summary['failure_count'] += 1
        summary['items'].append(item)

    summary['finished_at'] = int(time.time())
    report_path = PREWARM_REPORTS_DIR / f'dictionaries_prewarm_{summary["finished_at"]}.json'
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    summary['report_path'] = str(report_path)
    return summary


def compact_shared_dictionary_aliases(language: str = 'ZH_HANS') -> dict[str, Any]:
    started_at = int(time.time())
    pairs = _select_property_pairs(language=language)
    unique_targets = _load_dictionary_targets_from_property_pairs(pairs)
    groups = _group_dictionary_targets(unique_targets)

    summary = {
        'started_at': started_at,
        'language': language,
        'groups': len(groups),
        'shared_written': 0,
        'alias_written': 0,
    }

    for group in groups:
        if group.get('category_dependent'):
            continue
        seed = group['targets'][0]
        source_path = dictionary_cache_path(
            seed['attribute_id'],
            seed['description_category_id'],
            seed['type_id'],
            _dictionary_cache_mode_all(language),
        )
        record = read_cache_record(source_path)
        if not record:
            continue
        data = list(record.get('data') or [])
        shared_path = shared_dictionary_cache_path(group['attribute_id'], str(group.get('dictionary_id')), language)
        _write_cache_record_auto(shared_path, data, compress=True)
        summary['shared_written'] += 1
        _write_dictionary_alias_records(group['targets'], language, data, shared_path=str(shared_path))
        summary['alias_written'] += len(group.get('targets') or [])

    report_path = PREWARM_REPORTS_DIR / f'dictionaries_compact_{int(time.time())}.json'
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    summary['report_path'] = str(report_path)
    return summary


def sync_category_cache_to_supabase() -> dict[str, Any]:
    if not has_supabase_service_role():
        return {
            'synced': False,
            'reason': 'missing_service_role_key',
            'entry_count': 0,
        }
    cache = read_category_cache()
    entries = list(cache.get('entries') or [])
    result = upsert_verified_category_entries(entries)
    return {
        'synced': True,
        'entry_count': len(entries),
        'supabase': result,
    }


def export_cache_manifest(output_path: str | None = None) -> dict[str, Any]:
    started_at = int(time.time())

    def _scan(base_dir: Path) -> dict[str, Any]:
        if not base_dir.exists():
            return {'exists': False, 'file_count': 0, 'total_bytes': 0, 'items': []}
        files = [path for path in sorted(base_dir.rglob('*')) if path.is_file()]
        items = []
        total_bytes = 0
        for path in files:
            stat = path.stat()
            size = int(stat.st_size)
            total_bytes += size
            items.append({
                'path': path.relative_to(base_dir.parent).as_posix(),
                'size_bytes': size,
                'modified_at': int(stat.st_mtime),
            })
        return {
            'exists': True,
            'file_count': len(files),
            'total_bytes': total_bytes,
            'items': items,
        }

    manifest = {
        'generated_at': started_at,
        'category_tree': {
            'exists': TREE_CACHE_FILE.exists(),
            'size_bytes': TREE_CACHE_FILE.stat().st_size if TREE_CACHE_FILE.exists() else 0,
        },
        'category_cache': {
            'exists': CATEGORY_CACHE_FILE.exists(),
            'size_bytes': CATEGORY_CACHE_FILE.stat().st_size if CATEGORY_CACHE_FILE.exists() else 0,
        },
        'properties': _scan(PROPERTIES_DIR),
        'dictionaries': _scan(DICTIONARIES_DIR),
        'dictionary_shared': _scan(SHARED_DICTIONARIES_DIR),
        'prewarm_reports': _scan(PREWARM_REPORTS_DIR),
    }
    manifest['summary'] = {
        'property_files': manifest['properties']['file_count'],
        'dictionary_files': manifest['dictionaries']['file_count'],
        'shared_dictionary_files': manifest['dictionary_shared']['file_count'],
        'prewarm_report_files': manifest['prewarm_reports']['file_count'],
        'total_bytes': (
            manifest['category_tree']['size_bytes']
            + manifest['category_cache']['size_bytes']
            + manifest['properties']['total_bytes']
            + manifest['dictionaries']['total_bytes']
            + manifest['dictionary_shared']['total_bytes']
            + manifest['prewarm_reports']['total_bytes']
        ),
    }
    if output_path:
        target = resolve_input_path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        manifest['output_path'] = str(target)
    return manifest


def _walk_tree_rows(nodes: list[dict[str, Any]], parent_id: str | None = None, depth: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in nodes or []:
        category_id = str(node.get('description_category_id')) if node.get('description_category_id') is not None else None
        rows.append({
            'description_category_id': category_id,
            'parent_description_category_id': parent_id,
            'category_name': node.get('category_name'),
            'disabled': bool(node.get('disabled')),
            'depth': depth,
        })
        children = node.get('children') or []
        for child in children:
            if child.get('type_id') is not None:
                rows.append({
                    'description_category_id': category_id,
                    'type_id': str(child.get('type_id')),
                    'type_name': child.get('type_name'),
                    'disabled': bool(child.get('disabled')),
                    'depth': depth + 1,
                })
            else:
                rows.extend(_walk_tree_rows([child], category_id, depth + 1))
    return rows


def export_database_seed(output_dir: str) -> dict[str, Any]:
    target_dir = resolve_input_path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    tree_record = read_category_tree_cache()
    tree_nodes = list(tree_record.get('result') or [])
    category_rows = _walk_tree_rows(tree_nodes)
    leaf_pairs = _collect_tree_leaf_pairs(tree_nodes)
    cache_rows = list((read_category_cache().get('entries') or []))

    property_rows: list[dict[str, Any]] = []
    for path in sorted(PROPERTIES_DIR.rglob('*')):
        if not path.is_file():
            continue
        record = read_cache_record(path) or {}
        stem = path.stem
        if '_' not in stem:
            continue
        description_category_id, type_id = stem.split('_', 1)
        for attr in (record.get('data') or []):
            property_rows.append({
                'description_category_id': description_category_id,
                'type_id': type_id,
                'attribute_id': str(attr.get('id')),
                'attribute_name': attr.get('name'),
                'description': attr.get('description'),
                'type': attr.get('type'),
                'is_required': bool(attr.get('is_required')),
                'is_collection': bool(attr.get('is_collection')),
                'is_aspect': bool(attr.get('is_aspect')),
                'dictionary_id': int(attr.get('dictionary_id') or 0),
                'category_dependent': bool(attr.get('category_dependent')),
                'group_id': attr.get('group_id'),
                'group_name': attr.get('group_name'),
                'max_value_count': attr.get('max_value_count'),
                'attribute_complex_id': attr.get('attribute_complex_id'),
                'complex_is_collection': bool(attr.get('complex_is_collection')),
                'updated_at': record.get('updated_at'),
            })

    dictionary_rows: list[dict[str, Any]] = []
    for path in sorted(DICTIONARIES_DIR.rglob('*')):
        if not path.is_file():
            continue
        record = read_cache_record(path) or {}
        stem = path.name
        parts = stem.split('_')
        if len(parts) < 4:
            continue
        attribute_id = parts[0]
        description_category_id = parts[1]
        type_id = parts[2]
        for value in (record.get('data') or []):
            dictionary_rows.append({
                'attribute_id': attribute_id,
                'description_category_id': description_category_id,
                'type_id': type_id,
                'dictionary_value_id': str(value.get('id')),
                'value': value.get('value'),
                'info': value.get('info'),
                'picture': value.get('picture'),
                'updated_at': record.get('updated_at'),
            })

    outputs = {
        'categories.ndjson': category_rows,
        'category_leaf_pairs.ndjson': leaf_pairs,
        'category_mappings.ndjson': cache_rows,
        'properties.ndjson': property_rows,
        'dictionary_values.ndjson': dictionary_rows,
    }

    files = {}
    for filename, rows in outputs.items():
        path = target_dir / filename
        with path.open('w', encoding='utf-8') as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + '\n')
        files[filename] = {
            'path': str(path),
            'row_count': len(rows),
            'size_bytes': path.stat().st_size,
        }

    summary = {
        'output_dir': str(target_dir),
        'files': files,
        'generated_at': int(time.time()),
    }
    (target_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary
