#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _const import DEFAULT_MXOU_BASE_URL, get_config_profile
from _errors import ConfigError
from _output import print_failure, print_success
from capabilities.configure import service


def _missing_items(cfg: dict) -> list[str]:
    missing: list[str] = []
    if not cfg.get('ali_1688_ak'):
        missing.append('1688 AK')
    if not (cfg.get('ozon_client_id') and cfg.get('ozon_api_key')):
        missing.append('Ozon 店铺配置')
    if not cfg.get('mxou_token'):
        missing.append('mxou token')
    return missing


def _config_readiness(cfg: dict) -> dict:
    return {
        'store': get_config_profile(),
        'ali_1688_ak_ready': bool(cfg.get('ali_1688_ak')),
        'ozon_ready': bool(cfg.get('ozon_client_id') and cfg.get('ozon_api_key')),
        'mxou_ready': bool(cfg.get('mxou_token')),
        'cos_ready': bool(cfg.get('cos_secret_id') and cfg.get('cos_bucket') and cfg.get('cos_region') and cfg.get('cos_public_domain')),
        'publish_flow_ready': bool(cfg.get('ali_1688_ak') and cfg.get('ozon_client_id') and cfg.get('ozon_api_key') and cfg.get('mxou_token')),
    }


def _guide_steps(missing_items: list[str]) -> list[str]:
    steps = ['python3 cli.py configure status']
    if '1688 AK' in missing_items:
        steps.append('python3 cli.py configure 1688 --ak "<YOUR_AK>"')
    if 'Ozon 店铺配置' in missing_items:
        steps.append('python3 cli.py configure ozon --client-id "<ID>" --api-key "<KEY>"')
    if 'mxou token' in missing_items:
        steps.append('python3 cli.py configure mxou --token "<TOKEN>"')
    return steps


def _guide_markdown(cfg: dict) -> str:
    missing_items = _missing_items(cfg)
    readiness = _config_readiness(cfg)
    if not missing_items:
        return (
            '## 配置状态\n\n'
            f'当前店铺配置：`{readiness["store"]}`\n\n'
            '统一铺货主流程所需配置已齐全，可以直接执行：\n\n'
            '```bash\n'
            'python3 cli.py publish_flow --query "保温杯" --poll-status\n'
            '```'
        )

    lines = [
        '## 当前缺失配置引导',
        '',
        f'当前店铺配置：`{readiness["store"]}`',
        '',
        '在执行 1688 → 制图 → Ozon 主流程前，请先补齐以下缺失项：',
        '',
    ]
    for index, item in enumerate(missing_items, start=1):
        if item == '1688 AK':
            lines.append(f'{index}. 1688 AK')
        elif item == 'Ozon 店铺配置':
            lines.append(f'{index}. Ozon 店铺 `client_id / api_key`')
        elif item == 'mxou token':
            lines.append(f'{index}. mxou 图像 token（需到 `{DEFAULT_MXOU_BASE_URL}` 注册获取）')
    ready_count = sum(1 for key in ['ali_1688_ak_ready', 'ozon_ready', 'mxou_ready', 'cos_ready'] if readiness[key])
    lines.extend(['', f'当前已就绪 {ready_count}/4 项：'])
    lines.append(f'- 1688 AK：{"已配置" if readiness["ali_1688_ak_ready"] else "未配置"}')
    lines.append(f'- Ozon 店铺：{"已配置" if readiness["ozon_ready"] else "未配置"}')
    lines.append(f'- mxou token：{"已配置" if readiness["mxou_ready"] else "未配置"}')
    lines.append(f'- COS 公共存储：{"内置" if readiness["cos_ready"] else "未就绪"}')
    lines.extend(['', '推荐下一步：', '', '```bash'])
    lines.extend(_guide_steps(missing_items))
    lines.extend([
        '```',
        '',
        '配置完成后再执行：',
        '',
        '```bash',
        'python3 cli.py publish_flow --query "保温杯" --poll-status',
        '```',
    ])
    return '\n'.join(lines)


def _mask_config(cfg: dict) -> dict:
    masked = dict(cfg)
    for k in ['ali_1688_ak', 'ozon_api_key', 'mxou_token', 'cos_secret_id']:
        v = masked.get(k)
        if v:
            masked[k] = f"{str(v)[:4]}****{str(v)[-4:]}" if len(str(v)) >= 8 else '****'
    masked['store'] = get_config_profile()
    if masked.get('cos_bucket'):
        masked['cos_secret_key'] = 'stored_in_keyring_or_env'
    return masked


COMMAND_NAME = 'configure'
COMMAND_DESC = '统一配置 1688 AK / Ozon / mxou（支持多店铺）'


