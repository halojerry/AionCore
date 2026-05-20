#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短视频卖货脚本生成器
基于《短视频卖货》方法论，生成高转化率脚本
"""

import argparse
import json
import sys
from typing import Optional

# 7大爆款脚本模板定义
TEMPLATES = {
    "product-seeding": {
        "name": "产品种草式",
        "description": "生活场景切入 → 引出产品 → 产品优势 → 产品效果",
        "best_for": ["美妆护肤", "食品饮料", "日用品"],
        "structure": [
            {"section": "开场", "duration": "3-5秒", "purpose": "生活场景切入，引起共鸣"},
            {"section": "产品引出", "duration": "5-8秒", "purpose": "自然引出产品，建立期待"},
            {"section": "卖点阐述", "duration": "15-20秒", "purpose": "核心卖点+使用效果展示"},
            {"section": "行动号召", "duration": "3-5秒", "purpose": "引导购买，制造紧迫感"}
        ]
    },
    "unboxing-review": {
        "name": "开箱测评式",
        "description": "开箱氛围营造 → 产品展示 → 功能测试 → 真实体验",
        "best_for": ["数码3C", "高端商品", "新品首发"],
        "structure": [
            {"section": "开箱", "duration": "5-8秒", "purpose": "营造惊喜氛围，展示包装"},
            {"section": "外观展示", "duration": "8-10秒", "purpose": "展示产品外观、质感"},
            {"section": "功能测试", "duration": "15-20秒", "purpose": "实际使用，展示核心功能"},
            {"section": "总结推荐", "duration": "5-8秒", "purpose": "给出评价，推荐购买"}
        ]
    },
    "comparison": {
        "name": "对比种草式",
        "description": "常规方案弊端 → 竞品对比 → 产品优势突出 → 效果验证",
        "best_for": ["有竞争优势的产品", "创新产品", "升级款产品"],
        "structure": [
            {"section": "痛点抛出", "duration": "5-8秒", "purpose": "指出传统方案的弊端"},
            {"section": "对比展示", "duration": "15-20秒", "purpose": "直观对比，突出优势"},
            {"section": "效果验证", "duration": "8-10秒", "purpose": "实验证明或用户证言"},
            {"section": "购买引导", "duration": "3-5秒", "purpose": "强调性价比，引导下单"}
        ]
    },
    "knowledge": {
        "name": "知识干货式",
        "description": "话题引入 → 干货知识 → 产品特色 → 价值强调",
        "best_for": ["母婴用品", "健康保健", "教育培训", "专业知识类产品"],
        "structure": [
            {"section": "话题引入", "duration": "5-8秒", "purpose": "点明本期分享的知识话题"},
            {"section": "干货讲解", "duration": "20-30秒", "purpose": "专业知识+避坑指南"},
            {"section": "产品植入", "duration": "10-15秒", "purpose": "产品如何符合干货要点"},
            {"section": "价值总结", "duration": "3-5秒", "purpose": "强调获得感和价值"}
        ]
    },
    "problem-solving": {
        "name": "解决问题式",
        "description": "痛点问题抛出 → 解决方案 → 产品演示 → 效果证明",
        "best_for": ["解决特定痛点的产品", "功能性产品", "清洁用品"],
        "structure": [
            {"section": "问题抛出", "duration": "5-8秒", "purpose": "开门见山指出用户痛点"},
            {"section": "方案介绍", "duration": "8-10秒", "purpose": "给出完美解决方案"},
            {"section": "产品演示", "duration": "15-20秒", "purpose": "展示产品如何解决"},
            {"section": "效果证明", "duration": "5-8秒", "purpose": "前后对比或数据证明"}
        ]
    },
    "scenario": {
        "name": "场景代入式",
        "description": "场景营造 → 情感共鸣 → 产品融入 → 行动号召",
        "best_for": ["服装配饰", "礼品类", "生活方式类产品"],
        "structure": [
            {"section": "场景营造", "duration": "8-10秒", "purpose": "营造具体使用场景"},
            {"section": "情感共鸣", "duration": "10-15秒", "purpose": "引发观众情感共鸣"},
            {"section": "产品融入", "duration": "10-15秒", "purpose": "自然展示产品融入场景"},
            {"section": "行动号召", "duration": "5-8秒", "purpose": "引导体验和购买"}
        ]
    },
    "story": {
        "name": "剧情植入式",
        "description": "故事开头 → 冲突/转折 → 产品解决 → 升华主题",
        "best_for": ["品牌宣传", "有故事性的产品", "情感类产品"],
        "structure": [
            {"section": "故事开头", "duration": "10-15秒", "purpose": "有趣的故事开场"},
            {"section": "冲突转折", "duration": "15-20秒", "purpose": "遇到问题或转折"},
            {"section": "产品解决", "duration": "15-20秒", "purpose": "产品如何解决问题"},
            {"section": "主题升华", "duration": "5-10秒", "purpose": "升华情感或主题"}
        ]
    }
}

# 推荐模板匹配规则
CATEGORY_TEMPLATE_MAP = {
    "美妆": "product-seeding",
    "护肤": "product-seeding",
    "彩妆": "product-seeding",
    "食品": "product-seeding",
    "零食": "product-seeding",
    "饮料": "product-seeding",
    "数码": "unboxing-review",
    "3C": "unboxing-review",
    "手机": "unboxing-review",
    "电脑": "unboxing-review",
    "家电": "comparison",
    "母婴": "knowledge",
    "育儿": "knowledge",
    "清洁": "problem-solving",
    "家居": "problem-solving",
    "服装": "scenario",
    "配饰": "scenario",
    "首饰": "scenario",
    "礼品": "scenario",
    "教育": "knowledge",
    "健康": "problem-solving",
    "保健": "knowledge"
}


def recommend_template(category: str, selling_points: str) -> str:
    """根据产品类别推荐最适合的模板"""
    category = category.lower() if category else ""
    for key, template in CATEGORY_TEMPLATE_MAP.items():
        if key in category:
            return template
    # 默认返回产品种草式
    return "product-seeding"


def generate_script_prompt(product: str, category: str, selling_points: str,
                          template_type: str, duration: int, tone: str,
                          price: str = "", target: str = "") -> str:
    """生成用于LLM的脚本生成提示词"""
    
    template = TEMPLATES.get(template_type, TEMPLATES["product-seeding"])
    structure_text = "\n".join([
        f"  {i+1}. {s['section']}（{s['duration']}）：{s['purpose']}"
        for i, s in enumerate(template["structure"])
    ])
    
    prompt = f"""你是一个专业的短视频卖货脚本创作专家，精通《短视频卖货》方法论。

