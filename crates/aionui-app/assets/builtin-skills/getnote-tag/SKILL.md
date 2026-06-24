---
name: getnote-tag
version: 0.3.0
description: "GetNote 标签管理：添加、查看、移除笔记标签。注意移除需要标签 ID 而非标签名，且系统标签不可删除。批量替换标签用 ../getnote-note/SKILL.md 的 note update --tag。使用前先读 ../getnote-shared/SKILL.md。"
metadata:
  requires:
    bins: ["getnote"]
---

# getnote-tag 技能

管理笔记标签：添加、列表、移除。

使用前先读 [../getnote-shared/SKILL.md](../getnote-shared/SKILL.md)（认证、安全规则）。

## 命令

### 列出笔记标签

```
getnote tag list <note_id>
```

返回标签列表（含 ID 和类型）。

标签类型：
- `ai` — AI 自动生成
- `manual` — 用户添加
- `system` — 系统标签（**不可删除**）

```bash
getnote tag list 1896830231705320746
getnote tag list 1896830231705320746 -o json
```

---

### 添加标签

```
getnote tag add <note_id> <tag>
```

```bash
getnote tag add 1896830231705320746 工作
```

---

### 移除标签

```
getnote tag remove <note_id> <tag_id>
```

> ⚠️ 需要**标签 ID**（整数，来自 `tag list`），非标签名。
> ⚠️ `system` 类型标签不可移除。

```bash
# 第一步：获取标签 ID
getnote tag list 1896830231705320746 -o json

# 第二步：用标签 ID 移除
getnote tag remove 1896830231705320746 123
```

---

## Agent 使用注意事项

- `tag list -o json` 返回 `{"note_id":"...","tags":[{"id":"...","name":"...","type":"..."}]}`（无 `success` 包装）
- `tag remove` 需要**数字标签 ID**，非标签名 — 始终先调用 `tag list` 获取 ID
- 批量替换全部标签用 [../getnote-note/SKILL.md](../getnote-note/SKILL.md) 的 `getnote note update --tag "tag1,tag2"`
- 退出码 `0` = 成功，非零 = 错误，stderr 输出错误详情
