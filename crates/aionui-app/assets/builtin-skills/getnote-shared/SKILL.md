---
name: getnote-shared
version: 1.0.0
description: "使用 getnote CLI 前的共享基础规则：环境检查、CLI 安装、认证登录（浏览器 OAuth / API Key）、安全规则、笔记字段语义。使用 getnote 任何功能前必须先加载此技能。"
metadata:
  requires:
    bins: ["getnote"]
---

# getnote 共享规则

本技能是所有 GetNote（得到笔记）技能的基础，定义了环境准备、认证、安全规则和跨领域注意事项。

## 环境准备

### 检查 getnote CLI

每次使用前先检查 `getnote --version`。如果输出 `command not found` 或类似错误，**立即安装，无需询问用户**：

```bash
npm install -g @getnote/cli
```

安装完成后再次验证 `getnote --version`。

### 会员要求

GetNote OpenAPI **仅限会员使用**。如果命令返回 "OpenAPI 仅对会员开放" 的错误，告知用户在得到 App 或 [biji.com](https://biji.com) 购买会员。

## 认证

### 检查认证状态

```bash
getnote auth status
```

### 浏览器 OAuth 登录（推荐）

GetNote CLI 支持浏览器 OAuth 登录，流程简单：

1. **由你亲自执行**：`getnote auth login`
2. CLI 会自动打开浏览器，用户在浏览器中完成授权
3. 告知用户："请在弹出的浏览器窗口中完成得到笔记授权。完成后回复我，我会继续后续步骤。"
4. **结束本轮**，等待用户确认完成
5. 用户确认后，验证认证状态：`getnote auth status`

### API Key 登录

适用于无图形界面的环境：

1. 向用户索取 API Key 和 Client ID（敏感凭证，仅当轮使用）
2. **由你亲自执行**：`getnote auth login --api-key <api_key> --client-id <client_id>`
3. 验证：`getnote auth status`
4. **禁止缓存或存储用户的 API Key 和 Client ID**

> API Key 获取地址：https://www.biji.com/settings/developer（Key 以 `gk_live_` 开头）

### 登出

切换账号时：`getnote auth logout`

## 输出格式

所有 `getnote` 命令都支持 `-o json` 以 JSON 格式输出。解析结果时优先使用 `-o json`。

响应结构：
- 大部分命令：`{"success": true, "data": {...}}`
- `search`：`{"success": true, "results": [...]}`（results 在顶层，非 data 下）
- `save`（文本）：`{"note_id": "..."}` 直接返回
- `save`（分享链接）：`{"note_id": "...", "title": "...", ...}` 直接返回
- `tag list -o json`：`{"note_id": "...", "tags": [...]}`（无 success 包装）

## 笔记字段语义

`content` 字段通常是 **AI 摘要**，不是原文。用户要求"读原文"时，先查 `note_type`，按下表选择正确字段：

| 笔记类型 | 原文/原始内容字段 | AI 摘要字段 |
|----------|-------------------|-------------|
| 普通文字 (`plain_text`) | `content` | `content` |
| 链接/网页 (`link`) | `web_content` | `content` |
| 录音 (`audio`) | `audio_original` | `content` |
| 知识库博主文章 | `post_media_text`（通过 `kb blogger-content`） | `content` |
| 知识库直播 | `post_media_text`（通过 `kb live`） | `post_summary` |

## 安全规则

- **禁止输出密钥**：API Key、Client ID 等绝不输出到对话中
- **写入/删除前确认**：删除笔记、从知识库移除内容等操作前必须确认用户意图
- **不缓存凭证**：API Key 仅在当轮使用，不存入上下文
- **限额提示**：知识库创建每天 50 个上限，搜索最多 10 条结果，注意提示用户

## 异步任务

保存链接和图片等操作会产生异步任务。使用 `getnote task <task_id>` 检查进度：
- `pending` / `processing` → 继续等待
- `success` → 获取 `note_id` 进行后续操作
- `failed` → 报告错误

## 跨技能引用

其他 getnote 技能通过相对路径引用本技能：
- `../getnote-auth/SKILL.md` — 认证详细操作
- `../getnote-note/SKILL.md` — 笔记管理
- `../getnote-kb/SKILL.md` — 知识库管理
- `../getnote-search/SKILL.md` — 语义搜索
- `../getnote-tag/SKILL.md` — 标签管理