请为以下产品创作一个高转化率的短视频卖货脚本：

【产品信息】
- 产品名称：{product}
- 产品类别：{category}
- 核心卖点：{selling_points}
{f'- 价格信息：{price}' if price else ''}
{f'- 目标人群：{target}' if target else ''}
- 目标时长：{duration}秒
- 语气风格：{tone}

【使用模板】{template["name"]}
【模板逻辑】{template["description"]}

【脚本结构要求】
{structure_text}

请按以下格式输出完整脚本：

# 🎬 {product} - 短视频卖货脚本

## 📋 脚本信息
- **模板类型**：{template["name"]}
- **目标时长**：{duration}秒
- **语气风格**：{tone}

## 📝 完整口播文案

（按时间轴分段，每段标注时长）

### 1. 【开场钩子】（X秒）
[文案内容...]

**画面指导**：[镜头建议、场景描述]

### 2. [下一部分]...
（依此类推，覆盖全部结构段落）

## 🎨 拍摄建议
- **BGM推荐**：
- **字幕样式**：
- **标签建议**：

## 💡 创作要点
- [基于方法论的关键提示]

请确保文案口语化、有感染力，符合抖音/快手平台的风格。"""

    return prompt


def main():
    parser = argparse.ArgumentParser(
        description='短视频卖货脚本生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 generate_script.py --product "XX牌粉底液" --category "美妆" --selling-point "持妆12小时不脱妆"
  python3 generate_script.py --product "智能扫地机器人" --category "家电" --template comparison --duration 45
        """
    )
    
    parser.add_argument('--product', '-p', required=True, help='产品名称')
    parser.add_argument('--category', '-c', default='', help='产品类别')
    parser.add_argument('--selling-point', '-s', default='', help='核心卖点')
    parser.add_argument('--price', default='', help='价格信息')
    parser.add_argument('--target', '-t', default='', help='目标人群')
    parser.add_argument('--template', choices=list(TEMPLATES.keys()),
                       help='脚本模板类型（不指定则自动推荐）')
    parser.add_argument('--duration', type=int, default=30,
                       help='目标视频时长（秒），默认30')
    parser.add_argument('--tone', choices=['professional', 'casual', 'humorous', 'emotional'],
                       default='casual', help='语气风格')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--list-templates', action='store_true',
                       help='列出所有可用模板')
    
    args = parser.parse_args()
    
    # 列出模板
    if args.list_templates:
        print("\n📋 可用脚本模板：\n")
        for key, template in TEMPLATES.items():
            print(f"  {key:20} - {template['name']}")
            print(f"  {'':20}   适用：{', '.join(template['best_for'])}")
            print(f"  {'':20}   逻辑：{template['description']}\n")
        return
    
    # 自动推荐模板
    template_type = args.template
    if not template_type:
        template_type = recommend_template(args.category, args.selling_point)
        print(f"\n💡 根据产品类别推荐模板：{TEMPLATES[template_type]['name']}")
    
    # 生成提示词
    prompt = generate_script_prompt(
        product=args.product,
        category=args.category,
        selling_points=args.selling_point,
        template_type=template_type,
        duration=args.duration,
        tone=args.tone,
        price=args.price,
        target=args.target
    )
    
    # 输出结果
    output = f"""# 短视频卖货脚本生成任务

## 输入参数
- 产品：{args.product}
- 类别：{args.category or '未指定'}
- 卖点：{args.selling_point or '未指定'}
- 模板：{TEMPLATES[template_type]['name']}
- 时长：{args.duration}秒

## 使用方法

请将以下提示词发送给 AI 助手生成脚本：

---

{prompt}

---

## 模板说明
{TEMPLATES[template_type]['description']}

结构：
"""
    for s in TEMPLATES[template_type]['structure']:
        output += f"  - {s['section']}（{s['duration']}）：{s['purpose']}\n"
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\n✅ 脚本任务已保存到：{args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
