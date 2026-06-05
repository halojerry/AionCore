#!/usr/bin/env python3
from __future__ import annotations

from models.contracts import AssetManifest, CategoryResolution, NormalizedProductDraft, ResolvedAttributeSet, RuntimeConfig
from lib.payload_builder import build_payload


def build_import_payload(config: RuntimeConfig, draft: NormalizedProductDraft, category: CategoryResolution,
                         attrs: ResolvedAttributeSet, assets: AssetManifest):
    return build_payload(config, draft, category, attrs, assets)
