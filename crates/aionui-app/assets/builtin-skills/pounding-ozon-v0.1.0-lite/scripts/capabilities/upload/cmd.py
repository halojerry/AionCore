#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _const import resolve_input_path
from _errors import ValidationError
from _output import print_failure, print_success
from capabilities.upload.service import submit_payload
from models.contracts import OzonImportPayload

COMMAND_NAME = 'upload'
COMMAND_DESC = '提交 Ozon import payload（骨架版）'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='上传 payload')
    parser.add_argument('--payload-file', required=True)
    parser.add_argument('--correlation-id', default=str(uuid.uuid4()))
    parser.add_argument('--batch-id', default='batch-1')
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        raw = json.loads(resolve_input_path(parsed.payload_file, must_exist=True).read_text(encoding='utf-8'))
        payload = OzonImportPayload(**raw)
        result = submit_payload(payload, parsed.correlation_id, parsed.batch_id)
        print_success('upload 提交完成', result)
        return 0
    except ValidationError as exc:
        print_failure(f'❌ upload 失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ upload 失败：{exc}', error_code='UPLOAD_UNEXPECTED')
        return 1
