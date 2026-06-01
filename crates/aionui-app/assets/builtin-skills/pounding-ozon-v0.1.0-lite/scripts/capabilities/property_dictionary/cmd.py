#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _const import resolve_input_path
from _errors import SkillError
from _output import print_failure, print_success
from capabilities.property_dictionary.service import resolve_property_dictionary
from models.contracts import CategoryResolution, NormalizedProductDraft

COMMAND_NAME = 'property_dictionary'
COMMAND_DESC = 'Ozon 属性/字典值解析'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='属性/字典值解析')
    parser.add_argument('--draft-file', required=True)
    parser.add_argument('--category-file', required=True)
    parser.add_argument('--force-refresh', action='store_true')
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        draft = NormalizedProductDraft(**json.loads(resolve_input_path(parsed.draft_file, must_exist=True).read_text(encoding='utf-8')))
        category = CategoryResolution(**json.loads(resolve_input_path(parsed.category_file, must_exist=True).read_text(encoding='utf-8')))
        data = resolve_property_dictionary(draft, category, force_refresh=parsed.force_refresh)
        print_success('属性/字典值解析完成', data)
        return 0
    except SkillError as exc:
        print_failure(f'❌ 属性/字典值解析失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ 属性/字典值解析失败：{exc}', error_code='PROPERTY_DICTIONARY_UNEXPECTED')
        return 1
