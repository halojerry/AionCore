#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _const import resolve_input_path
from _errors import ConfigError
from _output import print_failure, print_success
from capabilities.image_pipeline.service import build_stub_manifest, execute_image_pipeline, plan_image_pipeline
from models.contracts import NormalizedProductDraft

COMMAND_NAME = 'image_pipeline'
COMMAND_DESC = 'mxou 图像流程规划 / stub 资产清单'


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description='图像流程')
    parser.add_argument('--draft-file', required=True)
    parser.add_argument('--stub-manifest', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--max-rounds', type=int, default=2)
    parser.add_argument('--max-polls', type=int, default=20)
    parser.add_argument('--poll-interval-seconds', type=float, default=3.0)
    parser.add_argument('--submit-timeout-seconds', type=int, default=150)
    parser.add_argument('--max-parallel-followups', type=int, default=3)
    parsed = parser.parse_args(args if args is not None else sys.argv[1:])
    try:
        draft = NormalizedProductDraft(**json.loads(resolve_input_path(parsed.draft_file, must_exist=True).read_text(encoding='utf-8')))
        if parsed.stub_manifest:
            manifest = build_stub_manifest(draft)
            print_success('已生成 stub AssetManifest', {
                'total_assets': manifest.total_assets,
                'primary_image': manifest.primary_image,
                'white_background_image': manifest.white_background_image,
                'generated_images': manifest.generated_images,
            })
            return 0
        if parsed.execute:
            result = execute_image_pipeline(
                draft,
                max_rounds=parsed.max_rounds,
                max_polls=parsed.max_polls,
                poll_interval_seconds=parsed.poll_interval_seconds,
                submit_timeout_seconds=parsed.submit_timeout_seconds,
                max_parallel_followups=parsed.max_parallel_followups,
            )
            manifest = result['manifest']
            print_success('已执行 mxou 图像流程', {
                'total_assets': manifest.total_assets,
                'primary_image': manifest.primary_image,
                'white_background_image': manifest.white_background_image,
                'generated_images': manifest.generated_images,
                'moderation_flags': manifest.moderation_flags,
                'generation_records': manifest.generation_records,
                'retry_count': manifest.retry_count,
                'pending_slots': result['pending_slots'],
                'max_parallel_followups': result.get('max_parallel_followups'),
            })
            return 0
        plan = plan_image_pipeline(draft)
        print_success('已生成 mxou 图像请求计划', plan)
        return 0
    except ConfigError as exc:
        print_failure(f'❌ image pipeline 失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ image pipeline 失败：{exc}', error_code='IMAGE_PIPELINE_UNEXPECTED')
        return 1
