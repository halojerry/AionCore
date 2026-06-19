---
name: getnote-kb
version: 0.5.2
description: "GetNote 知识库管理：列出/创建知识库、浏览笔记、添加/移除笔记、订阅知识库、博主内容、直播回放、配额查询。使用前先读 ../getnote-shared/SKILL.md。"
metadata:
  requires:
    bins: ["getnote"]
---

# getnote-kb 技能

管理 Get笔记 知识库：列出、创建、浏览笔记、添加/移除笔记。也支持订阅知识库、博主内容、直播回放和配额查询。

使用前先读 [../getnote-shared/SKILL.md](../getnote-shared/SKILL.md)（认证、安全规则）。

## 命令

### 列出全部知识库

```
getnote kbs
```

返回所有知识库，含 `topic_id`、`name`、`description`、`note_count`、`created_at`。

```bash
getnote kbs
getnote kbs -o json
```

---

### 列出已订阅知识库

```
getnote kbs-sub [--page <n>]
```

返回用户订阅的公开知识库，支持分页。

| 参数 | 默认 | 说明 |
|------|------|------|
| `--page` | 1 | 页码 |

```bash
getnote kbs-sub
getnote kbs-sub --page 2
getnote kbs-sub -o json
```

> 用 `getnote kb <topic_id>` 浏览订阅知识库中的笔记。

---

### 浏览知识库笔记

```
getnote kb <topic_id> [--limit <n>] [--all]
```

默认每页 20 条。

| 参数 | 默认 | 说明 |
|------|------|------|
| `--limit` | 20 | 每页条数 |
| `--all` | — | 获取全部（自动分页） |

```bash
getnote kb vnrOAaGY
getnote kb vnrOAaGY --all
getnote kb vnrOAaGY -o json
```

---

### 创建知识库

```
getnote kb create <name> [--desc <description>]
```

```bash
getnote kb create "研究论文"
getnote kb create "项目文档" --desc "文档链接汇总"
```

> 每天最多创建 50 个知识库（北京时间 00:00 重置）。

---

### 添加笔记到知识库

```
getnote kb add <topic_id> <note_id> [note_id...]
```

支持多个 note ID，每次最多 20 个。

```bash
getnote kb add vnrOAaGY 1234567890
getnote kb add vnrOAaGY 1234567890 9876543210
```

> 已存在的笔记会被静默跳过。

---

### 从知识库移除笔记

```
getnote kb remove <topic_id> <note_id> [note_id...]
```

```bash
getnote kb remove vnrOAaGY 1234567890
```

> ⚠️ **订阅知识库限制**：如果目标知识库是他人创建（通过 `getnote kbs-sub` 获取），且用户非该知识库管理员，则无法添加或移除笔记。只有自己创建的知识库（`getnote kbs`）支持完整增删操作。

---

### 列出知识库博主

```
getnote kb bloggers <topic_id> [--page <n>]
```

返回已订阅博主列表，含 `follow_id`（用于内容查询）、`account_name`、`platform`、`follow_time`。

```bash
getnote kb bloggers vnrOAaGY
getnote kb bloggers vnrOAaGY --page 2 -o json
```

---

### 列出博主内容

```
getnote kb blogger-contents <topic_id> <follow_id> [--page <n>]
```

返回内容列表（无全文）。用 `post_id_alias` 获取详情。

```bash
getnote kb blogger-contents vnrOAaGY follow123
getnote kb blogger-contents vnrOAaGY follow123 --page 2
```

---

### 查看博主文章详情

```
getnote kb blogger-content <topic_id> <post_id>
```

返回完整内容（含原文 `post_media_text`）。

```bash
getnote kb blogger-content vnrOAaGY post_abc123
getnote kb blogger-content vnrOAaGY post_abc123 -o json
```

---

### 列出已完成的直播

```
getnote kb lives <topic_id> [--page <n>]
```

仅返回已完成且 AI 处理过的直播。

```bash
getnote kb lives vnrOAaGY
getnote kb lives vnrOAaGY --page 2
```

---

### 查看直播详情

```
getnote kb live <topic_id> <live_id>
```

返回 AI 摘要（`post_summary`）和完整转写（`post_media_text`）。

```bash
getnote kb live vnrOAaGY live_abc123
getnote kb live vnrOAaGY live_abc123 -o json
```

---

### 关注直播频道

```
getnote kb live-follow <topic_id> <link> [--platform <platform>]
```

订阅得到直播频道到知识库。直播结束后 AI 处理完毕会出现在 `kb lives` 中。

> ⚠️ 目前仅支持得到 App 直播链接。

```bash
getnote kb live-follow vnrOAaGY https://m.dedao.cn/live/xxxxx
getnote kb live-follow vnrOAaGY https://m.dedao.cn/live/xxxxx -o json
```

返回：`follow_id`、`url`、`platform`、`type`、`created_at`。

---

### 查看配额

```
getnote quota
```

```bash
getnote quota
getnote quota -o json
```

---

## Agent 使用注意事项

- 优先用 `-o json` 解析结果
- `kbs -o json` 返回 `{"success":true,"data":{"topics":[...],"total":N}}`
- `kbs-sub -o json` 返回格式与 `kbs -o json` 相同
- `kb <topic_id> -o json` 返回 `{"success":true,"data":{"notes":[...],"has_more":...}}`
- `topic_id` 从 `getnote kbs -o json` 或 `getnote kbs-sub -o json` → `data.topics[].topic_id` 获取（非 `id`）
- `kb add` / `kb remove` 接受多个 note ID — 优先批量操作
- **订阅知识库只读**：非管理员的订阅知识库无法增删笔记。用 `getnote kbs`（自有）vs `getnote kbs-sub`（订阅）区分
- `kb bloggers` → 获取 `follow_id` → `kb blogger-contents` → 获取 `post_id_alias` → `kb blogger-content` 获取全文
- `kb lives` → 获取 `live_id` → `kb live` 获取 AI 摘要 + 转写
- `kb live-follow <topic_id> <link>` 订阅直播频道；新直播结束后会出现在 `kb lives`
- `quota -o json` 返回 `{"success":true,"data":{"read":{"daily":{limit,used,remaining,reset_at},"monthly":{...}},"write":{...},"write_note":{...}}}`
- 退出码 `0` = 成功，非零 = 错误，stderr 输出错误详情
