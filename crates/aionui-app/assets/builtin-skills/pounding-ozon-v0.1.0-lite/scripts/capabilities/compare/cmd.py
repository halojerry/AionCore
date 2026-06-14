#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _errors import SkillError
from _output import print_failure, print_success
from capabilities.compare.service import compare_products

COMMAND_NAME = 'compare'
COMMAND_DESC = '统一包装：1688 同款比价 + canonical intake'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='统一同款比价')
    parser.add_argument('--image', default=None)
    parser.add_argument('--url', default=None)
    parser.add_argument('--limit', type=int, default=3)
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        if not parsed.image and not parsed.url:
            print_failure('❌ compare 必须提供 --image 或 --url', error_code='MISSING_COMPARE_SOURCE')
            return 1
        data = compare_products(parsed.image, parsed.url, parsed.limit)
        print_success('同款比价完成，已生成 canonical intake 候选。', data)
        return 0
    except SkillError as exc:
        print_failure(f'❌ 同款比价失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ 同款比价失败：{exc}', error_code='COMPARE_UNEXPECTED')
        return 1
