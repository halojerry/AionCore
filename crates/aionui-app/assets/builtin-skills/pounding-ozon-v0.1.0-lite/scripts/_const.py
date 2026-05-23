#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

SKILL_VERSION = '0.1.0'
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

RUNTIME_DIRS = (
    DATA_DIR / 'config',
    DATA_DIR / 'manual',
    DATA_DIR / 'managed',
    DATA_DIR / 'ozon',
    DATA_DIR / 'ozon' / 'properties',
    DATA_DIR / 'ozon' / 'dictionaries',
    DATA_DIR / 'ozon' / 'dictionary_shared',
    DATA_DIR / 'ozon' / 'prewarm_reports',
)
for runtime_dir in RUNTIME_DIRS:
    runtime_dir.mkdir(parents=True, exist_ok=True)


def get_config_dir() -> Path:
    path = DATA_DIR / 'config'
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_profile() -> str:
    return (
        os.environ.get('POUNDING_OZON_STORE', '').strip()
        or os.environ.get('UNIFIED_1688_OZON_STORE', '').strip()
        or 'default'
    )


def resolve_input_path(raw_path: str | os.PathLike[str], *, must_exist: bool = False) -> Path:
    raw = str(raw_path).strip()
    if not raw:
        path = SKILL_ROOT
    else:
        candidate = Path(raw).expanduser()
        path = candidate if candidate.is_absolute() else (SKILL_ROOT / candidate)
    path = path.resolve()
    if must_exist and not path.exists():
        raise FileNotFoundError(f'路径不存在: {path}')
    return path


def get_config_file() -> Path:
    return get_config_dir() / f'runtime_config.{get_config_profile()}.json'


def get_legacy_config_file() -> Path:
    return get_config_dir() / 'runtime_config.json'


CONFIG_DIR = get_config_dir()
CONFIG_PROFILE = get_config_profile()
CONFIG_FILE = get_config_file()
LEGACY_CONFIG_FILE = get_legacy_config_file()

DEFAULT_OZON_CURRENCY = 'RUB'
DEFAULT_MXOU_BASE_URL = 'https://api.mxou.cn'
DEFAULT_MXOU_MODE = 'mxou_images'
DEFAULT_IMAGE_ASPECT = '1024x1536'
DEFAULT_COS_SECRET_ID = ''
DEFAULT_COS_SECRET_KEY = ''
DEFAULT_COS_BUCKET = 'yss-1256275613'
DEFAULT_COS_REGION = 'ap-guangzhou'
DEFAULT_COS_PUBLIC_DOMAIN = 'https://yss-1256275613.cos.ap-guangzhou.myqcloud.com'
DEFAULT_COS_PUBLIC_PREFIX = 'public'
DEFAULT_MAX_BATCH_SIZE = 100
DEFAULT_CATEGORY_CONFIDENCE_THRESHOLD = 0.85
DEFAULT_CATEGORY_MARGIN_THRESHOLD = 0.10
DEFAULT_CACHE_TTL_SECONDS = 86400
DEFAULT_PRICING_PACKAGING_COST_CNY = 3.0
DEFAULT_PRICING_COMMISSION_RATE = 0.18
DEFAULT_PRICING_FX_BUFFER_RATE = 0.06
DEFAULT_PRICING_TARGET_PROFIT_RATE = 0.25
DEFAULT_PRICING_RFBS_PROVIDER_CANDIDATES = 'RETS,OYX'
DEFAULT_PRICING_RFBS_SERVICE_CANDIDATES = 'Standard,Economy,Express'
DEFAULT_PRICING_RFBS_SELECTION_STRATEGY = 'prefer_standard'
DEFAULT_PRICING_RFBS_XLSX_PATH = ''
DEFAULT_PRICING_ALLOW_BATTERY = False
DEFAULT_PRICING_ALLOW_LIQUID = False

SKILL_NAME = 'pounding-ozon'
