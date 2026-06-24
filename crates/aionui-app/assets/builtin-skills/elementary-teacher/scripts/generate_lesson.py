#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小学全科交互式学习网页生成器

功能：
1. 读取结构化JSON数据
2. 根据科目生成包含点名转盘、科目特定卡片、朗读区、进度条、成就系统的交互式HTML网页
3. 天蓝浅紫配色，活泼明亮的校园风格

支持科目：chinese（语文）、math（数学）、english（英语）、science（科学）、morality（道法）
"""

import json
import sys
import os
import argparse


SUBJECT_CONFIG = {
    'chinese': {
        'name': '语文',
        'title_prefix': '语文小课堂',
        'card_field': 'vocab_list',
        'card_type': 'vocab',
        'card_label': '生字卡学习',
        'card_icon': '📝',
        'card_tip': '💡 点击生字卡翻转查看释义和组词，多读多写记得牢！',
    },
    'math': {
        'name': '数学',
        'title_prefix': '数学小课堂',
        'card_field': 'formula_cards',
        'card_type': 'formula',
        'card_label': '公式卡学习',
        'card_icon': '🔢',
        'card_tip': '💡 理解公式的含义，记住公式的用法，做题更轻松！',
    },
    'english': {
        'name': '英语',
        'title_prefix': '英语小课堂',
        'card_field': 'word_cards',
        'card_type': 'word',
        'card_label': '单词卡学习',
        'card_icon': '🔤',
        'card_tip': '💡 点击单词卡翻转查看释义和例句，多读多说记得牢！',
    },
    'science': {
        'name': '科学',
        'title_prefix': '科学小课堂',
        'card_field': 'concept_cards',
        'card_type': 'concept',
        'card_label': '概念卡学习',
        'card_icon': '🔬',
        'card_tip': '💡 点击概念卡翻转查看定义和实例，科学就在身边！',
    },
    'morality': {
        'name': '道法',
        'title_prefix': '道法小课堂',
        'card_field': 'value_cards',
        'card_type': 'value',
        'card_label': '价值观卡学习',
        'card_icon': '💝',
        'card_tip': '💡 点击卡片翻转查看名言和故事，好品德伴成长！',
    },
}


def generate_vocab_cards_html(vocab_list):
    """生成语文生字卡HTML"""
    if not vocab_list:
        return ''

    html = '''
        <!-- 生字卡区域 -->
        <div class="section">
            <h2>📝 生字卡学习</h2>
            <div class="vocab-grid">
'''
    for idx, vocab in enumerate(vocab_list):
        char = vocab.get('char', '')
        pinyin = vocab.get('pinyin', '')
        words = vocab.get('words', [])
        meaning = vocab.get('meaning', '')
        words_str = '、'.join(words)
        html += f'''
                <div class="vocab-card" onclick="flipCard(this, 'card-back-{idx}')">
                    <div class="card-front">
                        <div class="card-char">{char}</div>
                        <div class="card-pinyin">{pinyin}</div>
                    </div>
                    <div class="card-back" id="card-back-{idx}">
                        <div class="card-meaning">{meaning}</div>
                        <div class="card-words">组词：{words_str}</div>
                    </div>
                </div>
'''
    html += '''
            </div>
            <div class="vocab-tips">
                <p>💡 点击生字卡翻转查看释义和组词，多读多写记得牢！</p>
            </div>
        </div>
'''
    return html


def generate_formula_cards_html(formula_cards):
    """生成数学公式卡HTML"""
    if not formula_cards:
        return ''

    html = '''
        <!-- 公式卡区域 -->
        <div class="section">
            <h2>🔢 公式卡学习</h2>
            <div class="formula-grid">
'''
    for idx, card in enumerate(formula_cards):
        name = card.get('name', '')
        formula = card.get('formula', '')
        example = card.get('example', '')
        note = card.get('note', '')
        html += f'''
                <div class="formula-card" onclick="flipCard(this, 'formula-back-{idx}')">
                    <div class="card-front">
                        <div class="formula-name">{name}</div>
                        <div class="formula-expr">{formula}</div>
                    </div>
                    <div class="card-back" id="formula-back-{idx}">
                        <div class="formula-example">例子：{example}</div>
                        <div class="formula-note">{note}</div>
                    </div>
                </div>
'''
    html += '''
            </div>
            <div class="vocab-tips">
                <p>💡 点击公式卡翻转查看例子和注意事项！理解公式，灵活运用！</p>
            </div>
        </div>
'''
    return html


def generate_word_cards_html(word_cards):
    """生成英语单词卡HTML"""
    if not word_cards:
        return ''

    html = '''
        <!-- 单词卡区域 -->
        <div class="section">
            <h2>🔤 单词卡学习</h2>
            <div class="word-grid">
'''
    for idx, card in enumerate(word_cards):
        word = card.get('word', '')
        phonetic = card.get('phonetic', '')
        meaning = card.get('meaning', '')
        sentence = card.get('sentence', '')
        html += f'''
                <div class="word-card" onclick="flipCard(this, 'word-back-{idx}')">
                    <div class="card-front">
                        <div class="word-text">{word}</div>
                        <div class="word-phonetic">{phonetic}</div>
                    </div>
                    <div class="card-back" id="word-back-{idx}">
                        <div class="word-meaning">{meaning}</div>
                        <div class="word-sentence">例句：{sentence}</div>
                    </div>
                </div>
'''
    html += '''
            </div>
            <div class="vocab-tips">
                <p>💡 点击单词卡翻转查看释义和例句！多读多说，英语更棒！</p>
            </div>
        </div>
'''
    return html


def generate_concept_cards_html(concept_cards):
    """生成科学概念卡HTML"""
    if not concept_cards:
        return ''

    html = '''
        <!-- 概念卡区域 -->
        <div class="section">
            <h2>🔬 概念卡学习</h2>
            <div class="concept-grid">
'''
    for idx, card in enumerate(concept_cards):
        term = card.get('term', '')
        definition = card.get('definition', '')
        image_desc = card.get('image_desc', '')
        html += f'''
                <div class="concept-card" onclick="flipCard(this, 'concept-back-{idx}')">
                    <div class="card-front">
                        <div class="concept-term">{term}</div>
                    </div>
                    <div class="card-back" id="concept-back-{idx}">
                        <div class="concept-def">{definition}</div>
                        <div class="concept-example">生活实例：{image_desc}</div>
                    </div>
                </div>
'''
    html += '''
            </div>
            <div class="vocab-tips">
                <p>💡 点击概念卡翻转查看定义和实例！科学就在我们身边！</p>
            </div>
        </div>
'''
    return html


def generate_value_cards_html(value_cards):
    """生成道法价值观卡HTML"""
    if not value_cards:
        return ''

    html = '''
        <!-- 价值观卡区域 -->
        <div class="section">
            <h2>💝 价值观卡学习</h2>
            <div class="value-grid">
'''
    for idx, card in enumerate(value_cards):
        concept = card.get('concept', '')
        quote = card.get('quote', '')
        story = card.get('story', '')
        html += f'''
                <div class="value-card" onclick="flipCard(this, 'value-back-{idx}')">
                    <div class="card-front">
                        <div class="value-concept">{concept}</div>
                    </div>
                    <div class="card-back" id="value-back-{idx}">
                        <div class="value-quote">{quote}</div>
                        <div class="value-story">{story}</div>
                    </div>
                </div>
'''
    html += '''
            </div>
            <div class="vocab-tips">
                <p>💡 点击卡片翻转查看名言和小故事！好品德伴我们成长！</p>
            </div>
        </div>
'''
    return html


def generate_cards_html(json_data, subject):
    """根据科目生成对应的卡片HTML"""
    config = SUBJECT_CONFIG.get(subject, SUBJECT_CONFIG['chinese'])
    field = config['card_field']
    cards = json_data.get(field, [])

    generators = {
        'vocab': generate_vocab_cards_html,
        'formula': generate_formula_cards_html,
        'word': generate_word_cards_html,
        'concept': generate_concept_cards_html,
        'value': generate_value_cards_html,
    }

    generator = generators.get(config['card_type'])
    if generator:
        return generator(cards)
    return ''


def generate_html(json_data, subject='chinese', student_list=None):
    """
    根据JSON数据生成交互式HTML网页

    Args:
        json_data: 包含网页内容的字典
        subject: 科目 (chinese/math/english/science/morality)
        student_list: 学生名单列表（可选）

    Returns:
        HTML字符串
    """
    config = SUBJECT_CONFIG.get(subject, SUBJECT_CONFIG['chinese'])
    subject_name = config['name']
    title_prefix = config['title_prefix']

    title = json_data.get('title', f'{subject_name}课')
    subtitle = json_data.get('subtitle', '')
    sections = json_data.get('sections', [])
    fun_facts = json_data.get('fun_facts', [])
    extra_resources = json_data.get('extra_resources', [])
    summary = json_data.get('summary', '')
    reading_sections = json_data.get('reading_sections', [])

    # 默认学生名单
    if student_list is None:
        student_list = [
            '张宇轩', '李思涵', '王浩然', '陈雨桐', '刘子墨',
            '赵一诺', '周嘉诚', '孙婉清', '黄梓涵', '林俊熙',
            '徐可欣', '郭晨阳', '马语彤', '何沐辰', '高欣怡',
            '唐子睿', '宋依然', '郑博文', '韩若曦', '蔡承泽'
        ]

    # === 生成引入区HTML ===
    intro_html = ''
    for section in sections:
        if section.get('type') == 'intro':
            intro_html = '''
        <!-- 引入区 -->
        <div class="section">
            <h2>📖 课堂导入</h2>
            <div class="story-content">
'''
            for line in section.get('content', '').split('\n'):
                if line.strip():
                    intro_html += f'                <p>{line}</p>\n'

            if section.get('image_url'):
                intro_html += f'''
            </div>
            <div class="image-container">
                <img src="{section.get('image_url')}" alt="{section.get('image_caption', '')}">
                <p>{section.get('image_caption', '')}</p>
            </div>
        </div>
'''
            else:
                intro_html += '''            </div>
        </div>
'''
            break

    # === 生成朗读区HTML（语文课专用） ===
    reading_html = ''
    if reading_sections:
        reading_html = '''
        <!-- 朗读区 -->
        <div class="section">
            <h2>🔊 课文朗读</h2>
            <div class="reading-area">
'''
        for idx, rs in enumerate(reading_sections):
            role = rs.get('role', '')
            content = rs.get('content', '')
            if role:
                reading_html += f'''
                <div class="reading-block role-block">
                    <span class="role-tag">{role}</span>
                    <p>{content}</p>
                </div>
'''
            else:
                reading_html += f'''
                <div class="reading-block narrator-block">
                    <p>{content}</p>
                </div>
'''
        reading_html += '''
            </div>
            <div class="reading-tips">
                <p>💡 朗读小贴士：注意语气、停顿和感情，体会语言的魅力！</p>
            </div>
        </div>
'''

    # === 生成科目特定卡片HTML ===
    cards_html = generate_cards_html(json_data, subject)

    # === 生成知识点展开区HTML ===
    knowledge_html = f'''
        <!-- 知识点展开区 -->
        <div class="section">
            <h2>📚 深入理解</h2>
'''
    knowledge_count = 1
    for section in sections:
        if section.get('type') == 'knowledge':
            question = section.get('question', {})
            knowledge_html += f'''
            <div class="knowledge-point">
                <h3>知识点{knowledge_count}：{section.get('title', '')}</h3>
                <div class="story-content">
'''
            for line in section.get('content', '').split('\n'):
                if line.strip():
                    knowledge_html += f'                    <p>{line}</p>\n'

            knowledge_html += '''                </div>
'''

            if section.get('image_url'):
                knowledge_html += f'''
                <div class="image-container">
                    <img src="{section.get('image_url')}" alt="{section.get('image_caption', '')}">
                    <p>{section.get('image_caption', '')}</p>
                </div>
'''

            # 互动题目
            if question:
                question_type = question.get('type', 'thinking')
                question_text = question.get('text', '')
                hints = question.get('hints', [])
                answer = question.get('answer', '')
                options = question.get('options', [])

                question_title = '🤔 互动思考题' if question_type == 'thinking' else '🤔 互动选择题'

                knowledge_html += f'''
                <div class="interactive-question">
                    <h4>{question_title}</h4>
                    <div class="question-text">
                        {question_text}
                    </div>
'''

                if question_type == 'choice' and options:
                    knowledge_html += '''                    <div class="options">
'''
                    for i, option in enumerate(options):
                        knowledge_html += f'''                        <div class="option">
                            <input type="radio" name="q{knowledge_count}" value="{chr(65+i)}">
                            <label>{chr(65+i)}. {option}</label>
                        </div>
'''
                    knowledge_html += '''                    </div>
'''

                for i, hint in enumerate(hints):
                    knowledge_html += f'''                    <button class="hint-button" onclick="showHint('hint{knowledge_count}-{i+1}')">💡 提示{i+1}</button>
'''

                knowledge_html += f'''                    <button class="answer-button" onclick="showAnswer('answer{knowledge_count}')">✅ 显示答案</button>
'''

                for i, hint in enumerate(hints):
                    knowledge_html += f'''                    <div class="hint" id="hint{knowledge_count}-{i+1}">
                        <p>💡 提示{i+1}：{hint}</p>
                    </div>
'''

                knowledge_html += f'''                    <div class="answer" id="answer{knowledge_count}">
                        <p>✅ 答案：{answer}</p>
                    </div>
                </div>
'''

            knowledge_html += '''            </div>
'''
            knowledge_count += 1

    knowledge_html += '''        </div>
'''

    # === 生成趣味补充HTML ===
    fun_facts_html = ''
    if fun_facts:
        fun_facts_html = '''
        <!-- 趣味补充 -->
        <div class="section">
            <h2>🌟 趣味知识</h2>
'''
        for fact in fun_facts:
            fun_facts_html += f'''
            <div class="fun-fact">
                <h4>{fact.get('title', '')}</h4>
                <p>{fact.get('content', '')}</p>
            </div>
'''
        fun_facts_html += '''        </div>
'''

    # === 生成课外拓展HTML ===
    extra_html = ''
    if extra_resources:
        extra_html = '''
        <!-- 课外拓展 -->
        <div class="section">
            <h2>🔭 课外拓展</h2>
'''
        for resource in extra_resources:
            extra_html += f'''
            <div class="extra-resources">
                <h4>{resource.get('title', '')}</h4>
                <ul>
'''
            for item in resource.get('items', []):
                extra_html += f'                    <li>{item}</li>\n'
            extra_html += '''                </ul>
            </div>
'''
        extra_html += '''        </div>
'''

    # === 计算总问题数用于进度条 ===
    total_questions = sum(1 for s in sections if s.get('type') == 'knowledge' and s.get('question'))

    # === 生成完整HTML ===
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_prefix} - {title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
            background: linear-gradient(135deg, #e0f7fa 0%, #e8eaf6 30%, #f3e5f5 60%, #fce4ec 100%);
            color: #333;
            min-height: 100vh;
            position: relative;
        }}

        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image:
                radial-gradient(circle at 10% 20%, rgba(100, 181, 246, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 90% 80%, rgba(186, 104, 200, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(129, 212, 250, 0.08) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }}

        h1 {{
            text-align: center;
            background: linear-gradient(135deg, #42a5f5, #ab47bc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
            font-size: 2.8em;
            text-shadow: none;
            padding: 20px 0 5px;
        }}

        .subtitle {{
            text-align: center;
            color: #7e57c2;
            margin-bottom: 25px;
            font-size: 1.2em;
            font-style: italic;
        }}

        .section {{
            background: rgba(255, 255, 255, 0.92);
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 25px;
            box-shadow: 0 6px 20px rgba(100, 100, 200, 0.12);
            border: 2px solid rgba(171, 71, 188, 0.15);
            backdrop-filter: blur(5px);
        }}

        .section h2 {{
            background: linear-gradient(135deg, #42a5f5, #7e57c2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 20px;
            font-size: 1.7em;
            border-bottom: 2px solid rgba(171, 71, 188, 0.2);
            padding-bottom: 10px;
        }}

        .section h3 {{
            color: #5c6bc0;
            margin-top: 22px;
            margin-bottom: 12px;
            font-size: 1.3em;
        }}

        .story-content {{
            font-size: 1.1em;
            line-height: 1.9;
            margin-bottom: 18px;
            color: #424242;
        }}

        .image-container {{
            text-align: center;
            margin: 22px 0;
        }}

        .image-container img {{
            max-width: 70%;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15);
            border: 3px solid rgba(171, 71, 188, 0.2);
        }}

        .image-container p {{
            margin-top: 10px;
            font-style: italic;
            color: #7e57c2;
            font-size: 0.95em;
        }}

        /* 朗读区样式 */
        .reading-area {{
            background: linear-gradient(135deg, #e3f2fd, #ede7f6);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
        }}

        .reading-block {{
            margin-bottom: 12px;
            padding: 12px 18px;
            border-radius: 8px;
            line-height: 1.9;
            font-size: 1.1em;
        }}

        .role-block {{
            background: rgba(255, 255, 255, 0.7);
            border-left: 4px solid #42a5f5;
        }}

        .narrator-block {{
            background: rgba(255, 255, 255, 0.5);
            border-left: 4px solid #ab47bc;
        }}

        .role-tag {{
            display: inline-block;
            background: linear-gradient(135deg, #42a5f5, #7e57c2);
            color: white;
            padding: 2px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            margin-right: 8px;
            font-weight: bold;
        }}

        .reading-tips {{
            background: #fff8e1;
            border-radius: 8px;
            padding: 12px 18px;
            border: 1px solid #ffe082;
        }}

        .reading-tips p {{
            color: #f57f17;
            font-size: 0.95em;
        }}

        /* 生字卡/公式卡/单词卡/概念卡/价值观卡 通用网格 */
        .vocab-grid, .formula-grid, .word-grid, .concept-grid, .value-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 18px;
            padding: 20px 0;
        }}

        /* 生字卡样式 */
        .vocab-card, .formula-card, .word-card, .concept-card, .value-card {{
            background: linear-gradient(135deg, #42a5f5, #7e57c2);
            color: white;
            border-radius: 14px;
            padding: 18px 12px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            min-height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(100, 100, 200, 0.2);
            position: relative;
        }}

        .vocab-card:hover, .formula-card:hover, .word-card:hover, .concept-card:hover, .value-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(100, 100, 200, 0.3);
        }}

        .card-front {{
            transition: opacity 0.3s;
        }}

        /* 生字卡 */
        .card-char {{
            font-size: 2.8em;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}

        .card-pinyin {{
            font-size: 1.1em;
            margin-top: 6px;
            opacity: 0.9;
        }}

        /* 公式卡 */
        .formula-name {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 8px;
        }}

        .formula-expr {{
            font-size: 1.1em;
            font-family: 'Times New Roman', serif;
            font-style: italic;
            background: rgba(255,255,255,0.2);
            padding: 6px 10px;
            border-radius: 8px;
        }}

        .formula-example, .formula-note {{
            font-size: 0.85em;
            margin-bottom: 6px;
            line-height: 1.5;
        }}

        /* 单词卡 */
        .word-text {{
            font-size: 1.8em;
            font-weight: bold;
        }}

        .word-phonetic {{
            font-size: 0.9em;
            margin-top: 6px;
            opacity: 0.9;
            font-style: italic;
        }}

        .word-meaning, .word-sentence {{
            font-size: 0.85em;
            margin-bottom: 6px;
            line-height: 1.5;
        }}

        /* 概念卡 */
        .concept-term {{
            font-size: 1.3em;
            font-weight: bold;
        }}

        .concept-def, .concept-example {{
            font-size: 0.85em;
            margin-bottom: 6px;
            line-height: 1.5;
        }}

        /* 价值观卡 */
        .value-concept {{
            font-size: 1.4em;
            font-weight: bold;
        }}

        .value-quote {{
            font-size: 0.85em;
            font-style: italic;
            margin-bottom: 8px;
            line-height: 1.5;
        }}

        .value-story {{
            font-size: 0.8em;
            line-height: 1.5;
        }}

        .card-back {{
            display: none;
            font-size: 0.85em;
            line-height: 1.5;
        }}

        .card-meaning, .card-words {{
            margin-bottom: 6px;
        }}

        .vocab-tips {{
            background: #e8f5e9;
            border-radius: 8px;
            padding: 12px 18px;
            border: 1px solid #a5d6a7;
            margin-top: 10px;
        }}

        .vocab-tips p {{
            color: #2e7d32;
            font-size: 0.95em;
        }}

        /* 互动题目样式 */
        .interactive-question {{
            background: linear-gradient(135deg, #e8eaf6, #fce4ec);
            border-radius: 12px;
            padding: 20px;
            margin: 18px 0;
            border: 2px solid rgba(171, 71, 188, 0.2);
        }}

        .interactive-question h4 {{
            margin-bottom: 14px;
            color: #5c6bc0;
            font-size: 1.2em;
        }}

        .question-text {{
            font-size: 1.1em;
            margin-bottom: 18px;
            color: #424242;
        }}

        .options {{
            margin-bottom: 18px;
        }}

        .option {{
            margin-bottom: 10px;
            cursor: pointer;
            padding: 12px;
            border-radius: 8px;
            transition: background-color 0.3s;
            background: rgba(255,255,255,0.8);
            border: 1px solid rgba(171, 71, 188, 0.2);
        }}

        .option:hover {{
            background: rgba(232, 234, 246, 0.8);
        }}

        .option input {{
            margin-right: 10px;
        }}

        .hint-button, .answer-button {{
            border: none;
            padding: 10px 22px;
            border-radius: 20px;
            cursor: pointer;
            margin-right: 10px;
            margin-bottom: 10px;
            font-size: 0.95em;
            transition: all 0.3s;
        }}

        .hint-button {{
            background: linear-gradient(135deg, #42a5f5, #5c6bc0);
            color: white;
        }}

        .hint-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(66, 165, 245, 0.3);
        }}

        .answer-button {{
            background: linear-gradient(135deg, #66bb6a, #43a047);
            color: white;
        }}

        .answer-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
        }}

        .hint, .answer {{
            margin-top: 14px;
            padding: 14px;
            border-radius: 8px;
            display: none;
        }}

        .hint {{
            background: #e3f2fd;
            border: 1px solid #90caf9;
            color: #1565c0;
        }}

        .answer {{
            background: #e8f5e9;
            border: 1px solid #a5d6a7;
            color: #2e7d32;
        }}

        /* 进度条样式 */
        .progress-container {{
            margin: 22px 0;
        }}

        .progress-bar {{
            width: 100%;
            height: 24px;
            background-color: #e0e0e0;
            border-radius: 12px;
            overflow: hidden;
            border: 2px solid rgba(171, 71, 188, 0.2);
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #42a5f5, #7e57c2, #ab47bc);
            width: 0%;
            transition: width 0.5s ease;
            border-radius: 12px;
        }}

        #progress-text {{
            text-align: center;
            margin-top: 8px;
            color: #5c6bc0;
            font-weight: bold;
            font-size: 1em;
        }}

        /* 成就样式 */
        .achievement {{
            background: linear-gradient(135deg, #fff9c4, #fff59d);
            border-left: 5px solid #ffc107;
            padding: 16px;
            margin: 20px 0;
            display: none;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(255, 193, 7, 0.2);
        }}

        .achievement h3 {{
            color: #f57f17;
            margin-bottom: 8px;
        }}

        .achievement p {{
            color: #e65100;
        }}

        /* 点名转盘样式 */
        .lucky-wheel {{
            text-align: center;
            margin: 28px 0;
        }}

        .wheel-container {{
            position: relative;
            width: 300px;
            height: 300px;
            margin: 0 auto 20px;
        }}

        .wheel {{
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: conic-gradient(
                #42a5f5 0deg 18deg,
                #ab47bc 18deg 36deg,
                #66bb6a 36deg 54deg,
                #ffa726 54deg 72deg,
                #ef5350 72deg 90deg,
                #26c6da 90deg 108deg,
                #8d6e63 108deg 126deg,
                #78909c 126deg 144deg,
                #ec407a 144deg 162deg,
                #5c6bc0 162deg 180deg,
                #42a5f5 180deg 198deg,
                #ab47bc 198deg 216deg,
                #66bb6a 216deg 234deg,
                #ffa726 234deg 252deg,
                #ef5350 252deg 270deg,
                #26c6da 270deg 288deg,
                #8d6e63 288deg 306deg,
                #78909c 306deg 324deg,
                #ec407a 324deg 342deg,
                #5c6bc0 342deg 360deg
            );
            transition: transform 5s ease-out;
            border: 5px solid #7e57c2;
            box-shadow: 0 4px 15px rgba(126, 87, 194, 0.3);
        }}

        .wheel-pointer {{
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            width: 0;
            height: 0;
            border-left: 15px solid transparent;
            border-right: 15px solid transparent;
            border-top: 30px solid #7e57c2;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
        }}

        .wheel-btn {{
            background: linear-gradient(135deg, #42a5f5, #7e57c2);
            color: white;
            border: none;
            padding: 12px 28px;
            border-radius: 25px;
            cursor: pointer;
            margin: 0 8px;
            font-size: 1.05em;
            transition: all 0.3s;
            box-shadow: 0 4px 12px rgba(126, 87, 194, 0.3);
        }}

        .wheel-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(126, 87, 194, 0.4);
        }}

        .student-name {{
            font-size: 1.6em;
            font-weight: bold;
            background: linear-gradient(135deg, #42a5f5, #ab47bc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 20px 0;
        }}

        .sound-toggle {{
            text-align: center;
            margin: 18px 0;
        }}

        .sound-toggle button {{
            background: linear-gradient(135deg, #42a5f5, #7e57c2);
            color: white;
            border: none;
            padding: 10px 22px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 3px 10px rgba(126, 87, 194, 0.2);
        }}

        .sound-toggle button:hover {{
            transform: translateY(-2px);
        }}

        .fun-fact {{
            background: rgba(255, 255, 255, 0.7);
            border-left: 5px solid #ab47bc;
            padding: 14px;
            margin: 16px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(171, 71, 188, 0.1);
        }}

        .fun-fact h4 {{
            margin-top: 0;
            color: #7e57c2;
        }}

        .extra-resources {{
            background: rgba(255, 255, 255, 0.7);
            border-left: 5px solid #42a5f5;
            padding: 14px;
            margin: 16px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(66, 165, 245, 0.1);
        }}

        .extra-resources h4 {{
            margin-top: 0;
            color: #1565c0;
        }}

        .extra-resources ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}

        .extra-resources li {{
            margin-bottom: 8px;
            color: #424242;
        }}

        /* 知识点卡片 */
        .knowledge-point {{
            background: rgba(255, 255, 255, 0.6);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 18px;
            border: 1px solid rgba(171, 71, 188, 0.1);
        }}

        @media screen and (max-width: 768px) {{
            h1 {{
                font-size: 2em;
            }}
            .section {{
                padding: 18px;
            }}
            .wheel-container {{
                width: 250px;
                height: 250px;
            }}
            .vocab-grid, .formula-grid, .word-grid, .concept-grid, .value-grid {{
                grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                gap: 12px;
            }}
            .card-char {{
                font-size: 2.2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌟 {title_prefix}</h1>
        <div class="subtitle">{subtitle}</div>

        <div class="sound-toggle">
            <button id="sound-btn">🔊 音效开关</button>
        </div>

        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" id="progress-fill"></div>
            </div>
            <p id="progress-text">学习进度：0%</p>
        </div>

        <div class="achievement" id="achievement">
            <h3>🎉 太棒了！解锁新成就！</h3>
            <p>你已经完成了半数知识点的学习，继续加油！</p>
        </div>

{intro_html}
{reading_html}
{cards_html}
{knowledge_html}
{fun_facts_html}
{extra_html}

        <!-- 互动区：课堂点名转盘 -->
        <div class="section">
            <h2>🎡 课堂互动：幸运点名转盘</h2>
            <div class="lucky-wheel">
                <div class="wheel-container">
                    <div class="wheel" id="wheel"></div>
                    <div class="wheel-pointer"></div>
                </div>
                <button class="wheel-btn" onclick="spinWheel()">🎯 开始点名</button>
                <button class="wheel-btn" onclick="spinWheel()">🔄 再抽一次</button>
                <div class="student-name" id="student-name"></div>
                <button class="wheel-btn" onclick="assignQuestion()">📝 为TA出题</button>
            </div>
        </div>

        <!-- 总结区 -->
        <div class="section">
            <h2>📝 课堂总结</h2>
            <div class="story-content">
                <p>{summary}</p>
            </div>
        </div>
    </div>

    <script>
        // 学生名单
        const students = {json.dumps(student_list, ensure_ascii=False)};

        // 进度跟踪
        let progress = 0;
        const totalQuestions = {total_questions};

        // 显示提示
        function showHint(hintId) {{
            const hint = document.getElementById(hintId);
            hint.style.display = 'block';
        }}

        // 显示答案
        function showAnswer(answerId) {{
            const answer = document.getElementById(answerId);
            answer.style.display = 'block';
            // 更新进度
            if (totalQuestions > 0) {{
                updateProgress(Math.round(100 / totalQuestions));
            }}
        }}

        // 翻转卡片
        function flipCard(card, backId) {{
            const front = card.querySelector('.card-front');
            const back = card.querySelector('.card-back');
            if (front.style.display === 'none') {{
                front.style.display = 'block';
                back.style.display = 'none';
            }} else {{
                front.style.display = 'none';
                back.style.display = 'block';
            }}
        }}

        // 更新进度
        function updateProgress(amount) {{
            progress += amount;
            if (progress > 100) progress = 100;
            const progressFill = document.getElementById('progress-fill');
            const progressText = document.getElementById('progress-text');
            progressFill.style.width = progress + '%';
            progressText.textContent = '学习进度：' + progress + '%';

            // 成就提示
            if (progress >= 25 && progress < 50) {{
                const ach = document.getElementById('achievement');
                ach.style.display = 'block';
                ach.querySelector('p').textContent = '你已经迈出了学习的第一步，继续保持！🌟';
            }} else if (progress >= 50 && progress < 75) {{
                const ach = document.getElementById('achievement');
                ach.style.display = 'block';
                ach.querySelector('p').textContent = '你已经完成了半数知识点的学习，继续加油！💪';
            }} else if (progress >= 100) {{
                const ach = document.getElementById('achievement');
                ach.style.display = 'block';
                ach.querySelector('h3').textContent = '🏆 恭喜！全部完成！';
                ach.querySelector('p').textContent = '你是真正的学习小达人！所有知识点都学完啦！🎉';
            }}
        }}

        // 幸运点名转盘
        function spinWheel() {{
            const wheel = document.getElementById('wheel');
            const studentName = document.getElementById('student-name');
            const randomIndex = Math.floor(Math.random() * students.length);
            const selectedStudent = students[randomIndex];

            const rotation = 3600 + randomIndex * (360 / students.length);
            wheel.style.transform = 'rotate(' + rotation + 'deg)';

            setTimeout(() => {{
                studentName.textContent = '🎉 恭喜：' + selectedStudent;
            }}, 5000);
        }}

        // 为学生出题
        function assignQuestion() {{
            const studentName = document.getElementById('student-name').textContent;
            if (studentName) {{
                alert(studentName + '，请回答：请说说今天学的主要内容是什么？你从中学到了什么？');
            }} else {{
                alert('请先点击"开始点名"，选择一名同学！');
            }}
        }}

        // 音效开关
        let soundEnabled = false;
        const soundBtn = document.getElementById('sound-btn');

        soundBtn.addEventListener('click', () => {{
            soundEnabled = !soundEnabled;
            soundBtn.textContent = soundEnabled ? '🔊 音效：开启' : '🔇 音效：关闭';
        }});
    </script>
</body>
</html>
'''

    return html


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成小学全科交互式学习网页')
    parser.add_argument('--json-file', required=True, help='JSON数据文件路径')
    parser.add_argument('--output', required=True, help='输出HTML文件路径')
    parser.add_argument('--subject', required=True,
                        choices=['chinese', 'math', 'english', 'science', 'morality'],
                        help='科目：chinese(语文) math(数学) english(英语) science(科学) morality(道法)')
    parser.add_argument('--students', help='学生名单（JSON数组字符串）', default=None)

    args = parser.parse_args()

    # 读取JSON文件
    try:
        with open(args.json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到JSON文件 {args.json_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误：JSON文件解析失败 - {e}", file=sys.stderr)
        sys.exit(1)

    # 解析学生名单
    student_list = None
    if args.students:
        try:
            student_list = json.loads(args.students)
        except json.JSONDecodeError:
            print("警告：学生名单格式错误，使用默认名单", file=sys.stderr)

    # 生成HTML
    html_content = generate_html(json_data, args.subject, student_list)

    # 写入输出文件
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html_content)

    subject_names = {'chinese': '语文', 'math': '数学', 'english': '英语', 'science': '科学', 'morality': '道法'}
    print(f"✅ 成功：{subject_names.get(args.subject, '')}交互式学习网页已生成到 {args.output}")


if __name__ == '__main__':
    main()
