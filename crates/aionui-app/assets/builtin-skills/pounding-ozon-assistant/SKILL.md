---
name: pounding-ozon-assistant
description: 1688→Ozon 全链路。上架、跟卖、翻新、变体、选品。
version: 0.5.0
---

# pounding-ozon v0.5.0

工作目录：`pounding-ozon-assistant/`（所有命令从仓库根目录的此子目录执行）

## 每次开始前

```bash
python3 scripts/cli.py configure
```
返回 JSON。`missing` 不为空时，把 `user_action` 字段原样告诉用户。
`user_action` 为 null 时直接继续。

## 命令速查

| 用户意图 | 命令 |
|---------|------|
| 上架新品 | `python3 scripts/cli.py publish-new --item-id 679615860551 --detail-url https://detail.1688.com/offer/679615860551.html --category-query 帐篷 --poll` |
| 上架(不等待) | `python3 scripts/cli.py publish-new --item-id 679615860551 --detail-url https://detail.1688.com/offer/679615860551.html --category-query 帐篷` |
| 跟卖 | `python3 scripts/cli.py follow-sell --sku 123456 --offer-id BO-001 --name "Товар"` |
| 翻新 | `python3 scripts/cli.py refresh --product-id 4118215164 --name "Новое название"` |
| 多变体 | `python3 scripts/cli.py publish-variant --family-title "Семейство" --variants '[{"sku_id":"red","sku_title":"Красный","price":"100"}]'` |
| 选品 | `python3 scripts/cli.py find-supply "рюкзак" --page-size 5` |
| 查进度 | `python3 scripts/cli.py poll --task-id task-679615860551` |

## 参数说明

**publish-new** — 所有参数用实际值替换，不要留空：
- `--item-id` 1688 商品 ID（数字串，从选品结果或用户提供）
- `--detail-url` 1688 商品详情页完整 URL
- `--category-query` 中文类目关键词（必填，如 帐篷、睡袋、修枝剪）
- `--price` 可选，卢布售价（不填则自动计算）
- `--poll` 可选，加此标志等待管线完成（否则立即返回 task_id，稍后用 poll 查）

**follow-sell**：
- `--sku` Ozon SKU（整数）
- `--offer-id` 你在 Ozon 的 Offer ID（字符串）
- `--name` 可选，商品俄语名称

**refresh**：
- `--product-id` Ozon 商品 ID（数字串）
- `--name` 可选，新俄语标题

**publish-variant**：
- `--family-title` 族标题（俄语）
- `--variants` JSON 字符串，每个变体含 sku_id/sku_title/price

**find-supply**：
- 第一个位置参数：俄语或中文搜索关键词
- `--page-size` 可选，返回数量（默认 5）

**poll**：
- `--task-id` 从 publish-new 返回的 task_id
- `--max-wait` 可选，最长等待秒数（默认 600）

## 读懂返回 JSON

`print` 直接输出 JSON。关注这些顶层 key：

| key | 出现于 | 含义 |
|-----|-------|------|
| `ok` | 所有命令 | `true` 继续 / `false` 看 `error` |
| `task_id` | publish-new, follow-sell | 管线任务 ID，传给 `poll` |
| `ozon_task_id` | poll 成功时 | Ozon 导入任务 ID |
| `items` | find-supply | 商品列表，每项含 `product_id`/`title`/`price`/`detail_url` |
| `status` | poll | `succeeded` `blocked` `failed` `timeout` |
| `stages` | poll | 各阶段详情（`Category` `Upload` 等） |
| `error` | 失败时 | 人类可读错误 |
| `user_action` | configure | 引导用户操作的话术，原样展示 |

## 不能做的事

这个 skill 仅提供 CLI。Agent 不要 import 或调用本仓库的任何 `.py` 模块，不要构造 HTTP 请求，不要编辑 `.env` 之外的文件。
