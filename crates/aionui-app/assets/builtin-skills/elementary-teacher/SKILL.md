---
name: elementary-teacher
description: 小学全科教学助手（语文/数学/英语/科学/道法）的一键备课技能。输入课题，自动生成九件套：教案、讲课稿、导学案、分层习题、配图、交互学习网页、PPT大纲、播客稿、互动教学游戏。基于2022版新课标核心素养，覆盖1-6年级全部科目。
metadata:
  requires:
    bins: ["officecli"]
---

# 小学全科备课技能 🎒

## 技能简介

一键为小学全科（语文/数学/英语/科学/道法）课文或知识点生成全套**九件套**备课资源，适用**1-6年级**，帮助老师从繁琐的备课中解放出来！

**v3.0.0 重大升级**：从语文单科扩展为小学全科（5科目），新增科目识别、科目特定PPT结构、科目特定卡片组件、科目特定游戏类型。

## 适用人群

- 小学教师（1-6年级，全科目）
- 教研组长、备课组长
- 师范生实习备课
- 教学研究人员

## 科目速查表

不确定科目或格式时，**必须向用户确认**！

| 科目 | 默认习题格式 | 默认PPT页数 | 网页卡片字段 | 游戏类型 | 配图风格 | 教学目标维度 |
|------|-------------|------------|-------------|---------|---------|------------|
| 语文 | .docx | 11页 | vocab_list | 故事通关 | 卡通/水墨插画 | 文化自信、语言运用、思维能力、审美创造 |
| 数学 | .xlsx | 11页 | formula_cards | 算术闯关 | 几何示意图 | 数感、量感、符号意识、运算能力、几何直观、空间观念、推理意识、数据意识、模型意识、应用意识、创新意识 |
| 英语 | .docx | 11页 | word_cards | 情景对话 | 卡通场景 | 语言能力、文化意识、思维品质、学习能力 |
| 科学 | .docx | 11页 | concept_cards | 实验探索 | 实物/示意图 | 科学观念、科学思维、探究实践、态度责任 |
| 道法 | .docx | 11页 | value_cards | 道德抉择 | 生活场景 | 政治认同、道德修养、法治观念、健全人格、责任意识 |

用户说"Excel"→ 任何科目都输出 .xlsx。
用户提到"动画""好看""生动"→ 使用 morph-ppt 技能生成带 Morph 动画的 PPT。

## 九件套清单

| 序号 | 资源名称 | 交付格式 | 说明 |
|------|----------|---------|------|
| 1 | 教案 | .docx | 基于2022版新课标核心素养，含完整教学过程和板书设计 |
| 2 | 讲课稿 | .docx | 口语化课堂讲授脚本，含导入、新课讲授、巩固练习、课堂小结、作业布置 |
| 3 | 导学案 | .docx | 引导学生自主学习，含学习目标、预习内容、自主探究、合作探究、当堂检测 |
| 4 | 分层习题 | .docx 或 .xlsx | 基础题 + 提高题 + 拓展题三档（数学默认.xlsx，其他.docx） |
| 5 | 配图 | images/ 目录 | 根据科目风格生成，嵌入 Office 文档和 HTML |
| 6 | 交互学习网页 | .html | 含进度条、成就系统、点名转盘、科目特定卡片组件 |
| 7 | PPT | .pptx | 11页起，不可缩减（用户提"动画"→ morph-ppt） |
| 8 | 播客稿 | .docx | 课文背景、知识点预习、思考题引导 |
| 9 | 互动教学游戏 | .html | 5-10关闯关游戏，选对过关，选错重选，通关后复盘 |

## 操作步骤

### 第一步：获取课题信息

- 从用户输入中获取**科目**、**课题/知识点**、**年级**
- **科目识别优先**，不确定时必须询问！
- 确认**课时安排**、**教学重点**等基本信息
- 若用户未提供足够信息，列出需要确认的项目

### 第二步：生成核心教学资源（教案 + 讲课稿 + 导学案 + 播客稿）

**先出 Markdown，再转 Office，不要混在一起！Office 命令一条一条执行，检查 exit code。**

#### 2.1 教案生成 → .docx (officecli-docx)

参考 [references/_common/教案结构规范.md](references/_common/教案结构规范.md)，按科目加载 [references/{科目}/教学大纲要点.md]。

包含8大模块：基本信息、教学目标、教学重难点、教学准备、教学过程、板书设计、作业布置、教学反思。

