#!/usr/bin/env node
/**
 * 小红书选题研究脚本 v2.0
 * 用法: node topic_research.js --topic "选题" / --keyword "关键词" / --hot / --competitor "竞品名"
 * 搜索结果自动翻译为中文
 */

const https = require('https');
const http = require('http');
const { URL } = require('url');
const { translateToChinese } = require('../llm_client');

// 演示数据（无API Key时返回）
const DEMO_DATA = {
  hot: [
    { topic: '春季穿搭', heat: 98, trend: '↑', notes: '季节性强，提前布局', categories: ['穿搭', '时尚'] },
    { topic: '减脂餐食谱', heat: 95, trend: '↑', notes: '高收藏率，长期需求', categories: ['美食', '健康'] },
    { topic: '早C晚A护肤', heat: 92, trend: '→', notes: '稳定需求，可做系列', categories: ['护肤', '美妆'] },
    { topic: '露营装备清单', heat: 88, trend: '↑', notes: '假期前热度上升', categories: ['户外', '旅行'] },
    { topic: '职场通勤穿搭', heat: 85, trend: '→', notes: '稳定流量，长尾需求', categories: ['穿搭', '职场'] },
    { topic: '618好物推荐', heat: 83, trend: '↑', notes: '大促前种草需求爆发', categories: ['好物', '种草'] },
    { topic: '新手健身计划', heat: 80, trend: '↑', notes: '新年/春季flag高发期', categories: ['健身', '健康'] },
    { topic: '618攻略大全', heat: 78, trend: '↑', notes: '大促节点，高实用价值', categories: ['攻略', '省钱'] },
    { topic: '租房改造日记', heat: 75, trend: '→', notes: '毕业生/打工人大需求', categories: ['家居', '日常'] },
    { topic: '副业赚钱分享', heat: 73, trend: '↑', notes: '经济压力下关注度高', categories: ['职场', '理财'] },
    { topic: '父母体检指南', heat: 70, trend: '↑', notes: '银发经济，关注度上升', categories: ['健康', '家庭'] },
    { topic: '宠物用品测评', heat: 68, trend: '→', notes: '年轻人养宠率高且愿意消费', categories: ['宠物', '测评'] },
  ],
  keyword: [
    { title: 'XX真的好用吗？3个月真实测评', score: 92, type: '测评', reason: '解决选择困难' },
    { title: '手把手教你XX，从入门到精通', score: 88, type: '教程', reason: '高收藏需求' },
    { title: 'XX合集｜这10件值得买', score: 85, type: '种草', reason: '高实用性' },
    { title: 'XX踩坑总结｜新手必看', score: 82, type: '避坑', reason: '减少决策风险' },
    { title: '日常｜我的XX体验', score: 78, type: '日常', reason: '人设塑造' },
    { title: 'XX天打卡｜第X天变化', score: 76, type: '打卡', reason: '真实感强，算法偏爱' },
    { title: '均价50的XX清单｜附链接', score: 74, type: '种草', reason: '价格锚点明确，实用性强' },
    { title: '为什么我不推荐XX', score: 72, type: '避坑', reason: '反差感强，评论率高' },
    { title: 'XX VS XX｜真实对比', score: 70, type: '测评', reason: '解决选择焦虑' },
    { title: 'XX之后我变了｜真实故事', score: 68, type: '日常', reason: '情感共鸣强，人设加分' },
  ]
};

