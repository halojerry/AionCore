#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _errors import SkillError
from _output import print_failure, print_success
from capabilities.browser_login.service import launch_1688_login_browser

COMMAND_NAME = 'browser_login'
COMMAND_DESC = '用普通 Chrome 打开 1688 登录页并复用本地 profile'


def _markdown(data: dict) -> str:
    return '\n'.join([
        '## 1688 登录浏览器已启动',
        '',
        f"- profile: `{data.get('profile')}`",
        f"- browser: `{data.get('browser_path')}`",
        f"- user_data_dir: `{data.get('user_data_dir')}`",
        f"- login_url: `{data.get('login_url')}`",
        '',
        '请在打开的浏览器中直接扫码/登录 1688；登录完成后保持该窗口即可，后续 browser_probe / 发布链路会复用同一 profile。',
    ])


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='用普通 Chrome 打开 1688 登录页')
    parser.add_argument('--profile', default=None)
    parser.add_argument('--browser-path', default=None)
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        data = launch_1688_login_browser(profile=parsed.profile, browser_path=parsed.browser_path)
        print_success(_markdown(data), data)
        return 0
    except SkillError as exc:
        print_failure(f'❌ 启动 1688 登录浏览器失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ 启动 1688 登录浏览器失败：{exc}', error_code='BROWSER_LOGIN_UNEXPECTED')
        return 1
