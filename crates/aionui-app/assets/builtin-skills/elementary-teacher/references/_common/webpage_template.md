# 交互学习网页 JSON 数据模板

## 目录
1. 通用 JSON 结构
2. 各科目卡片字段
3. Section 类型说明
4. 完整示例

## 概览
本文档定义了交互式学习网页的结构化 JSON 数据模板。脚本 `generate_lesson.py` 读取此 JSON 并渲染为完整的 HTML 交互网页。

## 核心内容

### 1. 通用 JSON 结构

```json
{
  "title": "课题/知识点名称",
  "subtitle": "X年级{科目} · 快乐学习",
  "sections": [
    {
      "type": "intro",
      "title": "课堂导入",
      "content": "导入内容（支持多行文本）",
      "image_url": "images/intro.jpg",
      "image_caption": "图片说明文字"
    },
    {
      "type": "knowledge",
      "title": "知识点标题",
      "content": "知识点详细内容...",
      "image_url": "images/knowledge1.jpg",
      "image_caption": "图片说明",
      "question": {
        "type": "thinking",
        "text": "互动题目",
        "hints": ["提示1", "提示2"],
        "options": [],
        "answer": "答案和解析"
      }
    }
  ],
  "reading_sections": [
    {"role": "", "content": "旁白/叙述内容"},
    {"role": "角色名", "content": "角色台词"}
  ],
  "fun_facts": [
    {"title": "趣味知识标题", "content": "趣味知识内容"}
  ],
  "extra_resources": [
    {"title": "拓展分类", "items": ["条目1", "条目2"]}
  ],
  "summary": "课堂总结内容"
}
```

### 2. 各科目卡片字段

除通用字段外，各科目在 JSON 根级别添加科目特定数组字段。

#### 2.1 语文 — vocab_list（生字卡）
```json
"vocab_list": [
  {
    "char": "蝌",
    "pinyin": "kē",
    "meaning": "蝌蚪，蛙或蟾蜍的幼体",
    "words": ["蝌蚪"]
  }
]
```
字段说明：
- char: 单个汉字
- pinyin: 拼音（不带声调数字，用字母标调）
- meaning: 字义解释
- words: 包含该字的词语列表（2-3个）

#### 2.2 数学 — formula_cards（公式卡）
```json
"formula_cards": [
  {
    "name": "分数基本性质",
    "formula": "a/b = (a×k)/(b×k) （k≠0）",
    "example": "1/2 = (1×3)/(2×3) = 3/6",
    "note": "分子和分母同时乘以或除以同一个不为零的数，分数的大小不变"
  }
]
```
字段说明：
- name: 公式/性质名称
- formula: 公式表达（可用 LaTeX 风格）
- example: 具体例子
- note: 注意事项/记忆口诀

#### 2.3 英语 — word_cards（单词卡）
```json
"word_cards": [
  {
    "word": "morning",
    "phonetic": "/ˈmɔːnɪŋ/",
    "meaning": "早晨，上午",
    "sentence": "Good morning, class!"
  }
]
```
字段说明：
- word: 英文单词
- phonetic: 音标
- meaning: 中文释义
- sentence: 例句

#### 2.4 科学 — concept_cards（概念卡）
```json
"concept_cards": [
  {
    "term": "蒸发",
    "definition": "液体表面发生的气化现象，在任何温度下都能发生",
    "image_desc": "湿衣服晾干是蒸发现象"
  }
]
```
字段说明：
- term: 科学概念/术语
- definition: 概念定义（适合小学生理解的语言）
- image_desc: 可配图说明的生活实例

#### 2.5 道法 — value_cards（价值观卡）
```json
"value_cards": [
  {
    "concept": "诚实",
    "quote": "言必信，行必果。——《论语》",
    "story": "列宁打碎花瓶的故事..."
  }
]
```
字段说明：
- concept: 核心道德概念
- quote: 名言警句（注明出处）
- story: 相关小故事或生活案例

### 3. Section 类型说明

| type | 说明 | 渲染效果 |
|------|------|---------|
| intro | 课堂导入区 | 显示导入内容和配图 |
| knowledge | 知识点展开区 | 显示知识点内容+配图+互动题目（思考题或选择题） |

#### 3.1 互动题目类型（question.type）