// 本地选题生成器（无需API，按类别+场景+时机生成选题思路）
const TOPIC_TEMPLATES = {
  穿搭: [
    '小个子显高穿搭公式', '梨形身材遮胯穿搭', '黄皮显白颜色搭配', '职场通勤穿搭灵感',
    '一周不重样穿搭', '平价替代大牌穿搭', '换季衣橱整理术', '微胖女生显瘦穿搭',
  ],
  美妆: [
    '早C晚A真实测评', '新手化妆保姆教程', '平价好物真实测评', '618/双11好物清单',
    '素颜霜/气垫/粉底液对比', '年度爱用物总结', '换季护肤routine', '早八人快速妆容',
  ],
  美食: [
    '打工人快手早餐', '减脂餐食谱合集', '周末早午餐Brunch', '一人食食谱推荐',
    '宿舍做饭日记', '空气炸锅食谱大全', '咖啡/奶茶店平替', '618零食种草清单',
  ],
  护肤: [
    '油皮/干皮护肤步骤', '刷酸新手教程', '抗老精华真实测评', '平价替代大牌护肤',
    '春季过敏急救指南', '身体乳/颈霜推荐', '618护肤囤货攻略', '精简护肤心得',
  ],
  家居: [
    '租房改造前后对比', '小户型收纳技巧', '出租屋好物清单', '氛围感布置灵感',
    '独居女孩好物分享', '厨房收纳整理', '618家居好物种草', '租房避坑指南',
  ],
  职场: [
    '打工人通勤包里有什么', '职场穿搭灵感', '涨薪/晋升经验分享', '简历优化技巧',
    '远程办公好物', '副业探索记录', '职场沟通技巧', '新人入职指南',
  ],
  健康: [
    '帕梅拉/刘畊宏打卡', '减脂打卡记录', '体态改善计划', '中医养生小妙招',
    '年度体检攻略', '失眠/焦虑缓解', '上班族肩颈改善', '养生茶饮食谱',
  ],
  旅行: [
    '周末短途游攻略', '小长假出行清单', '露营装备推荐', '一个人旅行体验',
    '城市探店vlog', '省钱穷游攻略', '出境游准备事项', '家乡旅游打卡',
  ],
  数码: [
    'iPad/平板使用技巧', '蓝牙耳机测评', '618数码好物推荐', '桌面布置灵感',
    '自媒体工具分享', '学习/生产力App推荐', '苹果全家桶使用体验', '平价替代方案',
  ],
  理财: [
    '攒钱/存钱方法', '记账复盘记录', '保险配置思路', '副业收入分享',
    '基金/股票学习', '极简生活开销', '理性消费心得', '强制储蓄计划',
  ],
};

const SEASONAL_TOPICS = {
  '1月': ['新年flag制定', '年度总结分享', '元旦好物清单', '春节囤货指南'],
  '2月': ['情人节礼物', '春节假期vlog', '节后快速收心', '春季换季护肤'],
  '3月': ['春季穿搭上新', '妇女节礼物推荐', '春季护肤重点', '315消费者维权'],
  '4月': ['清明小长假攻略', '春季穿搭灵感', '春季护肤好物', '踏青/露营准备'],
  '5月': ['五一小长假出行', '母亲节礼物', '520送礼指南', '夏季穿搭预备'],
  '6月': ['618好物推荐', '儿童节/父亲节', '夏季护肤指南', '毕业季求职'],
  '7月': ['暑假出行攻略', '夏季穿搭分享', '618战利品展示', '高温避暑指南'],
  '8月': ['夏末穿搭灵感', '开学季好物', '七夕礼物攻略', '夏季瘦身总结'],
  '9月': ['秋季穿搭上新', '教师节礼物', '中秋节vlog', '换季衣橱整理'],
  '10月': ['十一出行攻略', '秋季护肤好物', '双十一预告', '重阳节登高'],
  '11月': ['双十一好物种草', '冬季穿搭预备', '感恩节vlog', '年终复盘准备'],
  '12月': ['圣诞礼物清单', '年度爱用物总结', '跨年vlog', '双十二收尾'],
};

const OPPORTUNISTIC_TOPICS = {
  大促: ['618/双十一好物清单', '大促攻略大全', '李佳琦直播间种草', '理性囤货清单'],
  热点: ['蹭热点XX话题', '热点事件看法', '热点相关XX测评', '热点角度分析'],
  节点: ['节假日XX攻略', '节前XX准备', '节后XX收心', 'XX节日特别企划'],
};

function generateLocalTopics(category, count = 10) {
  const results = [];
  const month = new Date().toLocaleString('zh-CN', { month: 'long' });
  const seasonTopics = SEASONAL_TOPICS[month] || SEASONAL_TOPICS['3月'];
  
  // 分类选题
  const catTopics = TOPIC_TEMPLATES[category] || TOPIC_TEMPLATES['穿搭'];
  for (const t of catTopics.slice(0, 6)) {
    results.push({ topic: t, source: `【${category}】常规选题`, applicability: '全年可用' });
  }
  
  // 季节性选题
  for (const t of seasonTopics.slice(0, 4)) {
    results.push({ topic: t, source: '【当月季节】选题', applicability: month });
  }
  
  // 蹭热点选题
  const opTopics = OPPORTUNISTIC_TOPICS['大促'].slice(0, 2);
  for (const t of opTopics) {
    results.push({ topic: t, source: '【蹭节点】选题', applicability: '大促期间爆发' });
  }
  
  return results.slice(0, count);
}

