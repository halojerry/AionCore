#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _errors import SkillError
from _output import print_failure, print_success
from capabilities.procurement.service import create_procurement

COMMAND_NAME = 'procurement'
COMMAND_DESC = '统一包装：采购询盘 + canonical inquiry'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='统一采购询盘')
    parser.add_argument('--offerName', required=True)
    parser.add_argument('--count', required=True)
    parser.add_argument('--demand', required=True)
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        data = create_procurement(parsed.offerName, parsed.count, parsed.demand)
        print_success('采购询盘已创建，并生成 canonical inquiry 结构。', data)
        return 0
    except SkillError as exc:
        print_failure(f'❌ 采购询盘失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ 采购询盘失败：{exc}', error_code='PROCUREMENT_UNEXPECTED')
        return 1
