---
name: xhs-ops
version: 2.0.3
description: |
  小红书运营助手 v2.0（AI驱动版），覆盖标题生成、笔记写作、博主诊断、账号定位等核心场景。
  触发场景：
  - 生成爆款标题（AI驱动）
  - 写小红书笔记正文（AI驱动）
  - 博主阶段诊断和运营建议（AI驱动）
  - 新人账号定位（昵称/简介/视觉风格，AI驱动）
  - 选题研究、封面文案、内容规划
---

# 小红书运营助手 v2.0.0

## 核心升级说明

**v2.0 核心变化：AI驱动，告别模板**
- 标题生成：扔掉模板池，LLM 直接生成多角度爆款标题
- 笔记写作：扔掉模板结构，AI 生成符合小红书调性的完整正文
- 博主诊断：AI 分析账号阶段，给出个性化运营建议

---

## 平台核心指标

| 指标 | 健康值 | 优化方向 |
|------|--------|---------|
| 收藏率 ⭐ | >3% | 提升实用感、增加干货密度 |
| 点赞率 | 3-8% | 优化封面标题 |
| 评论率 | 0.5-2% | 主动提问、设置讨论话题 |
| 分享率 | 0.5-1% | 增强实用性、收藏价值 |
| 封面点击率 | >5% | 优化封面视觉效果 |

> 💡 收藏率是核心指标：收藏 = 用户觉得有用，是算法最看重的信号

---

## 标签策略

**5个标签黄金法则**：

| 类型 | 数量 | 举例 |
|------|------|------|
| 流量大词 | 1个 | #穿搭 |
| 垂直领域词 | 2个 | #职场穿搭 #小个子穿搭 |
| 内容类型词 | 1个 | #穿搭分享 |
| 场景/人群词 | 1个 | #上班族 |

**标签选择原则**：
- 选用户会搜的词，不要自创
- 宁精勿多：5个精准 > 10个模糊
- 大小搭配：大流量词+精准词

---

## 发布时间参考

| 时段 | 适合内容 |
|------|---------|
| 7:30-8:30 | 干货教程、种草 |
| 12:00-13:00 | 快节奏内容 |
| 21:00-22:00 | 深度内容、种草 |

> 黄金时间优先发布重要内容

---

## 反模式：内容生成避坑指南

### ❌ 标题生成不要这样写

| 错误写法 | 问题 | 正确写法 |
|---------|------|---------|
| "最值得买的10款面霜" | 绝对化用词，违规 | "亲测！这10款面霜真的好用" |
| "用它皮肤真的变好了！" | 无依据、太泛 | "用了2周，下巴的痘消了一半" |
| "所有女生都要知道的事" | 绝对化 | "女生真的要试试这个方法" |
| "99%的人都不知道" | 夸大虚假 | "这个技巧用了3个月，真实有效" |

### ❌ 笔记正文不要这样写

| 错误写法 | 问题 | 正确写法 |
|---------|------|---------|
| "这款面霜含有丰富保湿成分" | 太广告、像说明书 | "涂上去润润的，第二天脸还是软软的" |
| "我推荐大家都去买" | 绝对化、违规 | "我自己已经回购了3瓶，真的喜欢" |
| "三天美白、七天淡斑" | 医疗宣称，违规 | "用了一周，感觉肤色亮了一点" |
| 大段文字不带emoji | 阅读疲劳 | 每2-3句一个节奏点，适当emoji |
| "适合所有肤质" | 无依据、违规 | "我是混干皮，用着OK，仅供参考" |

### ❌ 选题不要这样选

| 错误做法 | 问题 | 正确做法 |
|---------|------|---------|
| 追所有热点 | 没有定位，账号混乱 | 只追跟账号方向相关的热点 |
| 什么火发什么 | 内容碎片化，没有积累 | 深耕1-2个方向，做系列内容 |
| 跟风发同质内容 | 用户审美疲劳 | 加入独特视角或亲身经历 |
| 从不分析数据 | 不知道什么有效 | 每篇笔记后复盘收藏率、点赞率 |

