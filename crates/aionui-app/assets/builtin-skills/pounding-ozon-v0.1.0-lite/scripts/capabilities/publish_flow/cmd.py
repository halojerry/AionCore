#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _const import DEFAULT_MXOU_BASE_URL, resolve_input_path
from _errors import ValidationError
from _output import print_failure, print_success
from capabilities.publish_flow.service import orchestrate_publish_flow, orchestrate_publish_flow_batch, preflight

COMMAND_NAME = 'publish_flow'
COMMAND_DESC = '统一发布流程入口'


def _artifact_dir() -> Path:
    path = resolve_input_path('data/manual/publish_flow_runs')
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_run_artifact(result: dict, *, correlation_id: str, batch_id: str, mode: str) -> str:
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d-%H%M%S')
    safe_correlation = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in (correlation_id or 'run'))
    safe_batch = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in (batch_id or 'batch'))
    path = _artifact_dir() / f'{timestamp}-{mode}-{safe_batch}-{safe_correlation}.json'
    payload = dict(result or {})
    payload.setdefault('artifact_meta', {})
    payload['artifact_meta'].update({
        'mode': mode,
        'correlation_id': correlation_id,
        'batch_id': batch_id,
        'written_at': now.isoformat(),
        'artifact_path': str(path),
        'elapsed_seconds': ((payload.get('timing') or {}).get('elapsed_seconds')),
    })
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(path)


def _load_json_file(raw_path: str | None):
    if not raw_path:
        return None
    path = resolve_input_path(raw_path, must_exist=True)
    return json.loads(path.read_text(encoding='utf-8'))


def _single_publish_markdown(result: dict) -> str:
    if result.get('source_summary') and result.get('family_summaries'):
        source_summary = dict(result.get('source_summary') or {})
        artifact_path = ((result.get('artifact_meta') or {}).get('artifact_path'))
        lines = [
            '## 多 family 发布结果',
            '',
            f'- source_item_id: `{source_summary.get("source_item_id") or "-"}`',
            f'- family_count: `{source_summary.get("family_count")}`',
            f'- total_item_count: `{source_summary.get("total_item_count")}`',
            f'- mixed_family: `{source_summary.get("mixed_family")}`',
            f'- success_count: `{source_summary.get("success_count")}`',
            f'- blocked_count: `{source_summary.get("blocked_count")}`',
        ]
        if artifact_path:
            lines.append(f'- 运行产物: `{artifact_path}`')
        lines.extend(['', '### Families'])
        for summary in list(result.get('family_summaries') or []):
            lines.extend([
                '',
                f'- family_key: `{summary.get("family_key") or "-"}`',
                f'  - family_label: `{summary.get("family_label") or "-"}`',
                f'  - item_count: `{summary.get("item_count")}`',
                f'  - merge_group_value: `{summary.get("merge_group_value") or "-"}`',
                f'  - classified_outcome: `{summary.get("classified_outcome") or "-"}`',
                f'  - task_id: `{summary.get("task_id") or "-"}`',
            ])
        return '\n'.join(lines)

    summary = dict(result.get('final_summary') or {})
    title = summary.get('title') or '-'
    source_item_id = summary.get('source_item_id') or '-'
    offer_id = summary.get('offer_id') or '-'
    product_id = summary.get('product_id') or '-'
    source_url = summary.get('source_url') or summary.get('source_1688_url') or '-'
    outcome = summary.get('classified_outcome') or ('blocked' if result.get('blocked') else 'unknown')
    task_id = summary.get('ozon_task_id') or '-'
    procurement_cost = summary.get('procurement_cost')
    profit_margin = summary.get('profit_margin')
    suggested_price = summary.get('suggested_price')
    currency_code = summary.get('currency_code') or 'CNY'
    publish_status = summary.get('publish_status') or outcome
    browser_probe_label = summary.get('browser_probe_reason_label')
    detail_enrichment_mode = summary.get('detail_enrichment_mode')
    artifact_path = ((result.get('artifact_meta') or {}).get('artifact_path'))
    auto_repairs = list(result.get('auto_repairs') or [])
    lines = [
        '## 单商品发布结果',
        '',
        f'- 标题: {title}',
        f'- source_item_id: `{source_item_id}`',
        f'- product_id: `{product_id}`',
        f'- offer_id: `{offer_id}`',
        f'- 1688 链接: {source_url}',
        f'- 发布结果: `{outcome}`',
        f'- Ozon task_id: `{task_id}`',
        f'- 当前状态: `{publish_status}`',
    ]
    if detail_enrichment_mode:
        lines.append(f'- 详情补全模式: `{detail_enrichment_mode}`')
    if browser_probe_label:
        lines.append(f'- 浏览器补强状态: `{browser_probe_label}`')
    if procurement_cost is not None:
        lines.append(f'- 采购成本: `{procurement_cost}` {currency_code}')
    if profit_margin is not None:
        try:
            lines.append(f'- 利润率: `{round(float(profit_margin) * 100, 2)}%`')
        except Exception:
            lines.append(f'- 利润率: `{profit_margin}`')
    if suggested_price is not None:
        lines.append(f'- 建议售价: `{suggested_price}` {currency_code}')
    if artifact_path:
        lines.append(f'- 运行产物: `{artifact_path}`')
    if result.get('blocked'):
        issue_codes = [str(item.get('code') or '') for item in (((result.get('stages') or {}).get('gate') or {}).get('issues') or [])]
        if issue_codes:
            lines.append(f'- 阻断原因: `{", ".join(issue_codes)}`')
    if auto_repairs:
        lines.append(f'- 自动修复: `{", ".join(auto_repairs)}`')
    return '\n'.join(lines)


