---
name: pounding-ozon-cloud
description: |
  1688 → Ozon 全链路。跟卖、新上架、变体合并、翻新、选品找货源、制图。
---

# pounding-ozon-cloud

## 配置

| 凭据 | 层级 | 来源 | Worker 需要 |
|------|------|------|-----------|
| `MXOU_TOKEN` | 分发级 | `~/.pounding/config.json` → `api.key`（云端鉴权） | A, B, C, D |
| `MXOU_IMAGE_TOKEN` | 分发级 | `~/.pounding/config.json` → `api.key`（制图，同 key） | A, B, C, D |
| `ALI_1688_AK` | 用户级 | `.env` 或环境变量 | A, B |
| `OZON_CLIENT_ID` | 用户级 | `.env` 或环境变量 | A, B, C, D |
| `OZON_API_KEY` | 用户级 | `.env` 或环境变量 | A, B, C, D |

- **分发级凭证**（`MXOU_TOKEN`、`MXOU_IMAGE_TOKEN`）都来自 `~/.pounding/config.json` 的 `api.key`——制图和鉴权用同一个 mxou API key，随 Skill 分发给用户，**绝不写入 `.env`**。
- **用户级凭证**（`ALI_1688_AK`、`OZON_CLIENT_ID`、`OZON_API_KEY`）由 AI 助手写入 `.env` 持久化，下次对话自动加载。
- 用户说"设置 XXX=yyy"→ 写入 `.env` → 告知"已保存到 .env ✅"。
- 用户说"查看配置"→ `check_config()` 列出缺失和已配置项。
- **严禁硬编码凭据。Step 1 缺任何一项立即停止，列出缺失项。**

## CDP 浏览器是必须的

1688 API 返回文字属性但**不返回图片URL、重量、尺寸**。CDP 浏览器打开商品页采集这些数据是 Worker A 的必要步骤 (Step 2b)。

---

### Worker A：1688 → Ozon 新上架（9 步）

| # | 动作 | 函数 | 对用户说 |
|---|------|------|---------|
| 1 | 检查配置 | `check_config()` | 全部就绪→（静默）；有缺失→按 AGENTS.md「首次配置引导」逐个问答填 `.env` |
| 2 | 获取 1688 详情 | API `prod_detail` + CDP `probe_1688_page()` | "正在获取 1688 商品详情..." → "已获取详情（{N}张图，{M}个SKU）" |
| 3 | 类目匹配 | `property/lookup` → 命中则跳过；否则 `search_categories_locally()` → 用户选择 → `property/confirm` | 命中："已匹配类目：{类目名}（置信度 {X}%）"；未命中：列候选让用户选 → "已确认类目：{类目名}，已记录到云端 ✅" |
| 4 | 构建信封 | `build_envelope()` | （静默） |
| 5 | 属性解析 | 1688 CPV → Ozon 属性匹配引擎 | "正在解析属性..." → "已解析 {N} 个属性" |
| 6 | 提交任务 | `submit_envelope()` → `submit_task()` | "已提交任务 {task_id}，云端处理中 ⏳" |
| 7 | 制图 | `generate_product_images(token)` | "制图中（通常 3-9 分钟）..." |
| 8 | Ozon 上传 | `update_followed_product()` | "正在上架到 Ozon..." |
| 9 | 汇报结果 | 查 `gateway_tasks` | 按状态映射表汇报（见下方） |

### Worker B：Ozon 跟卖（6 步）

| # | 动作 | 函数 | 对用户说 |
|---|------|------|---------|
| 1 | 检查配置 | `check_config()` | （静默，失败时："缺少配置：{keys}"） |
| 2 | 解析 Ozon 商品 | `analyze_ozon_product(url)` | "正在分析 Ozon 商品..." → "已解析：{product_name}" |
| 3 | CDP 收集原图 | CDP 打开 Ozon 页 | "正在收集商品图片..." |
| 4 | 1688 找同款 | `search_products()` → 比价 → 问用户 | "找到 {N} 个同款，比价：\n1. ¥{X} ...\n跟卖还是新建？" |
| 5 | 跟卖 | `follow_sell_cloud(sku=product_id)` | "正在跟卖..." |
| 6 | 制图 → 写入 Ozon | 同 Worker A Step 7-8 | 同 Worker A |

