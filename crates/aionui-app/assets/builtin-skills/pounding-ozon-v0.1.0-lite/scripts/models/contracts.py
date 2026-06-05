#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

from _const import (
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_CATEGORY_CONFIDENCE_THRESHOLD,
    DEFAULT_CATEGORY_MARGIN_THRESHOLD,
    DEFAULT_IMAGE_ASPECT,
    DEFAULT_COS_BUCKET,
    DEFAULT_COS_PUBLIC_DOMAIN,
    DEFAULT_COS_PUBLIC_PREFIX,
    DEFAULT_COS_REGION,
    DEFAULT_COS_SECRET_ID,
    DEFAULT_MAX_BATCH_SIZE,
    DEFAULT_MXOU_BASE_URL,
    DEFAULT_MXOU_MODE,
    DEFAULT_OZON_CURRENCY,
    DEFAULT_PRICING_ALLOW_BATTERY,
    DEFAULT_PRICING_ALLOW_LIQUID,
    DEFAULT_PRICING_COMMISSION_RATE,
    DEFAULT_PRICING_FX_BUFFER_RATE,
    DEFAULT_PRICING_PACKAGING_COST_CNY,
    DEFAULT_PRICING_RFBS_PROVIDER_CANDIDATES,
    DEFAULT_PRICING_RFBS_SELECTION_STRATEGY,
    DEFAULT_PRICING_RFBS_SERVICE_CANDIDATES,
    DEFAULT_PRICING_RFBS_XLSX_PATH,
    DEFAULT_PRICING_TARGET_PROFIT_RATE,
)


@dataclass
class RuntimeConfig:
    ali_1688_ak: str | None = None
    ozon_client_id: str | None = None
    ozon_api_key: str | None = None
    ozon_currency: str | None = None
    cos_secret_id: str | None = DEFAULT_COS_SECRET_ID
    cos_bucket: str | None = DEFAULT_COS_BUCKET
    cos_region: str | None = DEFAULT_COS_REGION
    cos_public_domain: str | None = DEFAULT_COS_PUBLIC_DOMAIN
    cos_public_prefix: str | None = DEFAULT_COS_PUBLIC_PREFIX
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    mxou_token: str | None = None
    mxou_base_url: str = DEFAULT_MXOU_BASE_URL
    mxou_mode: str = DEFAULT_MXOU_MODE
    image_aspect: str = DEFAULT_IMAGE_ASPECT
    max_batch_size: int = DEFAULT_MAX_BATCH_SIZE
    category_confidence_threshold: float = DEFAULT_CATEGORY_CONFIDENCE_THRESHOLD
    category_margin_threshold: float = DEFAULT_CATEGORY_MARGIN_THRESHOLD
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    pricing_packaging_cost_cny: float = DEFAULT_PRICING_PACKAGING_COST_CNY
    pricing_commission_rate: float = DEFAULT_PRICING_COMMISSION_RATE
    pricing_fx_buffer_rate: float = DEFAULT_PRICING_FX_BUFFER_RATE
    pricing_target_profit_rate: float = DEFAULT_PRICING_TARGET_PROFIT_RATE
    pricing_rfbs_provider_candidates: str = DEFAULT_PRICING_RFBS_PROVIDER_CANDIDATES
    pricing_rfbs_provider_overrides: dict[str, dict[str, float]] = field(default_factory=dict)
    pricing_rfbs_service_candidates: str = DEFAULT_PRICING_RFBS_SERVICE_CANDIDATES
    pricing_rfbs_selection_strategy: str = DEFAULT_PRICING_RFBS_SELECTION_STRATEGY
    pricing_rfbs_xlsx_path: str | None = DEFAULT_PRICING_RFBS_XLSX_PATH or None
    pricing_allow_battery: bool = DEFAULT_PRICING_ALLOW_BATTERY
    pricing_allow_liquid: bool = DEFAULT_PRICING_ALLOW_LIQUID
    video_enabled: bool = False
    video_seconds_per_image: float = 1.8
    video_include_bgm: bool = False
    video_bgm_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceProductSnapshot:
    source_item_id: str
    source_category_ids: list[str] = field(default_factory=list)
    sku_count: int = 0
    source_images: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceInquiryRequest:
    offer_name: str
    count: str
    demand: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedProductDraft:
    source_item_id: str
    sku_count: int
    source_category_ids: list[str] = field(default_factory=list)
    title: str = ''
    description: str = ''
    attributes: dict[str, Any] = field(default_factory=dict)
    source_images: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    variants: list[dict[str, Any]] = field(default_factory=list)
    family_key: str | None = None
    family_label: str | None = None
    family_partition: dict[str, Any] = field(default_factory=dict)


@dataclass
class CategoryResolution:
    description_category_id: str | None = None
    type_id: str | None = None
    confidence: float = 0.0
    top_candidates: list[dict[str, Any]] = field(default_factory=list)
    cache_version: str | None = None
    cache_age_seconds: int | None = None
    explanation: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolvedAttributeSet:
    required_attributes: dict[str, Any] = field(default_factory=dict)
    optional_attributes: dict[str, Any] = field(default_factory=dict)
    missing_required_attributes: list[dict[str, Any]] = field(default_factory=list)
    skipped_optional_reason_codes: dict[str, str] = field(default_factory=dict)
    resolution_notes: list[str] = field(default_factory=list)


@dataclass
class AssetManifest:
    total_assets: int = 0
    primary_image: str | None = None
    white_background_image: str | None = None
    generated_images: list[str] = field(default_factory=list)
    moderation_flags: list[str] = field(default_factory=list)
    generation_records: list[dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0


@dataclass
class OzonImportPayload:
    payload_hash: str
    items: list[dict[str, Any]] = field(default_factory=list)
    complex_attributes: list[dict[str, Any]] = field(default_factory=list)
    video_debug: dict[str, Any] = field(default_factory=dict)
    item_debugs: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FamilyPartitionVariant:
    variant_key: str
    sku_id: str
    sku_title: str
    price: Any = None
    attributes: dict[str, Any] = field(default_factory=dict)
    source_images: list[str] = field(default_factory=list)
    split_reason_codes: list[str] = field(default_factory=list)


@dataclass
class FamilyPartitionGroup:
    family_key: str
    family_label: str
    merge_group_value: str
    family_level_attribute_hints: dict[str, Any] = field(default_factory=dict)
    family_level_asset_hints: dict[str, Any] = field(default_factory=dict)
    variants: list[FamilyPartitionVariant] = field(default_factory=list)
    split_reason_codes: list[str] = field(default_factory=list)
    source_item_id: str = ''


@dataclass
class FamilyPartitionResult:
    source_item_id: str
    family_groups: list[FamilyPartitionGroup] = field(default_factory=list)
    mixed_family: bool = False
    split_reason_codes: list[str] = field(default_factory=list)


@dataclass
class ImportAttemptRecord:
    correlation_id: str
    payload_hash: str
    batch_id: str
    task_id: str | None = None
    attempt_number: int = 1
    retry_state: str = 'not_started'


ImportOutcome = Literal['success', 'partial_success', 'retryable_failure', 'blocked_failure', 'ambiguous']


@dataclass
class ImportResult:
    outcome: ImportOutcome
    per_offer_results: list[dict[str, Any]] = field(default_factory=list)
    dead_letter_reason: str | None = None
    retry_eligible: bool = False