def _batch_publish_markdown(result: dict) -> str:
    artifact_path = ((result.get('artifact_meta') or {}).get('artifact_path'))
    lines = [
        '## 批量发布结果',
        '',
        f'- 队列模式: `{result.get("queue_mode")}`',
        f'- 最大并发: `{result.get("max_workers")}`',
        f'- 队列策略: `{result.get("queue_strategy")}`',
        f'- 总数: `{result.get("total")}`',
        f'- 成功: `{result.get("success_count")}`',
        f'- 阻断: `{result.get("blocked_count")}`',
        f'- 失败: `{result.get("failed_count")}`',
    ]
    if artifact_path:
        lines.append(f'- 运行产物: `{artifact_path}`')
    lines.extend([
        '',
        '### 明细',
    ])
    for item in list(result.get('items') or []):
        final_summary = dict(item.get('final_summary') or {})
        source_item_id = item.get('source_item_id') or final_summary.get('source_item_id') or '-'
        source_url = final_summary.get('source_url') or final_summary.get('source_1688_url') or '-'
        task_id = final_summary.get('ozon_task_id') or '-'
        suggested_price = final_summary.get('suggested_price')
        currency_code = final_summary.get('currency_code') or 'CNY'
        outcome = final_summary.get('classified_outcome') or item.get('queue_status') or 'unknown'
        browser_probe_label = final_summary.get('browser_probe_reason_label')
        detail_enrichment_mode = final_summary.get('detail_enrichment_mode')
        lines.extend([
            '',
            f'- `{source_item_id}` · `{outcome}` · task `{task_id}`',
            f'  - 1688: {source_url}',
        ])
        if detail_enrichment_mode:
            lines.append(f'  - 详情补全: {detail_enrichment_mode}')
        if browser_probe_label:
            lines.append(f'  - 浏览器补强: {browser_probe_label}')
        if suggested_price is not None:
            lines.append(f'  - 建议售价: {suggested_price} {currency_code}')
        if item.get('error'):
            lines.append(f'  - error: {item.get("error")}')
    return '\n'.join(lines)


def _next_steps_for_missing(missing: list[str]) -> list[str]:
    steps = ['python3 cli.py configure status']
    if '1688 AK' in missing:
        steps.append('python3 cli.py configure 1688 --ak <YOUR_AK>')
    if 'Ozon 店铺配置' in missing:
        steps.append('python3 cli.py configure ozon --client-id <ID> --api-key <KEY>')
    if 'mxou token' in missing:
        steps.append('python3 cli.py configure mxou --token <TOKEN>')
    return steps


