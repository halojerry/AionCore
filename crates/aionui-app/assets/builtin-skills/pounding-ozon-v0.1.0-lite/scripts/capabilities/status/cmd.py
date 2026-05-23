#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _output import print_failure, print_success
from capabilities.status.service import check_task

COMMAND_NAME = 'status'
COMMAND_DESC = '统一 Ozon 导入状态查询（骨架版）'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='查询 task 状态')
    parser.add_argument('--task-id', required=True)
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        data = check_task(parsed.task_id)
        raw = dict(data.get('raw') or {})
        items = list((raw.get('result') or {}).get('items') or [])
        summary = {
            'task_id': parsed.task_id,
            'classified_outcome': data.get('classified_outcome'),
            'publish_status': data.get('classified_outcome'),
            'items': items,
            'total_items': len(items),
        }
        markdown_lines = [
            '## 状态查询结果',
            '',
            f'- task_id: `{parsed.task_id}`',
            f'- 当前状态: `{summary["publish_status"]}`',
            f'- 条目数: `{summary["total_items"]}`',
        ]
        print_success('\n'.join(markdown_lines), summary)
        return 0
    except Exception as exc:
        print_failure(f'❌ 状态查询失败：{exc}', error_code='STATUS_UNEXPECTED')
        return 1