### ❌ 博主诊断不要这样用

| 错误用法 | 正确用法 |
|---------|---------|
| 要求诊断"我要年入百万" | 聚焦具体阶段目标："粉丝500了，下一步怎么突破" |
| 同时给太多方向 | 先集中一个方向诊断，验证后再扩展 |
| 诊断完不执行 | 把诊断输出的"立即行动"立即执行，不要拖 |

---

## 合规红线（限流/封禁）

1. ❌ 夸大宣传：不用"最"、绝对化用语
2. ❌ 医疗效果宣称：护肤品不得宣称治疗效果
3. ❌ 虚假优惠：价格对比必须有依据
4. ❌ 诱导私信：不要"私信领取"
5. ❌ 刷量行为：买赞买收藏会被检测
6. ❌ 敏感话题：政治/社会事件/擦边内容不碰

**合规表达**：
| 不要说 | 改为 |
|--------|------|
| 这个产品保证有效 | 我用下来觉得... |
| 所有人都适合 | 我个人感受是... |
| 强烈推荐大家都买 | 分享我的真实体验 |

---

## AI 命令（v2.0 新增）

```bash
# 爆款标题生成（AI驱动）
node index.js title --topic "选题"              # 生成标题
node index.js title --topic "选题" --audience "上班族"  # 指定目标受众

# 笔记正文生成（AI驱动）
node index.js note --title "标题" --topic "选题" --style "种草"

# 博主诊断（AI驱动）
node index.js diagnose --stage "刚起号" --topic "美妆"
node index.js diagnose --stage "成长期" --topic "穿搭" --fans 2000

# 账号定位（AI驱动）★新增
node index.js position --topic "美妆"
node index.js position --topic "穿搭" --audience "学生党" --features "平价爱好者"
```

### 风格参数说明

| 风格 | 说明 |
|------|------|
| 种草 | 真实体验分享，突出使用效果 |
| 教程 | 步骤清晰，干货满满，适合收藏 |
| 日常 | 生活化叙事，有代入感 |
| 测评 | 客观分析优缺点，帮助决策 |
| 合集 | 信息密度高，实用性强 |

---

## 原有命令（保持不变）

```bash
# 选题研究
node index.js topic --topic "选题"              # 单题深挖
node index.js topic --keyword "护肤"            # 关键词研究
node index.js topic --hot                       # 热点话题

# 封面文案（模板版）
node index.js cover --topic "选题" --style "种草"

# 内容规划（模板版）
node index.js plan --name "穿搭号" --directions "种草,教程" --weekly 5
```

---

## Agent 调用接口（handle 函数）

```javascript
const xhsOps = require('xhs-ops');

// 爆款标题生成（AI）
const r1 = await xhsOps.handle({ params: { action: 'title', topic: '新手露营装备' }});

// 笔记正文生成（AI）
const r2 = await xhsOps.handle({ params: { action: 'note', title: '姐妹们！挖到宝了！', topic: '新手露营装备', style: '种草' }});

// 博主诊断（AI）★新增
const r3 = await xhsOps.handle({ params: { action: 'diagnose', stage: '刚起号', topic: '美妆' }});

// 账号定位（AI）★新增
const r4 = await xhsOps.handle({ params: { action: 'position', topic: '美妆' }});

// 选题研究
const r5 = await xhsOps.handle({ params: { action: 'topic', topic: '新手露营装备' }});

// 封面文案
const r6 = await xhsOps.handle({ params: { action: 'cover', topic: '新手露营装备', style: '种草' }});

// 内容规划
const r7 = await xhsOps.handle({ params: { action: 'plan', name: '露营号', directions: '种草,教程', weekly: 4 }});
```

### handle() 参数速查

