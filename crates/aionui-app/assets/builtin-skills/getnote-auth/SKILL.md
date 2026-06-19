---
name: getnote-auth
version: 0.4.0
description: "GetNote 认证管理：登录（浏览器 OAuth / API Key）、状态检查、登出。使用前先读 ../getnote-shared/SKILL.md。"
metadata:
  requires:
    bins: ["getnote"]
---

# getnote-auth 技能

Get笔记 CLI 的认证管理。

使用前先读 [../getnote-shared/SKILL.md](../getnote-shared/SKILL.md)（环境检查、安全规则）。

## 命令

### 登录

```
getnote auth login [--api-key <key>] [--client-id <id>]
```

| 方式 | 命令 | 说明 |
|------|------|------|
| OAuth（推荐） | `getnote auth login` | 打开浏览器授权，自动保存凭证 |
| API Key | `getnote auth login --api-key <key> --client-id <id>` | 直接保存 Key，无需浏览器 |

```bash
# OAuth 流程（打开浏览器）
getnote auth login

# API Key 直接登录
getnote auth login --api-key gk_live_xxx --client-id xxx
```

> API Key 获取地址：https://www.biji.com/settings/developer（Key 以 `gk_live_` 开头）

---

### 检查状态

```
getnote auth status
```

显示当前认证状态。

```bash
getnote auth status
```

---

### 登出

```
getnote auth logout
```

清除 `~/.getnote/config.json` 中的凭证。

```bash
getnote auth logout
```

---

## Agent 使用注意事项

- 在执行其他操作前始终先运行 `getnote auth status`
- 如果未认证，引导用户登录（优先 OAuth，备用 API Key）
- `--api-key` 在任意命令中均为临时覆盖，不保存凭证
- 凭证保存在 `~/.getnote/config.json`；环境变量 `GETNOTE_API_KEY` / `GETNOTE_CLIENT_ID` 优先级更高
