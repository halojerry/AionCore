#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scripts._errors import SkillError
from _output import print_failure, print_success
from scripts.capabilities.browser_probe.service import probe_1688_page

COMMAND_NAME = 'browser_probe'
COMMAND_DESC = '拉起浏览器登录/探测 1688 页面结构化数据'


def _markdown(data: dict) -> str:
    summary = data.get('summary') or {}
    launch = data.get('launch') or {}
    probe = data.get('probe') or {}
    lines = [
        '## 1688 浏览器探测结果',
        '',
        f"- ready: `{data.get('ready')}`",
        f"- timed_out: `{data.get('timed_out')}`",
        f"- profile: `{launch.get('profile')}`",
        f"- browser: `{launch.get('browser_path')}`",
        f"- login_required: `{summary.get('login_required')}`",
        f"- title: {summary.get('title') or '-'}",
        f"- seller: {summary.get('seller') or '-'}",
        f"- price: {summary.get('price') or '-'}",
        f"- images: `{summary.get('image_count')}`",
        f"- attributes: `{summary.get('attribute_count')}`",
        f"- dom_sku_count: `{summary.get('dom_sku_count')}`",
        f"- runtime_sku_count: `{summary.get('runtime_sku_count')}`",
        f"- artifact: `{data.get('artifact_path')}`",
    ]
    if probe.get('loginRequired'):
        lines += ['', '提示：当前页面仍需要先登录 1688，重新运行时可加 `--headed` 保持可见浏览器登录。']
    return '\n'.join(lines)


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='浏览器探测 1688 页面结构化数据')
    parser.add_argument('--url', required=True)
    parser.add_argument('--headed', action='store_true')
    parser.add_argument('--timeout-seconds', type=int, default=120)
    parser.add_argument('--poll-ms', type=int, default=1500)
    parser.add_argument('--profile', default=None)
    parser.add_argument('--browser-path', default=None)
    parser.add_argument('--task-id', default=None)
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        data = probe_1688_page(
            parsed.url,
            headed=parsed.headed,
            timeout_seconds=parsed.timeout_seconds,
            poll_ms=parsed.poll_ms,
            profile=parsed.profile,
            browser_path=parsed.browser_path,
            task_id=parsed.task_id,
        )
        print_success(_markdown(data), data)
        return 0
    except SkillError as exc:
        print_failure(f'❌ 浏览器探测失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ 浏览器探测失败：{exc}', error_code='BROWSER_PROBE_UNEXPECTED')
        return 1
