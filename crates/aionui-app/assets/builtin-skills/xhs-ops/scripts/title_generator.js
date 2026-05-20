#!/usr/bin/env node
/**
 * 小红书爆款标题生成器 v2.0（AI驱动）
 * 用法: node title_generator.js --topic "选题" [--count 8] [--audience "目标受众"]
 */

const { generateTitles } = require('../llm_client');

// CLI
const args = process.argv.slice(2);
if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
  console.log('用法:');
  console.log('  node title_generator.js --topic "选题"        # 生成爆款标题（AI驱动）');
  console.log('  node title_generator.js --topic "选题" --count 12  # 指定数量');
  console.log('  node title_generator.js --topic "选题" --audience "上班族"  # 指定目标受众');
  process.exit(0);
}

const topicIdx = args.indexOf('--topic');
if (topicIdx === -1 || !args[topicIdx + 1]) {
  console.error('❌ 请指定 --topic 参数，用法: node title_generator.js --topic "选题"');
  process.exit(1);
}

const topic = args[topicIdx + 1];
const countIdx = args.indexOf('--count');
const audienceIdx = args.indexOf('--audience');
const audience = audienceIdx !== -1 && args[audienceIdx + 1] ? args[audienceIdx + 1] : null;

console.log(`\n🎯 选题: ${topic}${audience ? ` | 目标受众: ${audience}` : ''}`);
console.log('═'.repeat(50));
console.log('\n🤖 AI 生成中...\n');

generateTitles(topic, audience)
  .then(result => {
    console.log(result);
    console.log('\n' + '═'.repeat(50));
    console.log('\n💡 使用建议:');
    console.log('1. 选择2-3个不同情绪类型的标题做A/B测试');
    console.log('2. 封面图风格要与标题调性一致');
    console.log('3. 同一选题可以多次生成，每次结果会不同');
  })
  .catch(err => {
    console.error('❌ 生成失败:', err.message);
    process.exit(1);
  });