教学目标必须基于对应科目的**2022版新课标核心素养维度**（见科目速查表），不得使用旧版三维目标。

**导入环节**标注 3-5 分钟，含教师语言和预期学生回应。
**新授环节**标注 15-20 分钟，分步骤。
**巩固环节**标注 5-8 分钟。
**小结**标注 2-3 分钟。
**作业布置**标注 1-2 分钟。

转为 .docx 时使用 officecli-docx 技能。

#### 2.2 讲课稿生成 → .docx (officecli-docx)

参考 [references/_common/讲课稿撰写要点.md](references/_common/讲课稿撰写要点.md)。

语言口语化，用「师：」「生：」标注对话。
包含5大环节：导入（3-5分钟）、新课讲授（15-20分钟）、巩固练习（5-8分钟）、课堂小结（2-3分钟）、作业布置（1-2分钟）。

#### 2.3 导学案生成 → .docx (officecli-docx)

结构要求：
- 学习目标
- 预习内容区（留空给学生填写）
- 自主探究区
- 合作探究区
- 当堂检测区

#### 2.4 播客稿生成 → .docx (officecli-docx)

内容：课题背景、知识点预习、思考题引导，可直接用于播客录制。

### 第三步：生成配套资源（习题 + PPT大纲）

#### 3.1 分层习题 → .docx 或 .xlsx

参考 [references/_common/习题分层标准.md](references/_common/习题分层标准.md)。

按科目选格式：
- **数学**：默认 .xlsx（每行一道题，A列题号 B列题目 C列空），使用 officecli-xlsx 技能
- **语文/英语/科学/道法**：默认 .docx（文本形式，分层标注），使用 officecli-docx 技能
- 用户说"Excel"→ 任何科目都输出 .xlsx

分层：
- **基础题**（3-5道）：识记理解，面向全体学生
- **提高题**（3-5道）：应用分析，面向中等及以上学生
- **拓展题**（2-3道）：综合创造，面向学有余力学生

#### 3.2 PPT大纲 → .pptx

**PPT ≥ 11 页，不可缩减。**

用户偏好 → 技能选择：
- 提到"动画""好看""生动" → 使用 [../morph-ppt/SKILL.md](../morph-ppt/SKILL.md)（跨页 Morph 变形动画）
- 默认/未指定 → 使用 [../officecli-pptx/SKILL.md](../officecli-pptx/SKILL.md)（标准静态演示）

各科目 PPT 结构（11 页起）：

| 页码 | 语文 | 数学 | 英语 | 科学 | 道法 |
|------|------|------|------|------|------|
| 1 | 封面 | 封面 | 封面 | 封面 | 封面 |
| 2 | 教学目标 | 教学目标 | 教学目标 | 教学目标 | 教学目标 |
| 3 | 课文简介 | 复习导入 | Warm-up | 问题情境 | 案例引入 |
| 4 | 生字词 | 新知讲授1 | New Words | 猜想假设 | 分析1 |
| 5 | 课文分析1 | 新知讲授2 | Dialogue1 | 实验1 | 分析2 |
| 6 | 课文分析2 | 新知讲授3 | Dialogue2 | 实验2 | 讨论 |
| 7 | 课文分析3 | 例题讲解 | Grammar | 观察记录 | 归纳 |
| 8 | 重点赏析 | 练习巩固 | Practice | 结论 | 践行 |
| 9 | 结构梳理 | 归纳总结 | Game | 应用拓展 | 互动 |
| 10 | 互动环节 | 互动环节 | Culture | 互动环节 | 拓展 |
| 11 | 作业布置 | 作业布置 | Homework | 作业布置 | 作业布置 |

### 第四步：配图生成（不可跳过）

**图片生成是必需步骤，不可跳过！**

根据科目选择风格，为以下场景生成配图：

- 教案封面配图 ×1
- 每个知识点配图 ×1（2-4 个知识点）
- 游戏封面 + 每个场景配图（5-10 张）

| 科目 | 风格 | 配图描述模板 |
|------|------|------------|
| 语文 | 卡通/水墨插画 | "小学课文{课题}插画，水彩风格，明亮活泼" |
| 数学 | 几何示意图 | "小学数学{知识点}示意图，简洁清晰，彩色标注" |
| 英语 | 卡通场景 | "小学英语{主题}场景，卡通风格，生动有趣" |
| 科学 | 实物/示意图 | "小学科学{现象}图示，写实清晰，标注详细" |
| 道法 | 生活场景 | "小学生{主题}场景，温馨写实，积极向上" |

