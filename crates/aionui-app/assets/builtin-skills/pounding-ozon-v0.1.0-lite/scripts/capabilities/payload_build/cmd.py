#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _const import resolve_input_path
from _errors import ValidationError
from _output import print_failure, print_success
from capabilities.payload_build.service import build_import_payload
from lib.config_store import load_config
from models.contracts import AssetManifest, CategoryResolution, NormalizedProductDraft, ResolvedAttributeSet

COMMAND_NAME = 'payload_build'
COMMAND_DESC = '构建 Ozon import payload（骨架版）'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='构建 payload')
    parser.add_argument('--draft-file', required=True)
    parser.add_argument('--category-file', required=True)
    parser.add_argument('--assets-file', required=True)
    parser.add_argument('--attrs-file', required=True)
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        cfg = load_config()
        draft = NormalizedProductDraft(**json.loads(resolve_input_path(parsed.draft_file, must_exist=True).read_text(encoding='utf-8')))
        category = CategoryResolution(**json.loads(resolve_input_path(parsed.category_file, must_exist=True).read_text(encoding='utf-8')))
        assets = AssetManifest(**json.loads(resolve_input_path(parsed.assets_file, must_exist=True).read_text(encoding='utf-8')))
        attrs = ResolvedAttributeSet(**json.loads(resolve_input_path(parsed.attrs_file, must_exist=True).read_text(encoding='utf-8')))
        payload = build_import_payload(cfg, draft, category, attrs, assets)
        print_success('payload 构建成功', {'payload_hash': payload.payload_hash, 'items': payload.items})
        return 0
    except ValidationError as exc:
        print_failure(f'❌ payload 构建失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ payload 构建失败：{exc}', error_code='PAYLOAD_BUILD_UNEXPECTED')
        return 1
