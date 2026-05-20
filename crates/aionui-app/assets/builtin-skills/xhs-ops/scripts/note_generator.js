#!/usr/bin/env node
/**
 * 小红书笔记正文生成器 v2.0（AI驱动）
 * 根据选题和标题生成完整笔记正文
 * 用法: node note_generator.js --title "标题" --topic "选题" [--style 种草|教程|日常|测评|合集]
 */

const { generateNote } = require('../llm_client');

const NOTE_STYLES = {
  '种草': { name: '种草型', desc: '真实体验分享，突出使用效果' },
  '教程': { name: '教程型', desc: '步骤清晰，干货满满，适合收藏' },
  '日常': { name: '日常分享型', desc: '生活化叙事，有代入感' },
  '测评': { name: '测评对比型', desc: '客观分析优缺点，帮助决策' },
  '合集': { name: '合集整理型', desc: '信息密度高，实用性强' }
};

// CLI
const args = process.argv.slice(2);

if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
  console.log(`用法:`);
  console.log(`  node note_generator.js --title "标题" --topic "选题" [--style 种草]`);
  console.log(`\n支持的风格:`);
  Object.entries(NOTE_STYLES).forEach(([key, val]) => {
    console.log(`  ${key} - ${val.name}: ${val.desc}`);
  });
  process.exit(0);
}

const titleIdx = args.indexOf('--title');
const topicIdx = args.indexOf('--topic');
const styleIdx = args.indexOf('--style');

if (titleIdx === -1 || !args[titleIdx + 1]) {
  console.error('❌ 请指定 --title 参数');
  process.exit(1);
}
if (topicIdx === -1 || !args[topicIdx + 1]) {
  console.error('❌ 请指定 --topic 参数');
  process.exit(1);
}

const title = args[titleIdx + 1];
const topic = args[topicIdx + 1];
const style = styleIdx !== -1 && args[styleIdx + 1] ? args[styleIdx + 1] : '种草';

if (!NOTE_STYLES[style]) {
  console.error(`❌ 不支持的风格 "${style}"，可用: ${Object.keys(NOTE_STYLES).join(', ')}`);
  process.exit(1);
}

console.log(`\n📝 标题: ${title}`);
console.log(`🎯 选题: ${topic}`);
console.log(`🎨 风格: ${NOTE_STYLES[style].name}`);
console.log('═'.repeat(50));
console.log('\n🤖 AI 生成中...\n');

generateNote(title, topic, style)
  .then(result => {
    console.log(result);
    console.log('\n' + '═'.repeat(50));
    console.log('\n💡 使用建议:');
    console.log('1. 根据实际体验调整内容细节');
    console.log('2. 添加真实的个人感受更容易爆');
    console.log('3. 封面图和标题要跟正文调性一致');
  })
  .catch(err => {
    console.error('❌ 生成失败:', err.message);
    process.exit(1);
  });