function searchBrave(query, count = 10) {
  return new Promise((resolve) => {
    const apiKey = process.env.BRAVE_SEARCH_KEY;
    if (!apiKey) {
      console.log('（无 BRAVE_SEARCH_KEY，返回演示数据）\n');
      resolve(null);
      return;
    }

    const url = new URL('https://api.search.brave.com/res/v1/web/search');
    url.searchParams.set('q', query);
    url.searchParams.set('count', count);

    const options = {
      headers: {
        'Accept': 'application/json',
        'X-Subscription-Token': apiKey
      }
    };

    https.get(url.toString(), options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(null);
        }
      });
    }).on('error', () => resolve(null));
  });
}

async function topicResearch(topic) {
  console.log(`\n🔍 选题研究: ${topic}\n`);
  console.log('─'.repeat(50));

  const braveResults = await searchBrave(`${topic} 小红书`);
  if (!braveResults) {
    console.log('\n📊 本地选题生成（无 API Key，自动启用本地生成器）\n');
    
    // 自动识别最相关的分类
    const allCategories = Object.keys(TOPIC_TEMPLATES);
    const matched = allCategories.filter(c => c.includes(topic) || topic.includes(c));
    const primaryCategory = matched[0] || allCategories[Math.floor(Math.random() * allCategories.length)];
    
    console.log(`🎯 自动识别方向: ${primaryCategory}\n`);
    const localTopics = generateLocalTopics(primaryCategory, 10);
    localTopics.forEach((item, i) => {
      console.log(`${i + 1}. ${item.topic}`);
      console.log(`   来源: ${item.source} | 适用: ${item.applicability}`);
    });
    
    console.log('\n💡 使用建议: 选2-3个感兴趣的方向，生成标题后直接写稿');
    console.log('🔑 获取实时数据: 设置环境变量 BRAVE_SEARCH_KEY（免费额度足够用）');
    return;
  }

  const webResults = braveResults.web?.results || [];
  console.log(`\n🌐 找到 ${webResults.length} 条相关内容\n`);

  for (let i = 0; i < Math.min(webResults.length, 8); i++) {
    const result = webResults[i];
    const title = await translateToChinese(result.title || '');
    console.log(`${i + 1}. ${title}`);
    console.log(`   ${result.url}`);
    console.log('');
  }
}

async function keywordResearch(keyword, count = 10) {
  console.log(`\n🔍 关键词研究: ${keyword}\n`);
  console.log('─'.repeat(50));

  const braveResults = await searchBrave(`${keyword} 小红书选题`);
  if (!braveResults) {
    console.log('\n📊 本地选题生成（无 API Key，自动启用本地生成器）\n');
    
    const allCategories = Object.keys(TOPIC_TEMPLATES);
    const matched = allCategories.filter(c => c.includes(keyword) || keyword.includes(c));
    const primaryCategory = matched[0] || allCategories[Math.floor(Math.random() * allCategories.length)];
    
    console.log(`🎯 识别内容方向: ${primaryCategory}\n`);
    DEMO_DATA.keyword.slice(0, count).forEach((item, i) => {
      console.log(`${i + 1}. ${item.title.replace('XX', keyword)}`);
      console.log(`   类型: ${item.type} | 得分: ${item.score} | ${item.reason}`);
    });
    
    console.log('\n💡 本地选题推荐:');
    const local = generateLocalTopics(primaryCategory, 5);
    local.forEach((item, i) => {
      console.log(`   ${i + 1}. ${item.topic}`);
    });
    console.log('\n🔑 获取实时数据: 设置环境变量 BRAVE_SEARCH_KEY');
    return;
  }

  const webResults = braveResults.web?.results || [];
  for (let i = 0; i < Math.min(webResults.length, count); i++) {
    const result = webResults[i];
    const title = await translateToChinese(result.title || '');
    console.log(`${i + 1}. ${title}`);
    console.log(`   ${result.url}\n`);
  }
}