def _preflight_message(missing: list[str]) -> str:
    base = '❌ 发布流程预检失败：缺少关键配置。'
    detail = f'当前缺失：{", ".join(missing)}。'
    tail = '\n\n先补齐缺失项后，才能继续执行统一铺货链路。'
    if 'mxou token' in missing:
        tail += f'\n其中 mxou token 需要去 {DEFAULT_MXOU_BASE_URL} 注册获取。'
    return f'{base}\n\n{detail}{tail}'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='统一发布流程')
    parser.add_argument('--draft-file', help='Normalized draft JSON 文件')
    parser.add_argument('--drafts-file', help='批量发布 drafts JSON 文件（数组）')
    parser.add_argument('--assets-file', help='已完成的 AssetManifest JSON 文件')
    parser.add_argument('--query')
    parser.add_argument('--image')
    parser.add_argument('--url')
    parser.add_argument('--compare', action='store_true')
    parser.add_argument('--stub-images', action='store_true', help='使用 stub 图片清单继续流程')
    parser.add_argument('--force-refresh', action='store_true')
    parser.add_argument('--poll-status', action='store_true')
    parser.add_argument('--max-workers', type=int, default=0, help='批量队列最大并发数；默认自动按队列长度使用 2~3 并发')
    parser.add_argument('--batch-id', default='batch-1')
    parser.add_argument('--correlation-id', default=str(uuid.uuid4()))
    parser.add_argument('--dry-run', action='store_true', help='仅输出阶段预检信息')
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    os.environ.setdefault('POUNDING_OZON_TASK_ID', parsed.correlation_id)

    cfg, missing = preflight()
    if missing:
        print_failure(
            _preflight_message(missing),
            error_code='PREFLIGHT_MISSING_CONFIG',
            details={
                'missing': missing,
                'guide_command': 'python3 cli.py configure guide',
                'next_steps': _next_steps_for_missing(missing),
            },
        )
        return 1

    draft_data = _load_json_file(parsed.draft_file)
    drafts_data = _load_json_file(parsed.drafts_file)
    assets_data = _load_json_file(parsed.assets_file)

    try:
        if drafts_data is not None:
            result = orchestrate_publish_flow_batch(
                drafts_data=drafts_data,
                force_refresh=parsed.force_refresh,
                poll_status=parsed.poll_status,
                correlation_id_prefix=parsed.correlation_id,
                batch_id=parsed.batch_id,
                max_workers=parsed.max_workers,
            )
            artifact_path = _write_run_artifact(result, correlation_id=parsed.correlation_id, batch_id=parsed.batch_id, mode='batch')
            result.setdefault('artifact_meta', {})['artifact_path'] = artifact_path
            print_success(_batch_publish_markdown(result), {
                'dry_run': parsed.dry_run,
                'config': cfg.to_dict(),
                **result,
            })
            return 0
        result = orchestrate_publish_flow(
            draft_data=draft_data,
            query=parsed.query,
            image=parsed.image,
            url=parsed.url,
            compare_mode=parsed.compare,
            assets_data=assets_data,
            dry_run=parsed.dry_run,
            stub_images=parsed.stub_images,
            force_refresh=parsed.force_refresh,
            poll_status=parsed.poll_status,
            correlation_id=parsed.correlation_id,
            batch_id=parsed.batch_id,
        )
        artifact_path = _write_run_artifact(result, correlation_id=parsed.correlation_id, batch_id=parsed.batch_id, mode='single')
        result.setdefault('artifact_meta', {})['artifact_path'] = artifact_path
        if result.get('blocked') and not result['stages'].get('currency_detection', {}).get('detected', True):
            print_failure(
                '❌ 发布流程失败：无法自动探测当前店铺币种。',
                error_code='CURRENCY_CONFIRMATION_REQUIRED',
                details={
                    'currency_detection': result['stages'].get('currency_detection'),
                    'recommended_next_step': '请确认当前 Ozon 店铺合同币种（如 CNY / RUB），然后重新执行 configure ozon 补充 --currency。',
                    'example_command': 'python3 cli.py configure ozon --client-id <ID> --api-key <KEY> --currency <CNY_OR_RUB>',
                },
            )
            return 1
        print_success(_single_publish_markdown(result), {
            'dry_run': parsed.dry_run,
            'config': cfg.to_dict(),
            **result,
        })
        return 0
    except ValidationError as exc:
        details = None
        if '必须先明确选中 1 个商品' in exc.message:
            details = {
                'selection_required': True,
                'recommended_next_step': '先执行 text_search / image_search / compare 获取候选，再把确认后的 normalized draft 保存为 --draft-file 继续',
            }
        print_failure(f'❌ 发布流程失败：{exc.message}', error_code=exc.error_code, details=details)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
