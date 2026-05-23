#!/usr/bin/env python3
from __future__ import annotations

from models.contracts import AssetManifest, NormalizedProductDraft
from lib.image_manifest_builder import (
    build_manifest_plan,
    build_stub_asset_manifest,
    execute_manifest_generation,
    regenerate_manifest_slots,
)


def plan_image_pipeline(draft: NormalizedProductDraft) -> dict:
    return build_manifest_plan(draft)


def build_stub_manifest(draft: NormalizedProductDraft) -> AssetManifest:
    return build_stub_asset_manifest(draft)


def execute_image_pipeline(
    draft: NormalizedProductDraft,
    max_rounds: int = 2,
    max_polls: int = 20,
    poll_interval_seconds: float = 3.0,
    submit_timeout_seconds: int = 150,
    max_parallel_followups: int = 3,
) -> dict:
    return execute_manifest_generation(
        draft,
        max_rounds=max_rounds,
        max_polls=max_polls,
        poll_interval_seconds=poll_interval_seconds,
        submit_timeout_seconds=submit_timeout_seconds,
        max_parallel_followups=max_parallel_followups,
    )


def repair_image_pipeline_slots(
    draft: NormalizedProductDraft,
    current_manifest: AssetManifest,
    slots: list[str],
    max_rounds: int = 2,
    max_polls: int = 20,
    poll_interval_seconds: float = 3.0,
    submit_timeout_seconds: int = 150,
    max_parallel_followups: int = 3,
) -> dict:
    return regenerate_manifest_slots(
        draft,
        current_manifest,
        slots,
        max_rounds=max_rounds,
        max_polls=max_polls,
        poll_interval_seconds=poll_interval_seconds,
        submit_timeout_seconds=submit_timeout_seconds,
        max_parallel_followups=max_parallel_followups,
    )
