---
name: getnote-search
version: 0.4.0
description: "GetNote 语义搜索：全局搜索笔记、指定知识库内搜索。使用前先读 ../getnote-shared/SKILL.md。结果可进一步用 ../getnote-note/SKILL.md 查看详情。"
metadata:
  requires:
    bins: ["getnote"]
---

# getnote-search 技能

跨全部笔记或指定知识库进行语义搜索。

使用前先读 [../getnote-shared/SKILL.md](../getnote-shared/SKILL.md)（认证、字段语义）。

## 命令

### 搜索笔记

```
getnote search <query> [--kb <topic_id>] [--limit <n>]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--kb` | — | 限定在指定知识库（`topic_id`）内搜索 |
| `--limit` | 10 | 最大结果数（上限 10） |

结果按语义相关度从高到低排序。每条结果含：`note_id`、`title`、`content`（摘要）、`score`、`created_at`、`note_type`。

> 注意：仅 `NOTE` 类型结果填充 `note_id`。其他类型（`FILE`、`BLOGGER`、`LIVE` 等）的 `note_id` 为空。

```bash
# 全局搜索
getnote search "大模型 API"

# 限定知识库搜索
getnote search "RAG" --kb qnNX75j0

# 限制结果数 + JSON 输出
getnote search "机器学习" --limit 5 -o json
```

---

## Agent 使用注意事项

- 优先用 `-o json` 解析结果
- JSON 响应：`{"success":true,"results":[{"note_id":"...","title":"...","content":"...","score":0.95,"created_at":"...","note_type":"..."}]}`
- 注意：`results` 在顶层，不在 `data` 下
- `--kb` 的 `topic_id` 从 [../getnote-kb/SKILL.md](../getnote-kb/SKILL.md) (`getnote kbs -o json` → `data.topics[].topic_id`) 获取
- `NOTE` 类型结果用 `getnote note <note_id>` 获取完整内容（见 [../getnote-note/SKILL.md](../getnote-note/SKILL.md)）
- 最大 `--limit` 为 10；无关键词浏览用 `getnote notes`
- 退出码 `0` = 成功，非零 = 错误，stderr 输出错误详情