图片保存到 `./user-data/images/`，然后嵌入 Office 文档和 HTML 中。

### 第五步：交互学习网页

#### 5.1 构建 JSON 数据

通用结构参考 [references/_common/webpage_template.md](references/_common/webpage_template.md)。

各科目卡片字段：

| 科目 | JSON 字段 | 内容样例 |
|------|----------|---------|
| 语文 | vocab_list | {char:"蝌", pinyin:"kē", meaning:"...", words:["蝌蚪"]} |
| 数学 | formula_cards | {name:"分数基本性质", formula:"a/b = a×k/b×k", example:"...", note:"..."} |
| 英语 | word_cards | {word:"morning", phonetic:"/ˈmɔːnɪŋ/", meaning:"早晨", sentence:"..."} |
| 科学 | concept_cards | {term:"蒸发", definition:"...", image_desc:"..."} |
| 道法 | value_cards | {concept:"诚实", quote:"...", story:"..."} |

JSON 文本字段中的引号必须使用单引号（'），避免解析错误。

#### 5.2 调用脚本

```bash
python3 scripts/generate_lesson.py \
  --json-file ./user-data/{课题}_data.json \
  --output ./user-data/{课题}_交互网页.html \
  --subject {科目}
```

脚本按 `--subject` 渲染对应的卡片组件。

### 第六步：互动教学游戏

#### 6.1 游戏类型

| 科目 | 类型 | 设计逻辑 |
|------|------|---------|
| 语文 | 故事通关 | 课文情节拆成 5-10 关，选对情节推进 |
| 数学 | 算术闯关 | 题目拆成 5-10 关，算对进入下一关 |
| 英语 | 情景对话 | 对话拆成场景，选正确回应推进 |
| 科学 | 实验探索 | 实验步骤拆成关卡，选正确步骤推进 |
| 道法 | 道德抉择 | 情境设置，选正确行为推进剧情 |

#### 6.2 生成步骤

1. 将内容拆分为 5-10 个场景
2. 每个场景 3 个选项（1 正确 + 2 干扰）
3. 生成 JSON → 生成配图 → 更新图片路径
4. 调用脚本：

参考 [references/_common/game_template.md](references/_common/game_template.md) 了解 JSON 结构。

```bash
python3 scripts/build_game.py \
  ./user-data/game_config.json \
  assets/game_template.html \
  ./user-data/{课题}通关游戏.html
```

**注意**：选错留在当前场景重新选择，选对才进入下一场景。JSON文本字段中的引号使用单引号。

### 第七步：可选增强

- **思维导图**：用户要求时，用 [../mermaid/SKILL.md](../mermaid/SKILL.md) 生成知识结构图
- **PDF 打包**：用户要求时，用 [../pdf/SKILL.md](../pdf/SKILL.md) 将全部 Markdown 转为 PDF 合集

### 第八步：资源整合与交付

按以下顺序交付（优先 Office 文件）：

| # | 内容 | 交付文件 |
|---|------|---------|
| 1 | 教案 | 📄 教案_{课题}.docx |
| 2 | 讲课稿 | 📄 讲课稿_{课题}.docx |
| 3 | 导学案 | 📄 导学案_{课题}.docx |
| 4 | 分层习题 | 📄 习题_{课题}.docx 或 📊 习题_{课题}.xlsx |
| 5 | 配图 | 🖼️ images/ 目录下（已嵌入文档） |
| 6 | 交互网页 | 🌐 {课题}_交互网页.html |
| 7 | PPT | 📊 PPT_{课题}.pptx |
| 8 | 播客稿 | 📄 播客稿_{课题}.docx |
| 9 | 教学游戏 | 🎮 {课题}通关游戏.html |

交付时提示：

> 全套九件套已生成！所有 Office 文件可直接编辑使用。交互网页和游戏用浏览器打开即可。

## 资源索引

### 必要脚本
- [scripts/generate_lesson.py](scripts/generate_lesson.py)
  - 用途：将结构化JSON数据转换为交互式学习网页（含点名转盘、科目特定卡片、朗读区、进度条、成就系统）
  - 参数：`--json-file`（必需）、`--output`（必需）、`--subject`（必需，chinese/math/english/science/morality）、`--students`（可选）
