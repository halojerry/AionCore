#!/usr/bin/env node
/**
 * 小红书封面文案生成器
 * 用法: node cover_generator.js --topic "选题" [--style "种草"] [--style "教程"]
 */

const COVER_STYLES = {
  种草: {
    colors: ['#FFGE1', '#FFF5E6', '#FFE4E1'],
    titleFormat: '大字体 | 突出利益点 | 可加感叹词',
    examples: [
      { main: '这个面霜真的绝！', sub: '用了3个月皮肤细腻了' },
      { main: '均价50！均价50！', sub: '挖到宝了姐妹们' },
      { main: '后悔没早买！', sub: '租房神器Top1' },
    ],
    elements: ['emoji表情', '感叹号', '数字对比', '前后对比']
  },
  教程: {
    colors: ['#FFFFFF', '#F5F5F5', '#FAFAFA'],
    titleFormat: '清晰简洁 | 步骤感 | 可加序号',
    examples: [
      { main: '新手化妆｜保姆级教程', sub: '手把手教你从零开始' },
      { main: '5步搞定', sub: '上班族快手早餐' },
      { main: '一看就会！', sub: '日常通勤穿搭公式' },
    ],
    elements: ['步骤序号', '工具清单', '效果预览', '时间标注']
  },
  测评: {
    colors: ['#FFF0F5', '#F0F8FF', '#FFF8DC'],
    titleFormat: '对比感 | 突出悬念 | 可加问句',
    examples: [
      { main: '贵的VS便宜的差在哪？', sub: '10款面霜真实测评' },
      { main: 'XX品牌真的值得买吗？', sub: '无美颜无滤镜真实测评' },
      { main: '踩雷警告！', sub: '这些产品我劝你别买' },
    ],
    elements: ['对比图', '分数/星级', '价格标注', '真实感元素']
  },
  日常: {
    colors: ['#FFFEF0', '#F0FFF0', '#FFF5EE'],
    titleFormat: '亲切感 | 生活气息 | 可加日常词',
    examples: [
      { main: '周末日常🌿', sub: '一个人也要好好生活' },
      { main: '近期爱用物分享', sub: '均价不过百' },
      { main: 'Plog｜我的春日穿搭', sub: '简单舒适干净' },
    ],
    elements: ['emoji', '生活场景', '个人IP元素', '季节感']
  },
  合集: {
    colors: ['#FFFACD', '#E6E6FA', '#F0FFFF'],
    titleFormat: '数量感 | 清单体 | 可加“最”字',
    examples: [
      { main: '必买清单｜10件好物', sub: '附购物链接' },
      { main: 'Top10合集', sub: '2024最值得买的' },
      { main: '私藏店铺分享', sub: '学生党也能轻松入手' },
    ],
    elements: ['数字序号', '榜单感', '福利提示', '分类标签']
  }
};

const TITLE_TEMPLATES = {
  主标题: [
    '这个[XX]真的绝了！',
    '均价50！均价50！',
    '后悔没早买系列',
    '人手一件不过分吧',
    '我宣布这是Top1',
    '私藏已久的[XX]',
    '真的很好用！',
    '绝了绝了！'
  ],
  副标题: [
    '用了X个月真实反馈',
    '新手小白也能搞定',
    '均价不过百',
    '附详细测评',
    '建议收藏备用',
    '跟着买不踩雷',
    '真实无广放心入',
    '亲测有效'
  ],
  标签词: [
    '#好物分享 #种草 #平价好物',
    '#穿搭分享 #每日穿搭 #通勤穿搭',
    '#护肤 #测评 #好物推荐',
    '#教程 #新手教程 #保姆级',
    '#日常 #plog #生活记录'
  ]
};

function randomPick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function generateCover(topic, styles = []) {
  console.log(`\n🎨 封面文案生成 | 选题: ${topic}\n`);
  console.log('═'.repeat(50));

  // 确定风格
  if (styles.length === 0) {
    const allStyles = Object.keys(COVER_STYLES);
    styles = [randomPick(allStyles)];
  }

  styles.forEach((style) => {
    const styleData = COVER_STYLES[style];
    if (!styleData) {
      console.log(`\n⚠️ 未知风格: ${style}，跳过`);
      return;
    }

    console.log(`\n📌 风格: ${style}`);
    console.log('─'.repeat(30));
    console.log(`推荐色系: ${styleData.colors.join(' / ')}`);
    console.log(`标题格式: ${styleData.titleFormat}`);
    console.log(`常用元素: ${styleData.elements.join(' / ')}`);

    const example = randomPick(styleData.examples);
    console.log(`\n📸 封面文案示例:`);
    console.log(`   主标题: ${example.main}`);
    console.log(`   副标题: ${example.sub}`);
  });

  // 生成通用标题组合
  console.log('\n' + '─'.repeat(30));
  console.log('\n🔥 通用标题组合（可直接套用）:\n');

  for (let i = 0; i < 3; i++) {
    const main = randomPick(TITLE_TEMPLATES.主标题).replace('[XX]', topic);
    const sub = randomPick(TITLE_TEMPLATES.副标题);
    const tags = randomPick(TITLE_TEMPLATES.标签词);
    console.log(`组合${i + 1}:`);
    console.log(`   主标题: ${main}`);
    console.log(`   副标题: ${sub}`);
    console.log(`   推荐标签: ${tags}`);
    console.log('');
  }

  console.log('═'.repeat(50));
  console.log('\n💡 封面制作建议:');
  console.log('1. 主标题大字居中，3-6字最佳');
  console.log('2. 副标题补充信息，不超过10字');
  console.log('3. 竖版比例3:4，适配手机屏幕');
  console.log('4. 色彩对比度要高，远距离可辨识');
  console.log('5. 避免文字过多，核心信息一目了然');
  console.log('');
}

// CLI
const args = process.argv.slice(2);
if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
  console.log('用法:');
  console.log('  node cover_generator.js --topic "选题"                    # 生成封面文案');
  console.log('  node cover_generator.js --topic "选题" --style "种草"    # 指定风格');
  console.log('  node cover_generator.js --topic "选题" --style "教程"    # 指定多种风格');
  console.log('\n支持的风格: 种草 / 教程 / 测评 / 日常 / 合集');
  process.exit(0);
}

const topicIdx = args.indexOf('--topic');
if (topicIdx === -1 || !args[topicIdx + 1]) {
  console.error('❌ 请指定 --topic 参数，用法: node cover_generator.js --topic "选题"');
  process.exit(1);
}

const topic = args[topicIdx + 1];
const styleIndices = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--style' && args[i + 1]) {
    styleIndices.push(args[i + 1]);
  }
}

generateCover(topic, styleIndices);
