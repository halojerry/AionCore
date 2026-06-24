---
name: pounding-ozon-assistant
description: 1688→Ozon 跨境电商。上架、跟卖、翻新、变体、选品。客户端采集数据，管线(n8n)处理全部 Ozon 逻辑。
version: 0.7.0
---

# pounding-ozon v0.7.0

工作目录 `pounding-ozon-hybrid/`。全部命令用 `/usr/bin/python3`。

**架构**: 客户端采集 1688 数据 → POST n8n webhook → 管线处理(类目/属性/定价/图片/上架/自查)

## 每次开始

```bash
/usr/bin/python3 scripts/cli.py configure
```

JSON 返回。`missing` 不为空按 `user_action` 处理。`cdp.login_required`=true 提醒用户开 Chrome 登录 1688。

## 命令

```bash
# 选品
/usr/bin/python3 scripts/cli.py find-supply "关键词" --page-size 5

# 上架
/usr/bin/python3 scripts/cli.py publish-new --item-id <ID> --detail-url <URL> --category-query <类目> --poll

# 上架(不等待)
/usr/bin/python3 scripts/cli.py publish-new --item-id <ID> --detail-url <URL> --category-query <类目>

# 查进度
/usr/bin/python3 scripts/cli.py poll --task-id <task_id>

# 跟卖
/usr/bin/python3 scripts/cli.py follow-sell --sku <SKU> --offer-id <OfferID>

# 翻新
/usr/bin/python3 scripts/cli.py refresh --product-id <OzonID>

# 变体
/usr/bin/python3 scripts/cli.py publish-variant --family-title "Название" --variants '[...]'

# 搜索1688（纯API，无CDP）
/usr/bin/python3 scripts/cli.py search "关键词" --page 1 --page-size 5

# CDP抓取详情
/usr/bin/python3 scripts/cli.py probe --url <1688链接>

# 批量修复价格（扫描¥100/1300默认价）
/usr/bin/python3 scripts/cli.py fix-prices --dry-run
/usr/bin/python3 scripts/cli.py fix-prices --product-id <OzonID> --price <新价格>
```

## 类目关键词

帐篷/天幕/睡袋→帐篷 | 保温杯/水壶→保温杯 | 背包/手提包→背包 | 灯具/台灯→灯具 | 收纳盒→收纳盒 | 手机壳→手机壳 | 瑜伽垫→瑜伽垫 | 碗→碗

## JSON 返回值

| key | 在哪 | 含义 |
|-----|------|------|
| `ok` | 全部 | true=正常 false=看error |
| `task_id` | publish-new | 传给poll查进度 |
| `ozon_task_id` | poll成功 | Ozon导入任务ID |
| `stage` | publish-new,poll | submitted/succeeded/blocked/failed/timeout |
| `stages` | poll | 各节点详情 |
| `items` | find-supply | 商品列表(product_id/title/price/detail_url) |

## 严禁

- ❌ import `.py` 模块
- ❌ 构造 HTTP 请求/webhook URL
- ❌ 手动做管线的事
- ❌ 编辑 `.env` 以外文件
- ❌ 普通 `python3`(必须 `/usr/bin/python3`)
