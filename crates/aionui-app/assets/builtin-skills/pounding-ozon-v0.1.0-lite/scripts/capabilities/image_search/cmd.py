#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _errors import SkillError
from _output import print_failure, print_success
from capabilities.image_search.service import search_image

COMMAND_NAME = 'image_search'
COMMAND_DESC = '统一包装：1688 图片搜索 + canonical intake'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='统一图片搜索')
    parser.add_argument('--image', required=True)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--sort', default=None)
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        data = search_image(parsed.image, parsed.limit, parsed.sort)
        print_success('图片搜索完成，已生成 canonical intake 候选。', data)
        return 0
    except SkillError as exc:
        print_failure(f'❌ 图片搜索失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ 图片搜索失败：{exc}', error_code='IMAGE_SEARCH_UNEXPECTED')
        return 1
