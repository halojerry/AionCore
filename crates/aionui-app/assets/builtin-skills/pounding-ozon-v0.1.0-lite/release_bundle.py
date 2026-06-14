#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import fnmatch
import zipfile
from pathlib import Path

from scripts._const import SKILL_NAME, SKILL_VERSION
from scripts._const import resolve_input_path

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / 'dist'

EXCLUDE_GLOBS: tuple[str, ...] = (
    '.omx',
    '.omx/**',
    '**/.omx/**',
    '.gitignore',
    '.DS_Store',
    '**/.DS_Store',
    '.pytest_cache',
    '.pytest_cache/**',
    '**/.pytest_cache/**',
    '__pycache__',
    '__pycache__/**',
    '**/__pycache__/**',
    '*.pyc',
    'dist',
    'dist/**',
    'data',
    'data/**',
    'tests',
    'tests/**',
    'assets_*.json',
    'draft_*.json',
    'test_draft.json',
    'cat_*.json',
    'docs',
    'docs/**',
    'protected_release.py',
    'scripts/dev',
    'scripts/dev/**',
)


def _normalize(rel_path: str) -> str:
    normalized = rel_path.replace('\\', '/')
    while normalized.startswith('./'):
        normalized = normalized[2:]
    return normalized


def should_include_in_release(rel_path: str) -> bool:
    normalized = _normalize(rel_path)
    if not normalized:
        return False
    for pattern in EXCLUDE_GLOBS:
        if fnmatch.fnmatch(normalized, pattern):
            return False
    return True


def collect_release_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        rel_path = path.relative_to(root).as_posix()
        if should_include_in_release(rel_path):
            files.append(path)
    return files


def build_release_meta(root: Path = ROOT) -> dict[str, object]:
    files = collect_release_files(root)
    return {
        'name': SKILL_NAME,
        'version': SKILL_VERSION,
        'bundle': f'{SKILL_NAME}-v{SKILL_VERSION}-lite.zip',
        'entrypoint': 'cli.py',
        'release_type': 'lite',
        'file_count': len(files) + 1,
        'includes_meta_file': True,
    }


def build_release_bundle(output_dir: Path = DIST_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f'{SKILL_NAME}-v{SKILL_VERSION}-lite.zip'
    files = collect_release_files(ROOT)
    meta_payload = json.dumps(build_release_meta(ROOT), ensure_ascii=False, indent=2) + '\n'
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            rel = path.relative_to(ROOT).as_posix()
            if rel == '_meta.json':
                continue
            zf.write(path, rel)
        zf.writestr('_meta.json', meta_payload)
    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser(description='Build a lightweight first-release bundle without runtime caches.')
    parser.add_argument('--output-dir', default=str(DIST_DIR))
    args = parser.parse_args()
    archive_path = build_release_bundle(resolve_input_path(args.output_dir))
    print(archive_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
