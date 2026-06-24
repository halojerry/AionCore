---
name: redbook
version: 1.0.0
description: "小红书数据引擎。通过 redbook CLI 搜索笔记、阅读内容、分析博主、拆解爆款、检测限流、渲染图文卡片。覆盖 13 个分析模块（关键词矩阵→跨话题热力图→互动信号→博主画像→内容形式→机会评分→受众推断→选题策划→评论运营→爆款复刻→互动自动化→图文卡片→限流检测）。使用前确保已安装 redbook CLI 且已通过 whoami 认证。"
metadata:
  requires:
    bins: ["redbook"]
---

# redbook 技能 — 小红书数据引擎

使用 `redbook` CLI 搜索笔记、阅读内容、分析博主、拆解爆款、检测限流。

## 环境准备

### 安装 redbook CLI

```bash
npm install -g @lucasygu/redbook
```

需要 Node.js >= 22。支持 macOS、Windows、Linux。

### 验证连接

```bash
redbook whoami
```

CLI 自动读取 Chrome 浏览器中的小红书登录 Cookie。请先确保已在 Chrome 中登录 xiaohongshu.com。

- **macOS**：如遇钥匙串弹窗，点击"始终允许"
- **Windows**：Chrome 127+ 需先关闭 Chrome 再运行命令（CLI 会自动启动 headless 模式读取 Cookie）

---

## 命令速查

### 搜索笔记

```bash
redbook search "<关键词>" [--sort popular|latest|general] [--type image|video|all] [--page 1]
```

- `--sort popular`：按热门排序
- `--sort latest`：按最新排序
- `--type image`：仅图文笔记
- `--type video`：仅视频笔记

### 阅读笔记

```bash
redbook read <url或noteId>
redbook read https://www.xiaohongshu.com/explore/abc123
```

### 获取评论

```bash
redbook comments <url或noteId> [--all]
```

### 分析爆款笔记

```bash
redbook analyze-viral <url或noteId> [--comment-pages 3]
```

输出：标题钩子类型、互动比例（赞/藏/评/分享）、评论主题分析、结构拆解。

### 提取爆款模板

```bash
redbook viral-template <url1> <url2> <url3> --json
```

从 1-3 篇爆款笔记提取内容模板：标题结构、正文结构、钩子模式。

### 查看博主

```bash
redbook user <userId>
redbook user-posts <userId>
```

### 检测限流

```bash
redbook health            # 检测自己的笔记
redbook health --all --json
```

通过创作者后台 API 的隐藏 `level` 字段检测笔记是否被隐形限流。

### 渲染图文卡片

```bash
redbook render <文件.md> [--style xiaohongshu|purple|mint|sunset|ocean|elegant|dark] [--output-dir ./输出目录]
```

将 Markdown 渲染为小红书风格 PNG 图文卡片。需要可选依赖：
```bash
npm install -g puppeteer-core marked
```

### 评论管理

```bash
redbook comment "<noteUrl>" --content "评论内容"
redbook reply "<noteUrl>" --comment-id "<id>" --content "回复内容"
redbook batch-reply "<noteUrl>" --strategy questions --dry-run   # 先预览
redbook batch-reply "<noteUrl>" --strategy questions --max 10    # 执行
```

策略可选：`questions`（提问优先）/ `top-engaged`（高赞优先）/ `all-unanswered`（未回复优先）

### 收藏管理

```bash
redbook favorites [userId] --json
redbook collect "<noteUrl>"
redbook uncollect "<noteUrl>"
```

### 话题标签

```bash
redbook topics "<关键词>"
```

### 推荐页

```bash
redbook feed
```

---

## 13 个分析模块 (A-M)

| 模块 | 功能 | 关键命令 |
|------|------|---------|
| A. 关键词矩阵 | 分析各关键词的互动天花板和竞争密度 | `search` × N 个关键词 |
| B. 跨话题热力图 | 发现话题 × 场景的内容空白 | `search` 交叉关键词 |
| C. 互动信号分析 | 分类内容类型（工具型/认知型/娱乐型） | `analyze-viral` |
| D. 博主画像 | 对比头部博主的粉丝、互动、风格 | `user` + `user-posts` |
| E. 内容形式分析 | 图文 vs. 视频的表现对比 | `search --type image` vs `--type video` |
| F. 机会评分 | 按性价比排序关键词 | 综合分析 |
| G. 受众推断 | 从互动信号推断用户画像 | `comments --all` + LLM 分析 |
| H. 选题策划 | 数据驱动的内容创意 | 全文调研 |
| I. 评论运营 | 按策略筛选和批量回复评论 | `batch-reply` |
| J. 爆款复刻 | 从爆款笔记提取内容模板 | `viral-template` |
| K. 互动自动化 | 组合 I + J 的自动化运营 | 组合使用 |
| L. 图文卡片 | Markdown → 小红书风格 PNG | `render` |
| M. 限流检测 | 检测笔记隐形限流状态 | `health` |

---

## 安全规则

### 研究循环（最重要）

⚠️ 小红书风控会限制**读取**操作。任何需要读取 >5 条笔记的研究必须遵守：

- **人工节奏**：每次读笔记间隔 ≥20 秒，一次只处理一条
- **批量操作上限**：单次研究不超过 20 条笔记
- **冷却时间**：如果遇到 `300012` 错误（IP/captcha block），停止 30 分钟再试

### 写操作安全

- 批量回复前必须先 `--dry-run` 预览
- 回复间隔 ≥5 分钟（含 ±30% 随机抖动）
- 每天每篇笔记最多批量回复 1-2 次
- 发布功能容易触发验证码，不推荐自动化

### 通用规则

- 不操作非本人账号
- 不输出 Cookie/凭证到对话中
- 所有 `-o json` 输出优先用 JSON 解析

---

## 跨技能引用

- `../xhs-content-lab/SKILL.md` — 创作流水线（选题→标题→文案→优化→封面）
