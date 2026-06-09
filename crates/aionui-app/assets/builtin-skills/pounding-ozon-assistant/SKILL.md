---
name: pounding-ozon-assistant
description: |
  1688 → Ozon 全链路。跟卖、新上架、变体合并、翻新、选品找货源、制图。
version: 0.4.0
---

# pounding-ozon-assistant v0.3.6

## 全局规则

1. **永远先调 `check_config()`**——缺凭据立即停止，原样读出 `user_action` 给用户
2. **只用下面列出的函数**——不要自己拼 URL、不要自己发 HTTP、不要调未列出的内部函数
3. **一个 Worker 一个入口函数**——不要拆成多步手工拼接（轮询 `poll_pipeline_task` 除外，这是 Worker A 的第二步）

## 7 个入口函数（只能调这些）

```python
from scripts.lib.cloud_client import (
    publish_product_new,      # Worker A — 上架
    follow_sell_cloud,        # Worker B — 跟卖
    refresh_product,          # Worker C — 翻新
    publish_variant_product,  # Worker D — 变体
    find_supply,              # Worker E — 选品
    poll_pipeline_task,       # 轮询（配合 Worker A 用）
)
from scripts.lib.config_store import check_config
```

### 1. `check_config() → dict`
- 返回 `{missing: [...], present: [...], user_action: str|None}`
- `user_action` 不为 None 时**原样告诉用户**，不要自己处理

### 2. `publish_product_new(*, item_id, detail_url, title, price, category_query, poll, store_id) → dict` — Worker A
```python
# 所有参数必须用关键字传参（keyword-only）
result = publish_product_new(
    item_id="679615860551",                         # 1688 商品 ID（必填）
    detail_url="https://detail.1688.com/offer/...",  # 1688 链接（必填）
    title="Товар",                                   # 俄语标题（可选）
    price="1500",                                    # ₽（可选）
    category_query="рюкзак",                         # 类目关键词（可选）
    poll=False,                                      # False=不轮询，用 poll_pipeline_task
)
# → {ok, task_id, stage, category, enriched: {images, weight_grams, ...}, error, user_action}
```
Agent 流程：`check_config` → `publish_product_new` → `poll_pipeline_task`。中间所有步骤（1688 采集、CDP 探针、类目匹配、制图、上传）全自动，不要手工介入。

### 3. `follow_sell_cloud(*, sku, offer_id, name, price) → dict` — Worker B
```python
result = follow_sell_cloud(sku=123456, offer_id="BO-001", name="Товар", price="1000")
# → {ok, ozon_task_id, unmatched_sku_list}
```
跟卖提交后云端自动轮询 Ozon 导入状态，成功则 copy_and_update，失败/被拒则走新建上架。

### 4. `refresh_product(*, product_id, offer_id, name, ...) → dict` — Worker C
```python
result = refresh_product(product_id="4118215164", offer_id="BO-011", name="Новое название")
# → {ok, product_id, ozon_task_id}
```

### 5. `publish_variant_product(*, family_title, variants, ...) → dict` — Worker D
```python
result = publish_variant_product(
    family_title="Семейство товаров",
    variants=[{"sku_id": "red-m", "sku_title": "Красный M", "price": "1000", "attributes": {"color": "красный"}}],
)
# → {ok, task_id, ozon_task_id}
```

### 6. `find_supply(*, query, page_size=5) → dict` — Worker E
```python
result = find_supply(query="рюкзак")
# → {ok, items: [{title, price, itemId, detailUrl, ...}], count, hint}
```
Agent 流程：`find_supply` → 展示候选给用户 → 用户选 → `publish_product_new(item_id=选中的itemId, detail_url=选中的detailUrl)`

### 7. `poll_pipeline_task(task_id, interval_sec=30, max_wait_sec=600) → dict`
```python
final = poll_pipeline_task(result["task_id"])
# → {status: "succeeded"|"failed"|"timeout", ozon_task_id, stages}
```

## 配置

| 凭据 | 设置方式 | 说明 |
|------|---------|------|
| `MXOU_TOKEN` | 用户在终端 `export MXOU_TOKEN="sk-xxx"` | 云端鉴权+制图。Agent **绝不**写入文件（会被脱敏） |
| `ALI_1688_AK` | 写入 `.env` | 1688 API |
| `OZON_CLIENT_ID` | 写入 `.env` | Ozon 卖家 ID |
| `OZON_API_KEY` | 写入 `.env` | Ozon API Key |

`check_config()` 自动检测缺失项，返回 `user_action` 指导用户配置。

## 返回结果

| status | 对用户说 |
|--------|---------|
| `succeeded` | "✅ 上架成功！Ozon 任务: {ozon_task_id}" |
| `blocked` | "⛔ 被阻断：{原因}。" |
| `failed` | "❌ 失败：{错误}。重试或检查配置" |

## 严禁

- ❌ 跳过 `check_config`
- ❌ 自己拼 webhook URL 或发 HTTP 请求
- ❌ 调未列出的内部函数（如 `build_envelope`、`submit_task`、`search_products`、`search_categories_locally`——这些是内部实现，Agent 不要碰）
- ❌ 缺配置继续执行
- ❌ 把 `MXOU_TOKEN` 写入文件
- ❌ 编造未返回的数据
