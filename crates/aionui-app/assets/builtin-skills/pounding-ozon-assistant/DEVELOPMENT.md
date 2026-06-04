# pounding-ozon 开发文档

## 架构概览

```
用户 ─→ AI Client (Claude/OpenClaw/Hermes) ─→ SKILL.md + AGENTS.md
                                                    │
                                              cloud_client.py ─→ path_registry.json
                                                    │                    │
                                                    ▼                    ▼
                                              本地 CDP 浏览器         n8n 云端工作流
                                              (1688 数据采集)        (制图/上架/Supabase)
```

### 本地 vs 云端边界

| 必须在本地 | 原因 | 可以在云端 |
|-----------|------|-----------|
| 1688 CDP 浏览器采集 | 需要本地 Chrome + 登录态 | ✅ 类目解析 (查 Supabase) |
| 用户交互（类目选择、价格确认） | 需要人工决策 | ✅ 属性解析 (Ozon API) |
| 凭证管理 (.env / config.json) | 敏感信息不离开用户机器 | ✅ AI 制图 (mxou API) |
| Agent 行为 (AGENTS.md rules) | AI 客户端本地执行 | ✅ Ozon 上架 (Ozon API) |
| | | ✅ 结果存储 (Supabase) |

### 云端 5 个 Webhook

| 路径 | 用途 | Worker | 节点数 |
|------|------|--------|--------|
| `pl-v3-304140` | 完整新上架管线 (8阶段) | A, D | 13 |
| `v2-ingest-292201` | 类目匹配 (鉴权+接收) | D, 类目匹配 | 2 |
| `fs-v4-303992` | 跟卖 (import-by-sku) | B | 4 |
| `re-v2-304020` | 翻新 (Ozon update) | C | 4 |
| `mx-bp2-377417` | 单张制图 | A, B, C, D | 2 |

## 凭证体系

```
~/.pounding/config.json (分发级，随 Skill 分发)
  └─ api.key → MXOU_TOKEN / MXOU_IMAGE_TOKEN (制图+鉴权)

.env (用户级，AI 助手写入，跨对话保留)
  ├─ ALI_1688_AK     → 1688 搜索选品
  ├─ OZON_CLIENT_ID  → Ozon 上架/跟卖/翻新
  └─ OZON_API_KEY    → Ozon 上架/跟卖/翻新
```

**规则**：
- 分发级凭证只从 `~/.pounding/config.json` 读取，绝不写入 `.env`
- 用户级凭证自动写入 `.env` 持久化，下次对话 `load_env_file()` 自动加载
- 首次使用：AGENTS.md「首次配置引导」逐个问答填 `.env`

## 本地关键文件

| 文件 | 作用 |
|------|------|
| `SKILL.md` | Worker 定义 + 配置表 + 函数返回值速查 |
| `AGENTS.md` | Agent 人设 + 沟通话术 + 铁律 + 凭证引导 |
| `cloud_client.py` | 所有业务函数入口 (envelope/send/category/images) |
| `config_store.py` | 凭证加载/写入/check_config |
| `browser_probe/service.py` | CDP 浏览器探针 (EXTRACT_1688_JS) |
| `path_registry.json` | 云端 webhook 路径注册表 |

## 云管线 8 阶段 (pl-v3-304140)

```
📥 Webhook 接收信封
  → ① Category    查 Supabase category_mapping_verified
  → ② Mirror      图片 URL 收集
  → ③ Attributes  Ozon /v1/description-category/attribute
  → ④ Phase1      AI 白底图×2 (mxou API)
  → ⑤ Phase2Prep  准备 8 张图数据
  → ⑥ SplitBatch  分批并发 (batch=3)
  → ⑦ CallMxou    逐张调 mxou API
  → ⑧ Collect     收集全部 10 张图结果
  → ⑨ Payload     构建 Ozon 商品负载
  → ⑩ Gate        质量检查 (置信度/图片数/价格)
  → ⑪ Upload      Ozon /v3/product/import
  → ⑫ Status      写 Supabase + Sentry 错误上报
```

**制图 10 个 Slot**：白底参考 → 多角度白底 → 主图 → 信息图 → 细节图 → 好评图 → 旅行场景 → 家庭场景 → 商务场景 → 对比图

每张图有专业中文提示词，Phase2 使用 Phase1 生成的干净参考图。

## Sentry 错误追踪

- DSN 配置在 `pounding-ozon-cloud/.env` (SENTRY_DSN)
- 管线 Status 节点在有任何 stage 失败/blocked 时自动上报 Sentry
- 上报内容：失败的 stage 列表 + task_id

## 接口稳定约定

云端工作流更新时，Skills 不需要改代码，因为：

1. **Webhook 路径不变** — 云端更新只改工作流内部节点逻辑
2. **信封格式不变** — `{version, project_id, source, assets, draft, extensions}`
3. **返回格式不变** — `{task_id, status, terminal, stages, ...}`
4. **路径注册表自动同步** — `path_registry.json` 三层 fallback (API标签发现 → 注册表 → 硬编码)

