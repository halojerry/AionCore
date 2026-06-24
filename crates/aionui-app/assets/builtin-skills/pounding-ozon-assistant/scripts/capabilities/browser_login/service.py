#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts._const import DATA_DIR, get_config_profile
from scripts._errors import ConfigError
from scripts.capabilities.browser_probe.service import find_browser_executable, _pick_free_port


def _profile_dir(profile: str) -> Path:
    path = DATA_DIR / 'browser' / 'profiles' / '1688' / profile
    path.mkdir(parents=True, exist_ok=True)
    return path


def _login_url() -> str:
    return 'https://login.1688.com/member/signin.htm'


def _session_file(profile: str) -> Path:
    path = DATA_DIR / 'browser' / 'sessions'
    path.mkdir(parents=True, exist_ok=True)
    return path / f'1688-{profile}.json'


def _write_session(profile: str, payload: dict[str, Any]) -> Path:
    target = _session_file(profile)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return target


def launch_1688_login_browser(*, profile: str | None = None, browser_path: str | None = None) -> dict[str, Any]:
    resolved_browser = find_browser_executable(browser_path)
    if not resolved_browser:
        raise ConfigError('未找到可用的 Chromium 内核浏览器。\n'
                          '请安装以下任一浏览器：Chrome、Edge、Brave、Opera 或 360 浏览器。\n'
                          '安装后重试即可，系统会自动检测。')
    profile_name = str(profile or get_config_profile() or 'default').strip() or 'default'
    user_data_dir = _profile_dir(profile_name)
    login_url = _login_url()
    remote_debugging_port = _pick_free_port()
    launch_args = [
        f'--user-data-dir={user_data_dir}',
        '--profile-directory=Default',
        f'--remote-debugging-port={remote_debugging_port}',
        '--new-window',
        '--no-first-run', '--no-default-browser-check',  # Suppress first-run prompts
        login_url,
    ]
    # Detect browser flavor for platform-specific launch
    browser_lower = resolved_browser.lower()
    is_edge = 'edge' in browser_lower or 'msedge' in browser_lower
    is_brave = 'brave' in browser_lower
    is_opera = 'opera' in browser_lower

    if sys.platform == 'darwin':
        # macOS: use `open -na "App Name" --args ...` to properly bring to foreground
        if is_edge:
            subprocess.Popen(['open', '-na', 'Microsoft Edge', '--args', *launch_args])
        elif is_brave:
            subprocess.Popen(['open', '-na', 'Brave Browser', '--args', *launch_args])
        elif is_opera:
            subprocess.Popen(['open', '-na', 'Opera', '--args', *launch_args])
        elif 'google chrome' in browser_lower or 'chrome' in browser_lower:
            subprocess.Popen(['open', '-na', 'Google Chrome', '--args', *launch_args])
        elif 'chromium' in browser_lower:
            subprocess.Popen(['open', '-na', 'Chromium', '--args', *launch_args])
        else:
            subprocess.Popen([resolved_browser, *launch_args])
    else:
        # Windows / Linux: spawn directly
        subprocess.Popen([resolved_browser, *launch_args])

    session_path = _write_session(profile_name, {
        'profile': profile_name,
        'browser_path': resolved_browser,
        'user_data_dir': str(user_data_dir),
        'login_url': login_url,
        'remote_debugging_port': remote_debugging_port,
        'cdp_url': f'http://127.0.0.1:{remote_debugging_port}',
    })

    print(f'\n📱 请在打开的浏览器窗口中扫码登录 1688\n'
          f'   （如未自动打开，请手动访问: {login_url}）\n', file=sys.stderr)

    return {
        'profile': profile_name,
        'browser_path': resolved_browser,
        'user_data_dir': str(user_data_dir),
        'login_url': login_url,
        'remote_debugging_port': remote_debugging_port,
        'cdp_url': f'http://127.0.0.1:{remote_debugging_port}',
        'session_file': str(session_path),
    }