如果复制被拒（`fallback_new_product`）→ 走 Worker A Step 2-9。

### Worker C：翻新（3 步）

| # | 动作 | 函数 | 对用户说 |
|---|------|------|---------|
| 1 | 获取现存产品 | `list_product_infos(product_ids=[...])` | "正在获取产品信息..." |
| 2 | 制图 | `generate_product_images(token)` | "制图中..." |
| 3 | 写入 Ozon | `update_followed_product` | "正在更新到 Ozon..." |

### Worker D：多 SKU 变体（3 步）

| # | 动作 | 函数 | 对用户说 |
|---|------|------|---------|
| 1 | 构建变体信封 | `build_variant_envelope(variants=[...])` | （静默） |
| 2 | 提交 | `submit_envelope` → `submit_task` | "已提交变体任务" |
| 3 | 制图 → 更新 | `generate_product_images` → `update` | "制图并更新中..." |

### Worker E：智能选品（无具体商品时，6 步）

触发条件：用户没有指定 1688 商品链接，说"帮我上架蓝海产品/有利润的产品/好卖的产品"

| # | 动作 | 函数 | 对用户说 |
|---|------|------|---------|
| 1 | 确认偏好 | 问用户或查店铺 | "好的，帮你找{蓝海/有利润}的产品 ⏳ 先确认——你店铺主要做哪个类目？还是我帮你看看店铺现有品类分布？" |
| 2 | 分析店铺 | `ozon_client.list_products()` | "正在分析你 Ozon 店铺的品类分布..." |
| 3 | 1688 选品 | `1688-shopkeeper trend/opportunities` 或 `search_products()` | "正在 1688 搜索{类目}热销品..." |
| 4 | 利润/蓝海分析 | 1688 价格 vs Ozon 售价对比 | "正在计算预估利润..." → 过滤低利润/高竞争品 |
| 5 | 呈现候选 | — | "帮你筛选了 {N} 个候选（按利润率排序）：\n1. **{商品名}** — 成本 ¥{X} Ozon 约 ₽{Y} 利润率 ~{Z}% 竞争{低/中/高}\n2. ...\n\n选哪个？或'全上'" |
| 6 | 进入 Worker A | 用户选定后 | "收到，开始上架【{商品名}】⏳" → 进入 Worker A Step 2 |

降级方案：如果 1688-shopkeeper trend/opportunities 不可用 → 让用户指定类目关键词 → 1688 search → 人工筛选 → 呈现候选。

---

## 返回结果

| status | 对用户说 |
|--------|---------|
| `accepted` | "已提交，云端处理中（{task_id}）" |
| `succeeded` | "✅ 上架成功！Ozon 任务 ID: {ozon_task_id}" |
| `blocked` | "⛔ 被阻断：{原因}。{建议}" |
| `failed` | "❌ 失败了：{错误}。可以重试或检查配置" |
| `partial_failed` | "⚠️ 部分完成：{详情}" |

跟卖: `copy_and_update` → "跟卖成功 ✅" | `fallback_new_product` → "禁止复制，走新建上架"

---

## 严格禁止

- ❌ 跳过 Worker 步骤（尤其是 Worker A Step 3 类目匹配——跳过会导致云端 pipeline 因 Supabase 无映射而 blocked）
- ❌ 跳过 CDP 浏览器采集（1688 API 不返回图片/重量/尺寸）
- ❌ "已提交" = "上架成功"
- ❌ 缺配置继续执行
- ❌ 硬编码凭据
- ❌ 编造未返回的数据
- ❌ 本地 skill 直接写 Supabase（Supabase 写入全在云端 webhook）
