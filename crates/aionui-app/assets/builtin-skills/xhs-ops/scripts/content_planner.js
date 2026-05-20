#!/usr/bin/env node
/**
 * 小红书内容规划器
 * 根据账号定位和资源情况，生成内容日历和发布计划
 * 
 * 用法:
 *   node content_planner.js --name "账号名" --directions "种草,教程,日常" --weekly 5
 *   node content_planner.js --interactive
 */

const READLINE = require('readline');

function rl() {
  return READLINE.createInterface({ input: process.stdin, output: process.stdout });
}

function ask(question) {
  return new Promise((resolve) => {
    const i = rl();
    i.question(question, (answer) => {
      i.close();
      resolve(answer);
    });
  });
}

const CONTENT_TYPES = {
  种草: { emoji: '🛒', desc: '好物推荐/产品测评', frequency: '每周1篇', slot: '周二/周五' },
  教程: { emoji: '📖', desc: '步骤攻略/方法论', frequency: '每周1篇', slot: '周三/周六' },
  日常: { emoji: '📸', desc: '人设塑造/生活分享', frequency: '每两周1篇', slot: '周日' },
  合集: { emoji: '📋', desc: '清单整理/Top排行', frequency: '每月1篇', slot: '月末' },
  热点: { emoji: '🔥', desc: '蹭热点/节日节点', frequency: '按需', slot: '热点发生时' },
  测评: { emoji: '🔬', desc: '对比测评/长期跟踪', frequency: '每月1-2篇', slot: '月初/月中' },
};

const TIME_SLOTS = {
  '7:30-8:30': { name: '通勤', best: '干货教程、种草' },
  '12:00-13:00': { name: '午休', best: '快节奏内容' },
  '18:00-19:00': { name: '下班', best: '生活方式、日常' },
  '21:00-22:00': { name: '睡前', best: '深度内容、种草' },
};

function generateCalendar(name, directions, weeklyPosts, weeks = 4) {
  console.log(`\n📅 ${name} 内容日历（${weeks}周）\n`);
  console.log('═'.repeat(50));

  const posts = [];
  const directionList = directions.split(',').map(d => d.trim());
  
  // 周计划
  const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
  
  // 按周生成
  for (let w = 1; w <= weeks; w++) {
    console.log(`\n📆 第${w}周`);
    console.log('-'.repeat(30));
    
    let postCount = 0;
    const dayIndex = (w - 1) * 7;
    
    for (let d = 0; d < 7; d++) {
      if (postCount >= weeklyPosts) break;
      
      const dayName = days[d];
      const slot = Object.keys(TIME_SLOTS)[Math.floor(Math.random() * 4)];
      const typeIndex = postCount % directionList.length;
      const contentType = directionList[typeIndex];
      const typeInfo = CONTENT_TYPES[contentType] || CONTENT_TYPES.种草;
      
      const suggestions = {
        种草: ['XX好物真实测评', '均价50的XX清单', 'XX踩坑分享'],
        教程: ['XX步搞定XX教程', '新手入门指南', 'XX常见误区'],
        日常: ['我的XX体验', '今日穿搭分享', '周末日常vlog'],
        合集: ['Top10 XX清单', 'XX合集推荐', '必买XX列表'],
        热点: ['XX热点怎么看', '蹭热点XX话题', 'XX节日指南'],
        测评: ['XX对比测评', 'XX长期使用报告', 'XX真实体验'],
      };
      
      const suggestion = suggestions[contentType][Math.floor(Math.random() * 3)];
      
      console.log(`${dayName.padEnd(4)} ${slot.padEnd(14)} ${typeInfo.emoji} ${contentType.padEnd(4)} | ${suggestion}`);
      
      posts.push({ week: w, day: dayName, slot, type: contentType, suggestion });
      postCount++;
    }
  }

  console.log('\n' + '═'.repeat(50));
  console.log('\n📊 资源配置建议');
  console.log(`每周发布：${weeklyPosts}篇`);
  console.log('内容方向配比：');
  directionList.forEach(d => {
    const info = CONTENT_TYPES[d] || CONTENT_TYPES.种草;
    console.log(`  ${info.emoji} ${d}: ${info.frequency}（${info.slot}）`);
  });

  console.log('\n⏰ 发布时间推荐');
  Object.entries(TIME_SLOTS).forEach(([slot, info]) => {
    console.log(`  ${slot}（${info.name}）：${info.best}`);
  });

  console.log('\n💡 优化建议');
  if (weeklyPosts >= 5) {
    console.log('  ✓ 保持更新节奏，爆款+稳定内容组合');
  } else if (weeklyPosts >= 3) {
    console.log('  ✓ 聚焦核心内容方向，避免精力分散');
  } else {
    console.log('  ✓ 起步期建议至少每周3篇，测试内容方向');
  }
  console.log('  ✓ 爆款笔记出现后，同形式快速复制1-2篇');
  console.log('  ✓ 每月底做数据复盘，优化次月内容配比');
  console.log('');
}

async function interactive() {
  console.log('\n🎯 小红书内容规划器（交互模式）\n');
  
  const name = await ask('账号名称（或定位关键词）: ') || '我的账号';
  const directions = await ask('内容方向（用逗号分隔，如：种草,教程,日常）: ') || '种草,教程';
  const weeklyRaw = await ask('每周计划发布几篇？: ') || '3';
  const weeklyPosts = parseInt(weeklyRaw) || 3;
  const weeksRaw = await ask('规划几周？（默认4周）: ') || '4';
  const weeks = parseInt(weeksRaw) || 4;
  
  generateCalendar(name, directions, weeklyPosts, weeks);
}

// CLI
const args = process.argv.slice(2);
if (args.includes('--interactive') || args.includes('-i')) {
  interactive().catch(console.error);
} else if (args.includes('--help') || args.includes('-h')) {
  console.log('用法:');
  console.log('  node content_planner.js --interactive                # 交互式规划');
  console.log('  node content_planner.js --name "穿搭号" --directions "种草,教程" --weekly 5');
  console.log('');
  console.log('参数:');
  console.log('  --name        账号名称');
  console.log('  --directions  内容方向（逗号分隔）');
  console.log('  --weekly      每周篇数（默认3）');
  console.log('  --weeks       规划周数（默认4）');
  process.exit(0);
} else {
  // 解析参数
  const nameIdx = args.indexOf('--name');
  const dirIdx = args.indexOf('--directions');
  const weeklyIdx = args.indexOf('--weekly');
  const weeksIdx = args.indexOf('--weeks');
  
  const name = nameIdx !== -1 && args[nameIdx + 1] ? args[nameIdx + 1] : '我的账号';
  const directions = dirIdx !== -1 && args[dirIdx + 1] ? args[dirIdx + 1] : '种草,教程';
  const weeklyRaw = weeklyIdx !== -1 && args[weeklyIdx + 1] ? parseInt(args[weeklyIdx + 1]) : 3;
  const weeklyPosts = isNaN(weeklyRaw) || weeklyRaw < 1 ? 3 : weeklyRaw;
  const weeksRaw = weeksIdx !== -1 && args[weeksIdx + 1] ? parseInt(args[weeksIdx + 1]) : 4;
  const weeks = isNaN(weeksRaw) || weeksRaw < 1 ? 4 : weeksRaw;
  
  generateCalendar(name, directions, weeklyPosts, weeks);
}
