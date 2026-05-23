#!/usr/bin/env python3
from __future__ import annotations

from lib.config_store import clear_all_config, clear_cos_config, configure_1688_ak, configure_cos, configure_mxou, configure_ozon, configure_video, load_config
from models.contracts import RuntimeConfig


def get_status() -> RuntimeConfig:
    return load_config()


def set_1688_ak(ak: str) -> RuntimeConfig:
    return configure_1688_ak(ak)


def set_ozon(client_id: str, api_key: str, currency: str | None = None) -> RuntimeConfig:
    return configure_ozon(client_id, api_key, currency)


def set_mxou(token: str) -> RuntimeConfig:
    return configure_mxou(token)


def set_cos(
    secret_id: str,
    bucket: str,
    region: str,
    public_domain: str,
    *,
    public_prefix: str | None = None,
    secret_key: str | None = None,
) -> RuntimeConfig:
    return configure_cos(
        secret_id,
        bucket,
        region,
        public_domain,
        public_prefix=public_prefix,
        secret_key=secret_key,
    )


def set_video(enabled: bool, seconds_per_image: float | None = None, include_bgm: bool | None = None, bgm_path: str | None = None) -> RuntimeConfig:
    return configure_video(enabled, seconds_per_image, include_bgm, bgm_path)


def clear_config() -> None:
    clear_cos_config()
    clear_all_config()
