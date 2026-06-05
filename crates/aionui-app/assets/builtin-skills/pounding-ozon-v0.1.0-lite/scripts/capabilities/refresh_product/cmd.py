#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _output import print_failure, print_success
from capabilities.refresh_product.service import audit_refresh_candidates, find_refresh_candidates, list_managed_products, list_store_products, refresh_product, snapshot_store_products

COMMAND_NAME = 'refresh_product'
COMMAND_DESC = 'Ozon 老商品翻新 / 店铺商品巡检入口'
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve_project_root() -> Path:
    env_root = os.environ.get('PROJECT_ROOT', '').strip()
    if env_root:
        return Path(env_root).expanduser().resolve()
    return PROJECT_ROOT


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='Ozon 商品翻新')
    sub = parser.add_subparsers(dest='target')

    p_list = sub.add_parser('list_store')
    p_list.add_argument('--limit', type=int, default=20)
    p_list.add_argument('--last-id', default='')
    p_list.add_argument('--visibility', default='ALL')

    sub.add_parser('managed')
    p_snap = sub.add_parser('snapshot')
    p_snap.add_argument('--limit', type=int, default=100)
    p_snap.add_argument('--last-id', default='')
    p_snap.add_argument('--visibility', default='ALL')

    p_candidates = sub.add_parser('candidates')
    p_candidates.add_argument('--limit', type=int, default=20)
    p_candidates.add_argument('--last-id', default='')
    p_candidates.add_argument('--visibility', default='ALL')
    p_candidates.add_argument('--managed-only', action='store_true')

    p_audit = sub.add_parser('audit')
    p_audit.add_argument('--limit', type=int, default=20)
    p_audit.add_argument('--last-id', default='')
    p_audit.add_argument('--visibility', default='ALL')
    p_audit.add_argument('--managed-only', action='store_true')
    p_audit.add_argument('--no-snapshot', action='store_true')

    p_cron = sub.add_parser('install_cron')
    p_cron.add_argument('--schedule', default='0 9 * * *', help='cron 表达式，默认每天 09:00')

    p_refresh = sub.add_parser('run')
    p_refresh.add_argument('--product-id', default=None)
    p_refresh.add_argument('--offer-id', default=None)
    p_refresh.add_argument('--source-1688-url', default=None)
    p_refresh.add_argument('--no-better-supply', action='store_true')
    p_refresh.add_argument('--poll-status', action='store_true')
    p_refresh.add_argument('--batch-id', default='refresh-batch-1')
    p_refresh.add_argument('--correlation-id', default=str(uuid.uuid4()))

    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        if not parsed.target or parsed.target == 'list_store':
            data = list_store_products(limit=parsed.limit, last_id=parsed.last_id, visibility=parsed.visibility)
            print_success('店铺商品列表已获取', data)
            return 0
        if parsed.target == 'managed':
            print_success('内部托管商品列表已获取', list_managed_products())
            return 0
        if parsed.target == 'snapshot':
            print_success('店铺商品快照已写入', snapshot_store_products(
                limit=parsed.limit,
                last_id=parsed.last_id,
                visibility=parsed.visibility,
            ))
            return 0
        if parsed.target == 'candidates':
            print_success('翻新候选商品列表已获取', find_refresh_candidates(
                limit=parsed.limit,
                last_id=parsed.last_id,
                visibility=parsed.visibility,
                managed_only=parsed.managed_only,
            ))
            return 0
        if parsed.target == 'audit':
            print_success('翻新审计已完成，请先返回候选给 Agent/用户确认', audit_refresh_candidates(
                limit=parsed.limit,
                last_id=parsed.last_id,
                visibility=parsed.visibility,
                managed_only=parsed.managed_only,
                write_snapshot=not parsed.no_snapshot,
            ))
            return 0
        if parsed.target == 'install_cron':
            project_root = str(_resolve_project_root())
            cron_line = f'{parsed.schedule} cd "{project_root}" && python3 cli.py refresh_product audit --limit 100 >> data/manual/refresh_audit.log 2>&1'
            portable_cron_line = f'{parsed.schedule} PROJECT_ROOT="${{PROJECT_ROOT:?set PROJECT_ROOT to the repo root}}" && cd "$PROJECT_ROOT" && python3 cli.py refresh_product audit --limit 100 >> data/manual/refresh_audit.log 2>&1'
            print_success('建议的 cron 任务已生成，Agent 可据此自动创建', {
                'cron_line': cron_line,
                'portable_cron_line': portable_cron_line,
                'project_root': project_root,
                'agent_guidance': 'Agent 应先向用户展示将要安装的 cron_line，再决定是否写入 crontab。',
            })
            return 0
        if parsed.target == 'run':
            data = refresh_product(
                product_id=parsed.product_id,
                offer_id=parsed.offer_id,
                source_1688_url=parsed.source_1688_url,
                search_better_supply=not parsed.no_better_supply,
                poll_status=parsed.poll_status,
                correlation_id=parsed.correlation_id,
                batch_id=parsed.batch_id,
            )
            summary = dict(data.get('final_summary') or {})
            source_url = summary.get('source_url') or summary.get('source_1688_url') or '-'
            offer_id = summary.get('offer_id') or '-'
            product_id = summary.get('product_id') or parsed.product_id or '-'
            task_id = summary.get('ozon_task_id') or '-'
            procurement_cost = summary.get('procurement_cost')
            profit_margin = summary.get('profit_margin')
            suggested_price = summary.get('suggested_price')
            currency_code = summary.get('currency_code') or 'CNY'
            publish_status = summary.get('publish_status') or summary.get('classified_outcome') or '-'
            browser_probe_label = summary.get('browser_probe_reason_label')
            detail_enrichment_mode = summary.get('detail_enrichment_mode')
            lines = [
                '## 商品翻新结果',
                '',
                f'- product_id: `{product_id}`',
                f'- offer_id: `{offer_id}`',
                f'- 1688 链接: {source_url}',
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
            print_success('\n'.join(lines), data)
            return 0
        print_failure('未知 refresh_product 命令', error_code='UNKNOWN_REFRESH_PRODUCT_COMMAND')
        return 1
    except Exception as exc:
        print_failure(f'❌ 商品翻新失败：{exc}', error_code='REFRESH_PRODUCT_UNEXPECTED')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
