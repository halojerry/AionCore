#!/usr/bin/env python3
"""pounding-ozon CLI — 统一入口。Agent 应只通过本 CLI 调用系统，不直接调内部函数。

用法:
  python3 cli.py configure          # 检查/设置配置
  python3 cli.py find-supply "рюкзак"     # Worker E — 选品搜索
  python3 cli.py publish-new --item-id <1688产品ID> --detail-url <链接> --category-query <类目> --price <₽>
  python3 cli.py follow-sell --sku <SKU> --offer-id <ID>
  python3 cli.py refresh --product-id <Ozon产品ID>
  python3 cli.py publish-variant --family-title <名称> --variants '[{...}]'
  python3 cli.py poll --task-id <管线任务ID>
  python3 cli.py search "关键词"           # 搜索 1688
  python3 cli.py probe --url <1688链接>    # 浏览器抓取
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

# Load .env early so sub-commands see credentials
try:
    from scripts.lib.config_store import load_env_file
    load_env_file()
except Exception as e:
    logger.debug('load_env_file failed: %s', e)

_VERBOSE = False


def _log(msg: str) -> None:
    if _VERBOSE:
        print(f'[pounding] {msg}', file=sys.stderr)


def _out(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


# ═══════════════════════════════════════════════════════════════════════════
# Worker commands (map to cloud_client entry functions)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_update(args: argparse.Namespace) -> int:
    """检查并下载最新版本."""
    from scripts.lib.update import check_skill_version, download_skill_update
    result = check_skill_version()
    if not result.get("update_available"):
        _out({"ok": True, "message": "已是最新版本 v" + result.get("current_version", ""),
              "current": result.get("current_version"), "latest": result.get("latest_version")})
        return 0
    download = download_skill_update(result.get("latest_version", ""), result.get("changed_files", []))
    _out(download)
    return 0 if download.get("ok") else 1


def cmd_bootstrap(args: argparse.Namespace) -> int:
    """首次安装 — 从 COS 下载完整技能包."""
    from scripts.lib.update import bootstrap_skill
    result = bootstrap_skill()
    _out(result)
    return 0 if result.get("ok") else 1



def cmd_configure(args: argparse.Namespace) -> int:
    """Check config, set a key, or configure a store profile."""
    from scripts.lib.config_store import check_config

    # Store profile setup
    if args.store and (args.currency or args.shipping):
        from scripts.lib.config_store import write_store_profile
        provider, service = "", ""
        if args.shipping:
            parts = args.shipping.split(",")
            provider = parts[0].strip()
            service = parts[1].strip() if len(parts) > 1 else ""
        profile = write_store_profile(args.store, args.currency, provider, service)
        _out({"ok": True, "store_id": args.store, "profile": profile, "message": "店铺配置已保存到 ~/.pounding/config.json"})
        return 0

    cfg = check_config()
    if args.key:
        from scripts.lib.config_store import write_env_file
        write_env_file(args.key, args.value)
        cfg = check_config()
    _out(cfg)
    return 0 if not cfg.get("missing") else 1


def cmd_find_supply(args: argparse.Namespace) -> int:
    """Worker E — 搜索 1688 货源."""
    from scripts.lib.cloud_client import find_supply

    _log(f'选品搜索: {args.query}')
    result = find_supply(query=args.query, page_size=args.page_size)
    _log(f'找到 {result.get("count", 0)} 个产品')
    _out(result)
    return 0 if result.get("ok") else 1


def cmd_publish_new(args: argparse.Namespace) -> int:
    """Worker A — 上架新品（1688→Ozon 全流程）."""
    from scripts.lib.cloud_client import publish_product_new
    import logging as _logging

    if _VERBOSE:
        _logging.basicConfig(level=_logging.INFO, format='[pounding] %(message)s', stream=sys.stderr)

    _log(f'上架: item_id={args.item_id}')
    result = publish_product_new(
        item_id=args.item_id,
        detail_url=args.detail_url,
        title=args.title or "",
        price=args.price or "",
        category_query=args.category_query or "",
        description=args.description or "",
        poll=args.poll,
        poll_interval_sec=args.poll_interval,
        max_poll_sec=args.max_poll_sec,
    )
    _out(result)
    return 0 if result.get("ok") else 1


def cmd_follow_sell(args: argparse.Namespace) -> int:
    """Worker B — 跟卖（SKU 导入）."""
    from scripts.lib.cloud.follow_sell import follow_sell_cloud

    result = follow_sell_cloud(
        sku=args.sku,
        offer_id=args.offer_id,
        name=args.name or "",
        price=args.price or "",
    )
    _out(result)
    return 0 if result.get("ok") else 1


def cmd_refresh(args: argparse.Namespace) -> int:
    """Worker C — 翻新/更新已上架商品."""
    from scripts.lib.cloud_client import refresh_product

    result = refresh_product(
        product_id=args.product_id,
        offer_id=args.offer_id or "",
        name=args.name or "",
    )
    _out(result)
    return 0 if result.get("ok") else 1


def cmd_publish_variant(args: argparse.Namespace) -> int:
    """Worker D — 多变体上架."""
    from scripts.lib.cloud_client import publish_variant_product

    try:
        variants = json.loads(args.variants)
    except json.JSONDecodeError:
        _out({"ok": False, "error": "variants 必须为合法 JSON 字符串"})
        return 1

    result = publish_variant_product(
        family_title=args.family_title,
        variants=variants,
    )
    _out(result)
    return 0 if result.get("ok") else 1


def cmd_poll(args: argparse.Namespace) -> int:
    """轮询管线任务状态."""
    from scripts.lib.cloud_client import poll_pipeline_task

    result = poll_pipeline_task(
        args.task_id,
        interval_sec=args.interval,
        max_wait_sec=args.max_wait,
    )
    _out(result)
    return 0 if result.get("status") in ("succeeded", "timeout") else 1


# ═══════════════════════════════════════════════════════════════════════════
# Utility commands
# ═══════════════════════════════════════════════════════════════════════════

def cmd_search(args: argparse.Namespace) -> int:
    """搜索 1688 商品."""
    from scripts.lib.ak_1688_client import search_products

    if not args.query:
        _out({"error": "请提供搜索关键词"})
        return 1
    products = search_products(args.query, page=args.page, page_size=args.page_size)
    _out({"count": len(products), "products": products})
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    """浏览器抓取 1688 商品页面."""
    try:
        from scripts.capabilities.browser_probe.service import probe_1688_page
    except ImportError:
        _out({"error": "需要 playwright: pip install playwright && playwright install chromium"})
        return 1

    result = probe_1688_page(url=args.url, timeout_seconds=args.timeout)
    probe = result.get("probe", {})
    _out({
        "success": result.get("ready", False),
        "title": probe.get("title"),
        "price": probe.get("price"),
        "images": len(probe.get("images") or []),
        "attributes": len(probe.get("attributes") or []),
        "sku_count": len(probe.get("skuDetails") or []),
    })
    return 0


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    global _VERBOSE
    parser = argparse.ArgumentParser(description="pounding-ozon — 1688→Ozon 统一 CLI")
    parser.add_argument("--verbose", "-v", action="store_true", help="打印运行日志到 stderr")
    sub = parser.add_subparsers(dest="command", help="命令")

    # configure
    p = sub.add_parser("configure", help="检查/设置凭证或店铺配置")
    p.add_argument("key", nargs="?", default="", help="配置项名")
    p.add_argument("value", nargs="?", default="", help="配置值")
    p.add_argument("--store", default="", metavar="ID", help="店铺 ID (如 4718259)")
    p.add_argument("--currency", default="", metavar="CUR", help="店铺货币 (CNY/RUB)")
    p.add_argument("--shipping", default="", metavar="PROVIDER,SERVICE", help="物流方式 (如 RETS,Express)")
    p.set_defaults(func=cmd_configure)

    # find-supply (Worker E)
    p = sub.add_parser("find-supply", help="Worker E — 搜索 1688 货源")
    p.add_argument("query", help="搜索关键词 (建议俄语，如 рюкзак)")
    p.add_argument("--page-size", type=int, default=5)
    p.set_defaults(func=cmd_find_supply)

    # publish-new (Worker A)
    p = sub.add_parser("publish-new", help="Worker A — 上架新品（全流程）")
    p.add_argument("--item-id", required=True, help="1688 商品 ID")
    p.add_argument("--detail-url", required=True, help="1688 商品详情页 URL")
    p.add_argument("--title", default="", help="俄语标题（可选，自动生成）")
    p.add_argument("--price", default="", help="售价 ₽（可选，自动计算）")
    p.add_argument("--category-query", default="", help="类目关键词（中文，如 帐篷）")
    p.add_argument("--description", default="", help="产品描述")
    p.add_argument("--poll", action="store_true", help="阻塞等待管线完成")
    p.add_argument("--poll-interval", type=float, default=30.0, help="轮询间隔秒")
    p.add_argument("--max-poll-sec", type=float, default=600.0, help="最长等待秒")
    p.set_defaults(func=cmd_publish_new)

    # follow-sell (Worker B)
    p = sub.add_parser("follow-sell", help="Worker B — 跟卖 (SKU 导入)")
    p.add_argument("--sku", type=int, required=True, help="Ozon SKU")
    p.add_argument("--offer-id", required=True, help="你的 Offer ID")
    p.add_argument("--name", default="", help="商品名称")
    p.add_argument("--price", default="", help="售价 ₽")
    p.set_defaults(func=cmd_follow_sell)

    # refresh (Worker C)
    p = sub.add_parser("refresh", help="Worker C — 翻新已上架商品")
    p.add_argument("--product-id", required=True, help="Ozon 商品 ID")
    p.add_argument("--offer-id", default="", help="新 Offer ID")
    p.add_argument("--name", default="", help="新标题")
    p.set_defaults(func=cmd_refresh)

    # publish-variant (Worker D)
    p = sub.add_parser("publish-variant", help="Worker D — 多变体上架")
    p.add_argument("--family-title", required=True, help="族标题")
    p.add_argument("--variants", required=True, help='变体 JSON, 例: \'[{"sku_id":"red","sku_title":"红色","price":"100"}]\'')
    p.set_defaults(func=cmd_publish_variant)

    # poll
    p = sub.add_parser("poll", help="轮询管线任务状态")
    p.add_argument("--task-id", required=True, help="管线任务 ID")
    p.add_argument("--interval", type=float, default=30.0, help="轮询间隔秒")
    p.add_argument("--max-wait", type=float, default=600.0, help="最长等待秒")
    p.set_defaults(func=cmd_poll)

    # search
    p = sub.add_parser("search", help="搜索 1688 商品")
    p.add_argument("query", nargs="?", default="", help="搜索关键词")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--page-size", type=int, default=20)
    p.set_defaults(func=cmd_search)

    # probe
    p = sub.add_parser("probe", help="浏览器抓取 1688 商品详情")
    p.add_argument("--url", "-u", required=True, help="1688 商品链接")
    p.add_argument("--timeout", type=int, default=120, help="超时秒数")
    p.set_defaults(func=cmd_probe)

    # update — check and download latest skill version
    p = sub.add_parser("update", help="检查并下载最新版本")
    p.set_defaults(func=cmd_update)

    # bootstrap — first-run install
    p = sub.add_parser("bootstrap", help="首次安装（初始化环境）")
    p.set_defaults(func=cmd_bootstrap)

    args = parser.parse_args()
    _VERBOSE = getattr(args, 'verbose', False)

    if not args.command:
        from scripts.lib.config_store import check_config
        cfg = check_config()
        if cfg.get("missing"):
            print(f"配置缺失: {', '.join(cfg['missing'])}")
            print("运行 'cli.py configure' 查看详情")
            return 1
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