| action | 必填参数 | 可选参数 | 说明 |
|--------|---------|---------|------|
| `title` | `topic` | `count`, `audience` | 标题生成，AI驱动 |
| `note` | `title`, `topic` | `style` | 笔记正文，AI驱动 |
| `diagnose` | `stage`, `topic` | `fans`, `困惑` | 博主诊断，AI驱动 ★新增 |
| `position` | `topic` | `audience`, `features` | 账号定位，AI驱动 ★新增 |
| `topic` | `topic` 或 `keyword` | `count`, `hot`, `competitor` | 选题研究 |
| `cover` | `topic` | `style` | 封面文案 |
| `plan` | — | `name`, `directions`, `weekly`, `weeks`, `interactive` | 内容规划 |

---

## 触发词

**AI生成**
`爆款标题` / `生成标题` / `小红书标题` / `写笔记` / `小红书笔记` / `博主诊断` / `账号诊断` / `账号定位` / `帮我定位` / `新人怎么起步`

**内容生产**
`选题研究` / `热点选题` / `封面文案` / `内容规划`

**账号成长**
`数据复盘` / `评论区运营`

**商业变现**
`品牌合作` / `种草文案`

---

## 环境配置

### LLM 配置（支持任意 OpenAI 兼容 API）

| 变量 | 说明 | 优先级 |
|------|------|--------|
| `XHS_LLM_API_KEY` | 自定义 LLM API Key | **最高** |
| `XHS_LLM_BASE_URL` | 自定义 API 地址 | **最高** |
| `XHS_LLM_MODEL` | 自定义模型名称 | **最高** |
| `OPENAI_API_KEY` | OpenAI 兼容 API Key | 中 |
| `OPENAI_BASE_URL` | API 地址（无则用 MiniMax 默认） | 中 |
| `MINIMAX_API_KEY` | MiniMax API Key | 低 |
| `LLM_MODEL` | 模型名（无则用 MiniMax 默认） | 低 |

> 优先级：显式 `XHS_LLM_*` > `OPENAI_*` > `MINIMAX_*`

### 快速切换 LLM

```bash
# 查看当前配置
node index.js llm-info

# 使用 OpenAI
export XHS_LLM_API_KEY=sk-xxx
export XHS_LLM_BASE_URL=https://api.openai.com/v1
export XHS_LLM_MODEL=gpt-4o

# 使用 Groq（免费额度）
export XHS_LLM_API_KEY=gsk_xxx
export XHS_LLM_BASE_URL=https://api.groq.com/openai/v1
export XHS_LLM_MODEL=llama-3.3-70b-versatile

# 使用 MiniMax（默认）
export MINIMAX_API_KEY=xxx

# 选题研究（独立配置）
export BRAVE_SEARCH_KEY=xxx
```

### Brave Search（选题研究用）

| 变量 | 说明 |
|------|------|
| `BRAVE_SEARCH_KEY` | Brave Search API Key（选题研究用） |

> 无 API Key 时：标题/笔记/诊断会降级到演示数据，选题研究有本地知识库可用

---

## 快速工作流

```bash
# Step 1：先做选题研究
node index.js topic --topic "露营装备"

# Step 2：AI 生成多个标题
node index.js title --topic "新手露营装备清单" --audience "上班族"

# Step 3：AI 生成完整笔记正文
node index.js note --title "姐妹们！挖到宝了！" --topic "新手露营装备清单" --style "种草"

# Step 4：生成封面文案
node index.js cover --topic "新手露营装备清单" --style "种草"

# Step 5：博主诊断（了解当前阶段该做什么）
node index.js diagnose --stage "刚起号" --topic "露营"

# Step 6：账号定位（新人起步先用这个）
node index.js position --topic "露营"
```

---

## 常见问题

**Q: 提示"无 LLM API Key"怎么办？**
> 标题和笔记生成需要 LLM 支持。请设置 `OPENAI_API_KEY` 或 `MINIMAX_API_KEY` 环境变量。

**Q: Brave Search 结果是英文？**
> v2.0 已内置翻译，搜索结果会自动翻译为中文。

**Q: 标题/笔记生成结果不满意？**
> AI 生成每次结果不同，可以多次生成挑选。也可以通过 `--audience` 参数指定目标受众来调整方向。