async function hotTopics(count = 20) {
  console.log('\n🔥 小红书热点话题\n');
  console.log('─'.repeat(50));

  const braveResults = await searchBrave('小红书 热门话题 今日');
  if (!braveResults) {
    console.log('\n📊 本地热点库（无 API Key，基于分类知识库生成）\n');
    DEMO_DATA.hot.slice(0, count).forEach((item, i) => {
      console.log(`${i + 1}. ${item.topic} ${item.trend} (热度: ${item.heat})`);
      console.log(`   ${item.notes} | 分类: ${(item.categories || []).join(', ')}`);
    });
    
    console.log('\n📌 当月热点选题推荐:');
    const monthNum = new Date().getMonth() + 1; // 1-12
    const monthKey = `${monthNum}月`;
    const seasonal = SEASONAL_TOPICS[monthKey] || [];
    seasonal.forEach((t, i) => console.log(`   ${i + 1}. ${t}`));
    
    console.log('\n💡 使用方法: 选感兴趣的热点 → 配合标题生成器产出具体方案');
    console.log('🔑 获取实时数据: 设置环境变量 BRAVE_SEARCH_KEY');
    return;
  }

  const webResults = braveResults.web?.results || [];
  for (let i = 0; i < Math.min(webResults.length, count); i++) {
    const result = webResults[i];
    const title = await translateToChinese(result.title || '');
    console.log(`${i + 1}. ${title}`);
  }
}

async function competitorAnalysis(competitor) {
  console.log(`\n👀 竞品分析: ${competitor}\n`);
  console.log('─'.repeat(50));

  const braveResults = await searchBrave(`${competitor} 小红书 爆款笔记`);
  if (!braveResults) {
    console.log('\n📊 竞品分析要点（本地知识库）:');
    console.log('\n🔍 分析维度:');
    console.log('1. 爆款标题规律：找数字型/疑问型/感叹型使用频率');
    console.log('2. 封面图风格：色调/字体/人物/产品使用模式');
    console.log('3. 内容结构：开头钩子写法、正文节奏、结尾CTA');
    console.log('4. 标签策略：高频标签词、标签数量（通常5个）');
    console.log('5. 互动引导：评论区引导方式、收藏话术');
    
    console.log('\n📋 爆款共性提取表:');
    console.log('| 维度     | 规律1         | 规律2         | 规律3         |');
    console.log('|----------|----------------|----------------|----------------|');
    console.log('| 标题类型 | 数字型         | 疑问型         | 感叹型         |');
    console.log('| 封面风格 |                 |                |                |');
    console.log('| 内容框架 |                 |                |                |');
    console.log('| 标签策略 |                 |                |                |');
    
    console.log('\n💡 建议: 找5-10篇竞品爆款，按上述维度填表，提取规律后再模仿');
    return;
  }

  const webResults = braveResults.web?.results || [];
  for (let i = 0; i < Math.min(webResults.length, 10); i++) {
    const result = webResults[i];
    const title = await translateToChinese(result.title || '');
    console.log(`${i + 1}. ${title}`);
    console.log(`   ${result.url}\n`);
  }
}

// CLI 入口
const args = process.argv.slice(2);
if (args.length === 0) {
  console.log('用法:');
  console.log('  node topic_research.js --topic "选题"        # 选题研究');
  console.log('  node topic_research.js --keyword "关键词"   # 关键词研究');
  console.log('  node topic_research.js --hot                # 热点话题');
  console.log('  node topic_research.js --competitor "竞品"  # 竞品分析');
  process.exit(0);
}

const topicIdx = args.indexOf('--topic');
const keywordIdx = args.indexOf('--keyword');
const hotIdx = args.indexOf('--hot');
const competitorIdx = args.indexOf('--competitor');
const countIdx = args.indexOf('--count');

let count = 10;
if (countIdx !== -1 && args[countIdx + 1]) {
  count = parseInt(args[countIdx + 1]);
}

(async () => {
  try {
    if (topicIdx !== -1 && args[topicIdx + 1]) {
      await topicResearch(args[topicIdx + 1]);
    } else if (keywordIdx !== -1 && args[keywordIdx + 1]) {
      await keywordResearch(args[keywordIdx + 1], count);
    } else if (hotIdx !== -1) {
      await hotTopics(count);
    } else if (competitorIdx !== -1 && args[competitorIdx + 1]) {
      await competitorAnalysis(args[competitorIdx + 1]);
    } else {
      console.error('❌ 缺少参数，请使用 --topic / --keyword / --hot / --competitor 指定研究类型');
      console.log('\n用法:');
      console.log('  node topic_research.js --topic "选题"        # 选题研究');
      console.log('  node topic_research.js --keyword "关键词"   # 关键词研究');
      console.log('  node topic_research.js --hot                # 热点话题');
      console.log('  node topic_research.js --competitor "竞品"  # 竞品分析');
      process.exit(1);
    }
  } catch (err) {
    console.error('❌ 运行出错:', err.message);
  }
})();