- [scripts/build_game.py](scripts/build_game.py)
  - 用途：将game_config.json和HTML模板合成为通关游戏单文件HTML（图片Base64嵌入）
  - 参数：`json_config_path`、`template_path`、`output_html_path`

### 通用参考
- [references/_common/教案结构规范.md](references/_common/教案结构规范.md) — 教案撰写标准（8大模块规范+各科目核心素养维度对照）
- [references/_common/讲课稿撰写要点.md](references/_common/讲课稿撰写要点.md) — 讲课流程规范（5环节+语言技巧）
- [references/_common/习题分层标准.md](references/_common/习题分层标准.md) — 习题难度分级（基础/提高/拓展三档，通用+科目特定题型）
- [references/_common/webpage_template.md](references/_common/webpage_template.md) — 交互式学习网页JSON数据结构模板
- [references/_common/game_template.md](references/_common/game_template.md) — 通关游戏JSON数据结构模板
- [references/_common/ppt-outline-template.md](references/_common/ppt-outline-template.md) — 各科目PPT大纲模板

### 科目参考（按需加载）
- [references/语文/教学大纲要点.md](references/语文/教学大纲要点.md) — 语文1-6年级学段要求
- [references/数学/教学大纲要点.md](references/数学/教学大纲要点.md) — 数学1-6年级学段要求
- [references/英语/教学大纲要点.md](references/英语/教学大纲要点.md) — 英语1-6年级学段要求
- [references/科学/教学大纲要点.md](references/科学/教学大纲要点.md) — 科学1-6年级学段要求
- [references/道法/教学大纲要点.md](references/道法/教学大纲要点.md) — 道法1-6年级学段要求

### 输出资产
- [assets/lesson_template.html](assets/lesson_template.html) — 交互式学习网页HTML模板（手动填充用）
- [assets/game_template.html](assets/game_template.html) — 通关游戏HTML模板（脚本自动注入用）
- [assets/learning-web-template.html](assets/learning-web-template.html) — 旧版学习网页模板（兼容保留）

## 外部技能依赖

- [../officecli-docx/SKILL.md](../officecli-docx/SKILL.md) — Word 文档生成（教案、讲课稿、导学案、播客稿、习题）
- [../officecli-xlsx/SKILL.md](../officecli-xlsx/SKILL.md) — Excel 表格生成（数学习题）
- [../officecli-pptx/SKILL.md](../officecli-pptx/SKILL.md) — PPT 演示文稿生成（标准静态演示）
- [../morph-ppt/SKILL.md](../morph-ppt/SKILL.md) — Morph 动画 PPT（用户要求动画效果时）
- [../mermaid/SKILL.md](../mermaid/SKILL.md) — 思维导图/知识结构图
- [../pdf/SKILL.md](../pdf/SKILL.md) — PDF 打包转换

## 注意事项

- **科目识别优先**，不确定时必须询问用户
- 所有资源生成要**符合小学生认知水平**，语言贴近儿童
- 教案和讲课稿要体现**新课程理念**（以学生为中心，教师为主导）
- 习题设计要**循序渐进**，激发学习兴趣
- 配图风格要与**科目和内容匹配**
- 确保生成的内容**专业、准确、有教育价值**
- 教学目标必须基于**2022版新课标核心素养**对应科目维度
- **图片生成是必需步骤（关键！）**：交互网页和通关游戏都必须生成配图
- **JSON格式规范**：文本字段中的引号使用单引号（'）
- **图片路径规范**：所有图片保存在 `user-data/images/` 目录下
- 通关游戏的选项设计：**选错留在当前场景重新选择**
- 脚本仅用于处理技术性任务，内容创作由智能体主导
- **先出 Markdown 再转 Office，不要混在一起**
- **Office 命令一条一条执行，检查 exit code**
- **PPT ≥ 11 页，不可缩减**
- **数学习题默认 .xlsx**

## 版本更新日志

### v3.0.0
- 🆕 从语文单科扩展为小学全科（5科目：语文/数学/英语/科学/道法）
- 🆕 新增科目速查表（格式/风格/卡片字段/游戏类型一键对照）
- 🆕 新增4个科目教学大纲参考文件
- 🆕 网页脚本支持 --subject 参数，自动切换科目卡片组件
- 🆕 各科目特定PPT结构（11页）
- 🆕 各科目特定游戏类型（故事通关/算术闯关/情景对话/实验探索/道德抉择）
- 保留 v2.0.0 全部功能：交互网页、通关游戏、点名转盘、成就系统