| type | 说明 | 渲染效果 |
|------|------|---------|
| thinking | 思考题 | 提示按钮+答案按钮，逐步揭示 |
| choice | 选择题 | 选项单选+提示+答案 |

**choice 类型题目需提供 options 数组：**
```json
"question": {
  "type": "choice",
  "text": "以下哪个是正确的？",
  "options": ["选项A", "选项B", "选项C"],
  "answer": "B。解析：..."
}
```

### 4. 完整示例：语文课《小蝌蚪找妈妈》

```json
{
  "title": "小蝌蚪找妈妈",
  "subtitle": "二年级语文 · 快乐学习",
  "sections": [
    {
      "type": "intro",
      "title": "课堂导入",
      "content": "春天来了，池塘里有一群小蝌蚪，它们有大大的脑袋、黑灰色的身子、长长的尾巴。可是它们找不到妈妈了...",
      "image_url": "images/pond_spring.jpg",
      "image_caption": "春天的小池塘"
    },
    {
      "type": "knowledge",
      "title": "小蝌蚪的变化",
      "content": "小蝌蚪在找妈妈的过程中，身体发生了很多变化：先长出两条后腿，再长出两条前腿，尾巴慢慢变短，最后变成了小青蛙。",
      "image_url": "images/tadpole_change.jpg",
      "image_caption": "小蝌蚪变青蛙的过程",
      "question": {
        "type": "thinking",
        "text": "小蝌蚪为什么要找妈妈？它们在找妈妈的过程中遇到了哪些动物？",
        "hints": ["想一想小蝌蚪问了哪些动物", "每个动物都告诉了小蝌蚪什么信息"],
        "options": [],
        "answer": "因为小蝌蚪不知道自己的妈妈长什么样。它们遇到了鲤鱼阿姨、乌龟和青蛙妈妈。鲤鱼告诉它们妈妈有四条腿，乌龟告诉它们妈妈有白肚皮，最后青蛙妈妈找到了它们。"
      }
    }
  ],
  "vocab_list": [
    {"char": "蝌", "pinyin": "kē", "meaning": "蝌蚪，蛙的幼体", "words": ["蝌蚪"]},
    {"char": "蚪", "pinyin": "dǒu", "meaning": "见'蝌蚪'", "words": ["蝌蚪"]},
    {"char": "鲤", "pinyin": "lǐ", "meaning": "鲤鱼，一种淡水鱼", "words": ["鲤鱼", "锦鲤"]}
  ],
  "reading_sections": [
    {"role": "", "content": "池塘里有一群小蝌蚪，大大的脑袋，黑灰色的身子，甩着长长的尾巴，快活地游来游去。"},
    {"role": "小蝌蚪", "content": "鲤鱼阿姨，我们的妈妈在哪里？"},
    {"role": "鲤鱼", "content": "你们的妈妈四条腿，宽嘴巴。你们到那边去找吧！"}
  ],
  "fun_facts": [
    {"title": "青蛙是两栖动物", "content": "青蛙既能在水里生活，也能在陆地上生活。它们的皮肤需要保持湿润，所以经常待在水边。"},
    {"title": "青蛙是益虫", "content": "一只青蛙一天能吃掉50-200只害虫，是农民伯伯的好帮手！"}
  ],
  "extra_resources": [
    {"title": "推荐阅读", "items": ["《小壁虎借尾巴》", "《棉花姑娘》", "《动物王国开大会》"]},
    {"title": "实践活动", "items": ["观察小蝌蚪变青蛙的过程（记录表）", "画一画小蝌蚪变青蛙的四个阶段"]}
  ],
  "summary": "今天我们学习了《小蝌蚪找妈妈》这篇课文，了解了小蝌蚪变青蛙的过程：先长后腿→再长前腿→尾巴变短→变成青蛙。我们还学习了生字词，知道了青蛙是益虫，要爱护小动物。"
}
```

## 注意事项

- JSON 文本字段中的引号必须使用单引号（'），避免解析错误
- 所有图片路径使用相对路径 `images/xxx.jpg`
- 图片生成后将 URL 写入 `image_url` 字段
- sectors 中 type 为 "knowledge" 的条目建议 2-4 个
- reading_sections 为可选字段（语文课建议包含，其他科目可省略）
- 确保 question 字段完整（即使不显示也要提供空值）
