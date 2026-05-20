#!/usr/bin/env node
/**
 * 小红书博主诊断模块
 * 诊断博主当前阶段，给出运营建议
 * 用法: node diagnose.js --stage "刚起号" --topic "美妆" [--fans 500] [--conf "不知道发什么"]
 */

const { diagnoseBlogger } = require('../llm_client');

// CLI
const args = process.argv.slice(2);

if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
  console.log(`用法:`);
  console.log(`  node diagnose.js --stage "刚起号" --topic "美妆"`);
  console.log(`  node diagnose.js --stage "成长期" --topic "穿搭" --fans 2000`);
  console.log(`  node diagnose.js --stage "刚起号" --topic "美食" --conf "不知道发什么"`);
  console.log(`\n参数说明:`);
  console.log(`  --stage   账号阶段: 刚起号/冷启动/成长期/变现阶段/瓶颈期`);
  console.log(`  --topic   内容方向: 美妆/穿搭/美食/护肤/家居等`);
  console.log(`  --fans    (可选) 当前粉丝数`);
  console.log(`  --conf    (可选) 当前最大的困惑或问题`);
  process.exit(0);
}

const stageIdx = args.indexOf('--stage');
const topicIdx = args.indexOf('--topic');
const fansIdx = args.indexOf('--fans');
const confIdx = args.indexOf('--conf');

if (stageIdx === -1 || !args[stageIdx + 1]) {
  console.error('❌ 请指定 --stage 参数（账号阶段）');
  console.log('示例: node diagnose.js --stage "刚起号" --topic "美妆"');
  process.exit(1);
}
if (topicIdx === -1 || !args[topicIdx + 1]) {
  console.error('❌ 请指定 --topic 参数（内容方向）');
  console.log('示例: node diagnose.js --stage "刚起号" --topic "美妆"');
  process.exit(1);
}

const stage = args[stageIdx + 1];
const topic = args[topicIdx + 1];
const fans = fansIdx !== -1 && args[fansIdx + 1] ? args[fansIdx + 1] : null;
const conf = confIdx !== -1 ? args[confIdx + 1] : null;

console.log(`\n🔍 博主诊断中...`);
console.log(`📍 阶段: ${stage} | 方向: ${topic} ${fans ? `| 粉丝: ${fans}` : ''}`);
console.log('─'.repeat(50));

diagnoseBlogger(stage, topic, fans, conf)
  .then(result => {
    console.log('\n' + result + '\n');
  })
  .catch(err => {
    console.error('❌ 诊断失败:', err.message);
    process.exit(1);
  });