#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = str(SKILL_DIR / 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from lib.bootstrap import ensure_runtime_dependencies
from scripts._const import SKILL_NAME, SKILL_VERSION


def _output(success: bool, markdown: str = '', data: dict | None = None, error_code: str = '') -> None:
    result: dict = {'success': success}
    if markdown:
        result['markdown'] = markdown
    if data is not None:
        result['data'] = data
    if error_code:
        result['error_code'] = error_code
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


def _discover_capabilities() -> dict[str, str]:
    commands: dict[str, str] = {}
    caps_dir = os.path.join(SCRIPTS_DIR, 'capabilities')
    if not os.path.isdir(caps_dir):
        return commands
    for name in sorted(os.listdir(caps_dir)):
        cmd_path = os.path.join(caps_dir, name, 'cmd.py')
        if not os.path.isfile(cmd_path):
            continue
        module_path = f'capabilities.{name}.cmd'
        try:
            mod = importlib.import_module(module_path)
            cmd_name = getattr(mod, 'COMMAND_NAME', name)
            commands[cmd_name] = module_path
        except Exception:
            pass
    return commands


def _load_release_meta() -> dict:
    meta_path = SKILL_DIR / '_meta.json'
    if meta_path.is_file():
        try:
            return json.loads(meta_path.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {
        'name': SKILL_NAME,
        'version': SKILL_VERSION,
        'entrypoint': 'cli.py',
        'release_type': 'source',
        'includes_meta_file': meta_path.is_file(),
    }


def _version() -> None:
    meta = _load_release_meta()
    markdown = '\n'.join([
        f'**{meta.get("name", SKILL_NAME)} 版本信息**',
        '',
        f'- name: `{meta.get("name", SKILL_NAME)}`',
        f'- version: `{meta.get("version", SKILL_VERSION)}`',
        f'- release_type: `{meta.get("release_type", "source")}`',
        f'- entrypoint: `{meta.get("entrypoint", "cli.py")}`',
        f'- includes_meta_file: `{meta.get("includes_meta_file", False)}`',
    ])
    _output(True, markdown=markdown, data=meta)


def _usage(commands: dict[str, str]) -> None:
    lines = ['**pounding-ozon 用法**\n', '```']
    lines.append('python3 cli.py version              查看版本与 _meta.json 信息')
    for name in sorted(commands):
        try:
            mod = importlib.import_module(commands[name])
            desc = getattr(mod, 'COMMAND_DESC', '')
        except Exception:
            desc = ''
        lines.append(f'python3 cli.py {name:<20} {desc}')
    lines.append('```')
    _output(True, markdown='\n'.join(lines))


def main() -> int:
    ensure_runtime_dependencies()
    commands = _discover_capabilities()
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        _usage(commands)
        return 0

    command = sys.argv[1]
    if command in ('version', '--version', 'about'):
        _version()
        return 0
    args = sys.argv[2:]
    handler = commands.get(command)
    if not handler:
        _output(False, markdown=f'未知命令: `{command}`', error_code='UNKNOWN_COMMAND')
        return 1

    sys.argv = [f'cli.py {command}'] + args
    mod = importlib.import_module(handler)
    result = mod.main(args)
    return result if isinstance(result, int) else 0


if __name__ == '__main__':
    raise SystemExit(main())
