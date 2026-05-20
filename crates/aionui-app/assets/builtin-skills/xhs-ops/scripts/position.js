#!/usr/bin/env node
/**
 * 小红书账号定位模块
 * 帮助新人确定账号定位、昵称方向、简介框架、视觉风格
 * 用法: node position.js --topic "美妆" [--audience "年轻女生"] [--features "爱折腾"]
 */

const { positionBlogger } = require('../llm_client');

// CLI
const args = process.argv.slice(2);

if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
  console.log(`用法:`);
  console.log(`  node position.js --topic "美妆"`);
  console.log(`  node position.js --topic "穿搭" --audience "学生党" --features "平价爱好者"`);
  console.log(`\n参数说明:`);
  console.log(`  --topic     内容方向: 美妆/穿搭/美食/护肤/家居等`);
  console.log(`  --audience  (可选) 目标用户群体`);
  console.log(`  --features  (可选) 个人特点或优势`);
  process.exit(0);
}

const topicIdx = args.indexOf('--topic');
const audienceIdx = args.indexOf('--audience');
const featuresIdx = args.indexOf('--features');

if (topicIdx === -1 || !args[topicIdx + 1]) {
  console.error('❌ 请指定 --topic 参数（内容方向）');
  console.log('示例: node position.js --topic "美妆"');
  process.exit(1);
}

const topic = args[topicIdx + 1];
const audience = audienceIdx !== -1 ? args[audienceIdx + 1] : null;
const features = featuresIdx !== -1 ? args[featuresIdx + 1] : null;

console.log(`\n🎯 账号定位分析中...`);
console.log(`📍 方向: ${topic} ${audience ? `| 用户: ${audience}` : ''} ${features ? `| 特点: ${features}` : ''}`);
console.log('─'.repeat(50));

positionBlogger(topic, audience, features)
  .then(result => {
    console.log('\n' + result + '\n');
  })
  .catch(err => {
    console.error('❌ 定位失败:', err.message);
    process.exit(1);
  });
