---
name: getnote-note
version: 0.4.0
description: "GetNote 笔记管理：保存链接/文本/图片、列表浏览、查看详情（区分原文与AI摘要）、更新标题/内容/标签、删除、分享。使用前先读 ../getnote-shared/SKILL.md。"
metadata:
  requires:
    bins: ["getnote"]
---

# getnote-note 技能

管理 Get笔记 中的笔记：保存、列表、查看、更新、删除、分享。

使用前先读 [../getnote-shared/SKILL.md](../getnote-shared/SKILL.md)（认证、字段语义、安全规则）。

## 命令

### 保存笔记

```
getnote save <url|text|image_path> [--title <title>] [--tag <tag>]...
```

| 参数 | 说明 |
|------|------|
| `--title` | 可选标题 |
| `--tag` | 标签，可重复使用 |

- URL（`http://` 或 `https://`）→ 链接笔记：
  - **分享链接**（`biji.com/note/share_note/*` 或 `d.biji.com/*` 短链接）→ **同步**，直接返回 `note_id`
  - **内部笔记链接**（`biji.com/note/{note_id}`）→ 用于笔记内容中引用其他笔记；如当前笔记将公开发布，优先使用被引用笔记的分享链接
  - **其他 URL** → 异步，自动轮询直到完成
- 本地图片路径 → 图片笔记（异步）
- 其他 → 文字笔记（同步）

```bash
getnote save https://example.com --title "好文章"
getnote save "记得查看文档" --tag 工作 --tag 重要
getnote save ./screenshot.png --title "设计稿"
```

使用 `-o json` 时静默轮询并返回最终笔记 JSON（含 `title`、`content`、`note_type`、`tags`、`created_at`）。

---

### 跟踪保存任务

```
getnote task <task_id>
```

手动检查异步保存任务进度。

```bash
getnote task task_xyz789 -o json
```

返回 `status`（`pending` / `processing` / `success` / `failed`），完成后含 `note_id`。

---

### 列表浏览

```
getnote notes [--since-id <id>] [--all]
```

每页固定 20 条，无 `--limit` 参数。

| 参数 | 说明 |
|------|------|
| `--since-id` | 分页游标（上次看到的最后一条 note ID） |
| `--all` | 获取全部笔记（自动分页） |

```bash
getnote notes
getnote notes --all
getnote notes --since-id 1234567890
getnote notes -o json
```

笔记类型：`plain_text` / `img_text` / `link` / `audio` / `meeting` / `local_audio` / `internal_record` / `class_audio` / `recorder_audio` / `recorder_flash_audio`

---

### 查看详情

```
getnote note <id> [--field <field>]
```

返回完整笔记（含内容、标签、附件）。`--field` 提取单个字段。

| `--field` 值 | 说明 |
|-------------|------|
| `id` | 笔记 ID |
| `title` | 标题 |
| `content` | 内容 / AI 摘要 |
| `type` | 笔记类型 |
| `created_at` | 创建时间 |
| `updated_at` | 最后更新时间 |
| `url` | 来源 URL（链接笔记） |
| `excerpt` | 摘要 |
| `web_content` | 网页原文（仅链接笔记） |
| `audio_original` | 录音转写原文（仅 `audio` 类型） |
| `source` | 来源（如 `openapi`、`manual`） |
| `tags` | 逗号分隔的标签名 |

```bash
getnote note 1234567890
getnote note 1234567890 --field content
getnote note 1234567890 --field url
getnote note 1234567890 -o json
```

---

### 更新笔记

```
getnote note update <id> [--title <title>] [--content <content>] [--tag <tags>]
```

| 参数 | 说明 |
|------|------|
| `--title` | 新标题 |
| `--content` | 新内容（仅限 `plain_text` 笔记） |
| `--tag` | 逗号分隔的标签 — **替换全部现有标签** |

```bash
getnote note update 1234567890 --title "新标题"
getnote note update 1234567890 --tag "工作,重要"
```

> ⚠️ `--tag` 替换全部标签。部分修改请用 `getnote tag add/remove`。
> ⚠️ 内容更新仅适用于 `plain_text` 笔记。

---

### 删除笔记

```
getnote note delete <id> [-y]
```

移至回收站。

```bash
getnote note delete 1234567890 -y
```

---

### 分享笔记

```
getnote note share <id> [--exclude-audio]
```

生成公开分享链接。幂等操作——多次调用返回相同 URL。

```bash
getnote note share 1234567890
getnote note share 1234567890 --exclude-audio
getnote note share 1234567890 -o json
```

返回：`share_url`（如 `https://biji.com/note/share_note/rBzdMlXrzgYVM`）

---

## Agent 使用注意事项

- 优先用 `-o json` 解析响应
- 大部分 JSON 响应格式为 `{"success":true,"data":{...}}`，**例外**：
  - `save`(文字)：`{"note_id":"..."}` 直接返回
  - `save`(分享链接)：`{"note_id":"...","title":"...","created_at":"...","updated_at":"..."}` 直接返回
  - `save`(普通链接/图片)：`{"data":{"tasks":[{"task_id":"..."}],...}}`
  - `task`：`{"success":true,"data":{"status":"...","note_id":"..."}}`
- `notes` 列表每页 20 条；用 `--since-id` 翻页
- note ID 为 int64，处理时当字符串避免 JS 精度丢失
- 退出码 `0` = 成功，非零 = 错误，stderr 输出错误详情

### 字段语义（"原文" vs AI 摘要）

不同笔记类型的"原文"字段不同，`content` 通常是 AI 摘要而非原文。用户要求"读原文"时，先用 `getnote note <id> -o json` 查看 `note_type`，再按下表选择：

| 笔记类型 | 原文字段 | AI 摘要字段 |
|---------|---------|------------|
| 普通文字笔记 | `content` | `content` |
| 链接/网页笔记 | `web_content` | `content` |
| 录音笔记 | `audio_original` | `content` |
| 知识库博主内容 | `post_media_text`（via [../getnote-kb/SKILL.md](../getnote-kb/SKILL.md)）| `content` |
| 知识库直播 | `post_media_text`（via [../getnote-kb/SKILL.md](../getnote-kb/SKILL.md)）| `post_summary` |