def _parse_store(argv: list[str]) -> tuple[str | None, list[str]]:
    args = list(argv)
    store = None
    for i, token in enumerate(list(args)):
        if token == '--store' and i + 1 < len(args):
            store = args[i + 1].strip()
            del args[i:i + 2]
            break
    return store, args


def main(args: list[str] | None = None):
    raw_args = args if args is not None else sys.argv[1:]
    store, parsed_args = _parse_store(raw_args)
    if store:
        os.environ['POUNDING_OZON_STORE'] = store
        os.environ['UNIFIED_1688_OZON_STORE'] = store

    parser = argparse.ArgumentParser(description='统一配置能力')
    sub = parser.add_subparsers(dest='target')

    sub.add_parser('status', help='查看当前配置状态')
    sub.add_parser('guide', help='查看首次使用配置引导')

    p_ak = sub.add_parser('1688', help='配置 1688 AK')
    p_ak.add_argument('--ak', required=True, help='1688 AK')

    p_ozon = sub.add_parser('ozon', help='配置 Ozon 店铺')
    p_ozon.add_argument('--client-id', required=True)
    p_ozon.add_argument('--api-key', required=True)
    p_ozon.add_argument('--currency', default=None, choices=['RUB', 'CNY', 'USD', 'EUR'])

    p_mxou = sub.add_parser('mxou', help='配置 mxou 图像能力')
    p_mxou.add_argument('--token', required=True)

    p_cos = sub.add_parser('cos', help='配置 COS 公共存储（视频上传用）')
    p_cos.add_argument('--secret-id', required=True)
    p_cos.add_argument('--secret-key', required=True)
    p_cos.add_argument('--bucket', required=True)
    p_cos.add_argument('--region', required=True)
    p_cos.add_argument('--public-domain', required=True)
    p_cos.add_argument('--public-prefix', default='public')

    p_video = sub.add_parser('video', help='配置本地商品视频生成')
    p_video.add_argument('--enabled', required=True, choices=['true', 'false'])
    p_video.add_argument('--seconds-per-image', type=float, default=None)
    p_video.add_argument('--include-bgm', choices=['true', 'false'], default=None)
    p_video.add_argument('--bgm-path', default=None)

    sub.add_parser('clear', help='清空当前店铺配置')

    parsed = parser.parse_args(parsed_args)

    try:
        if parsed.target == 'guide':
            cfg = service.get_status().to_dict()
            missing_items = _missing_items(cfg)
            print_success(_guide_markdown(cfg), {
                'store': get_config_profile(),
                'missing_items': missing_items,
                'next_steps': _guide_steps(missing_items),
            })
            return 0

        if not parsed.target or parsed.target == 'status':
            cfg = service.get_status().to_dict()
            print_success('当前统一配置状态\n\n' + _guide_markdown(cfg), {
                **_mask_config(cfg),
                'readiness': _config_readiness(cfg),
                'missing_items': _missing_items(cfg),
            })
            return 0

        if parsed.target == '1688':
            cfg = service.set_1688_ak(parsed.ak)
            print_success('1688 AK 配置成功', _mask_config(cfg.to_dict()))
            return 0

        if parsed.target == 'ozon':
            cfg = service.set_ozon(parsed.client_id, parsed.api_key, parsed.currency)
            print_success('Ozon 店铺配置成功', _mask_config(cfg.to_dict()))
            return 0

        if parsed.target == 'mxou':
            cfg = service.set_mxou(parsed.token)
            print_success('mxou 配置成功', _mask_config(cfg.to_dict()))
            return 0

        if parsed.target == 'cos':
            cfg = service.set_cos(
                parsed.secret_id,
                parsed.bucket,
                parsed.region,
                parsed.public_domain,
                public_prefix=parsed.public_prefix,
                secret_key=parsed.secret_key,
            )
            print_success('COS 配置成功（SecretKey 已写入系统 keyring）', _mask_config(cfg.to_dict()))
            return 0

        if parsed.target == 'video':
            cfg = service.set_video(
                parsed.enabled == 'true',
                parsed.seconds_per_image,
                None if parsed.include_bgm is None else parsed.include_bgm == 'true',
                parsed.bgm_path,
            )
            print_success('本地视频配置成功', _mask_config(cfg.to_dict()))
            return 0

        if parsed.target == 'clear':
            service.clear_config()
            print_success('当前店铺配置已清空', {'store': get_config_profile()})
            return 0

        print_failure('未知配置目标', error_code='UNKNOWN_CONFIG_TARGET')
        return 1
    except ConfigError as exc:
        print_failure(f'❌ 配置失败：{exc.message}', error_code=exc.error_code)
        return 1
    except Exception as exc:
        print_failure(f'❌ 配置失败：{exc}', error_code='CONFIG_UNEXPECTED_ERROR')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