## 测试

### E2E 测试 (云管线)

```bash
cd pounding-ozon-cloud
python3 -m pytest tests/ -v
# 30 passed, 1 skipped
```

### n8n Webhook 测试

```bash
# 新上架管线
curl -X POST https://worker.mxou.cn/webhook/pl-v3-304140 \
  -H "Content-Type: application/json" \
  -d '{"envelope":{...}}'

# 跟卖
curl -X POST https://worker.mxou.cn/webhook/fs-v4-303992 \
  -H "Content-Type: application/json" \
  -d '{"sku":"...","ozon_client_id":"...","ozon_api_key":"..."}'
```

## 部署

### n8n 工作流导入

```bash
# 通过 API
N8N_API_KEY=xxx python3 deploy/deploy-n8n.py

# 或手动: n8n UI → Import from File → 选择 deploy/n8n/{name}.json
```

### Skills 分发包

```bash
# 复制到 AI 客户端 skills 目录
cp -r pounding-ozon-assistant/ ~/.claude/skills/pounding-ozon/

# Python 依赖
pip install pounding-ozon-cloud>=0.2.0
```

## 更新策略

### 用户更新 Skill

大部分云端更新**不需要用户重新安装 Skill**（见下方接口稳定约定）。以下情况才需要用户更新：

| 改了这些文件 | 需要用户更新 |
|-------------|:-----------:|
| `AGENTS.md` / `SKILL.md`（新功能、流程优化） | 建议更新 |
| `cloud_client.py`（性能/缓存/bug修复） | 建议更新 |
| `config_store.py`（凭证相关） | 建议更新 |
| `browser_probe/service.py`（CDP优化） | 建议更新 |

**更新方式**：用户替换 `pounding-ozon-assistant/` 目录即可，`.env` 和 `~/.pounding/config.json` 不动。

### 云端更新（n8n 工作流）

云端更新 n8n 工作流时，**用户不需要做任何操作**——webhook 路径不变，旧 Skill 的请求自动到达新工作流。

### 接口稳定约定（Interface Stability Contract）

云端更新 n8n 工作流内部逻辑时，以下三项**绝不改变**：

| 约定 | 内容 |
|------|------|
| **Webhook 路径不变** | `path_registry.json` 锁定的 5 个路径 |
| **信封格式不变** | `{version, project_id, source, assets, draft, extensions}` |
| **返回格式不变** | `{task_id, status, terminal, stages, ...}` |

**可以改的**（内部实现）：工作流节点逻辑、API 目标地址、Sentry 上报、制图提示词、分批并发数。
**不能改的**（对外接口）：5 个 webhook 路径、信封/返回 JSON schema、`path_registry.json` 的 key 名。

### 回滚

```bash
git checkout <commit> -- deploy/n8n/pipeline.json
N8N_API_KEY=xxx python3 deploy/deploy-n8n.py pipeline
```

### Supabase 数据生命周期

`gateway_tasks` 表会随时间增长，需要定期清理旧数据。

**推荐方案：Supabase pg_cron 定时任务**（独立于 Skills/n8n，最可靠）

```sql
-- 1. 在 Supabase Dashboard → Database → Extensions 启用 pg_cron

-- 2. 创建每天凌晨3点清理30天前数据的定时任务
SELECT cron.schedule(
  'cleanup-gateway-tasks',
  '0 3 * * *',
  $$ DELETE FROM gateway_tasks WHERE created_at < (EXTRACT(EPOCH FROM NOW() - INTERVAL '30 days'))::bigint $$
);

-- 3. 查看任务状态
SELECT * FROM cron.job;

-- 4. 查看执行日志
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;
```

**备用方案：n8n 管线 Status 节点**（每次运行管线时顺带清理，已实现）

**各表策略**：

| 表 | 生命周期 | 清理方式 |
|----|---------|---------|
| `gateway_tasks` | 30天 | pg_cron 定时 DELETE |
| `category_mapping_verified` | 永久 | 不清理（越用越丰富） |
| `tokens` | 手动 | 管理员管理 |

## 故障排查

| 问题 | 排查步骤 |
|------|---------|
| n8n 返回 500 | 检查 deploy/n8n/*.json 与线上是否一致；看 n8n 执行日志 |
| Token 无效 | 检查 `~/.pounding/config.json` 的 `api.key` 是否在 Supabase tokens 表中 |
| CDP 1688 限流 | 缓存已内置（24h内同商品复用结果）；清理旧文件 `cleanup_old_files(7)` 自动运行 |
| CDP 缓存未命中 | 检查 `data/ozon/tasks/*/browser-probes/` 是否有该 offer 的文件，超过 24h 会过期 |
| mxou 制图 503 | mxou 服务暂时不可用，等恢复即可 |
| 类目匹配失败 | 查 Supabase `category_mapping_verified` 表是否有该 source_category_id 的记录 |
