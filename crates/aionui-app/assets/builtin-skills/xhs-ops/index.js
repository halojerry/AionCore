/**
 * 小红书运营助手 v2.0.3
 *
 * CLI 命令：
 *   node index.js topic --topic "选题"                    # 选题研究
 *   node index.js topic --keyword "关键词" --count 10   # 关键词研究
 *   node index.js topic --hot --count 20                # 热点话题
 *   node index.js topic --competitor "竞品名"           # 竞品分析
 *   node index.js title --topic "选题"                  # 爆款标题生成（AI驱动）
 *   node index.js cover --topic "选题" [--style 种草]  # 封面文案生成
 *   node index.js plan --name "账号名" --directions "种草,教程" --weekly 5  # 内容规划
 *   node index.js plan --interactive                    # 交互式内容规划
 *   node index.js note --title "标题" --topic "选题"   # 笔记正文生成（AI驱动）
 *   node index.js diagnose --stage "刚起号" --topic "美妆"  # 博主诊断（AI驱动）
 *   node index.js position --topic "美妆"              # 账号定位（AI驱动）
 *
 * handle() 函数（供其他 agent 直接调用）：
 *   handle({ params: { action: 'topic', topic: '选题' }})
 *   handle({ params: { action: 'title', topic: '选题', count: 8 }})
 *   handle({ params: { action: 'cover', topic: '选题', style: '种草' }})
 *   handle({ params: { action: 'plan', name: '账号名', directions: '种草,教程', weekly: 5 }})
 *   handle({ params: { action: 'note', title: '标题', topic: '选题', style: '种草' }})
 *   handle({ params: { action: 'diagnose', stage: '刚起号', topic: '美妆' }})
 *   handle({ params: { action: 'position', topic: '美妆' }})
 */

const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

// ─── 配色输出 ────────────────────────────────────────
const RESET = '\x1b[0m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[36m';
const RED = '\x1b[31m';

function log(msg, color = RESET) {
  console.log(`${color}${msg}${RESET}`);
}
function info(msg) { log(msg, BLUE); }
function success(msg) { log(msg, GREEN); }
function warn(msg) { log(msg, YELLOW); }
function error(msg) { log(msg, RED); }

// ─── 路径解析 ────────────────────────────────────────
const SCRIPT_DIR = path.join(__dirname, 'scripts');

function runScript(scriptName, args = []) {
  const scriptPath = path.join(SCRIPT_DIR, scriptName);
  if (!fs.existsSync(scriptPath)) {
    error(`❌ 脚本不存在: ${scriptName}`);
    console.log('可用命令: topic / title / cover / plan / note / diagnose / position');
    process.exit(1);
  }
  try {
    const result = execSync(`node "${scriptPath}" ${args.join(' ')}`, { encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024 });
    return result.trim();
  } catch (err) {
    const out = err.stdout ? err.stdout.trim() : '';
    const errOut = err.stderr ? err.stderr.trim() : '';
    if (out) return out;
    if (errOut) { console.error(errOut); process.exit(1); }
    console.error(`❌ 命令执行失败（exit ${err.status}）`);
    process.exit(err.status || 1);
    return '';
  }
}

function runScriptQuiet(scriptName, args = []) {
  // handle() 内部用，不打印只返回值
  const scriptPath = path.join(SCRIPT_DIR, scriptName);
  try {
    const result = execSync(`node "${scriptPath}" ${args.join(' ')}`, { encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024 });
    return result.trim();
  } catch (err) {
    const out = err.stdout ? err.stdout.trim() : '';
    return out || '';
  }
}

// ─── handle() 入口（供 agent 直接调用）───────────────
async function handle({ params = {} } = {}) {
  const {
    action = 'help',
    // topic params
    topic, keyword, hot, competitor, count,
    // title params
    list, audience,
    // cover params
    style,
    // plan params
    name, directions, weekly, weeks, interactive,
    // note params
    title,
    // diagnose params
    stage, fans, conf,
    // position params
    targetAudience, features,
  } = params;

  switch (action) {
    case 'topic': {
      const args = [];
      if (topic) { args.push('--topic', topic); }
      if (keyword) { args.push('--keyword', keyword); }
      if (hot) { args.push('--hot'); }
      if (competitor) { args.push('--competitor', competitor); }
      if (count) { args.push('--count', String(count)); }
      const out = runScriptQuiet('topic_research.js', args);
      return { success: true, action: 'topic', output: out };
    }

    case 'title': {
      const args = [];
      if (topic) { args.push('--topic', topic); }
      if (count) { args.push('--count', String(count)); }
      if (list) { args.push('--list'); }
      if (audience) { args.push('--audience', audience); }
      const out = runScriptQuiet('title_generator.js', args);
      return { success: true, action: 'title', output: out };
    }

    case 'cover': {
      const args = [];
      if (topic) { args.push('--topic', topic); }
      if (style) { args.push('--style', style); }
      const out = runScriptQuiet('cover_generator.js', args);
      return { success: true, action: 'cover', output: out };
    }

    case 'plan': {
      const args = [];
      if (interactive) { args.push('--interactive'); }
      else {
        if (name) { args.push('--name', name); }
        if (directions) { args.push('--directions', directions); }
        if (weekly) { args.push('--weekly', String(weekly)); }
        if (weeks) { args.push('--weeks', String(weeks)); }
      }
      const out = runScriptQuiet('content_planner.js', args);
      return { success: true, action: 'plan', output: out };
    }

    case 'note': {
      const args = [];
      if (title) { args.push('--title', title); }
      if (topic) { args.push('--topic', topic); }
      if (style) { args.push('--style', style); }
      const out = runScriptQuiet('note_generator.js', args);
      return { success: true, action: 'note', output: out };
    }

    case 'diagnose': {
      const args = [];
      if (stage) { args.push('--stage', stage); }
      if (topic) { args.push('--topic', topic); }
      if (fans) { args.push('--fans', String(fans)); }
      if (conf) { args.push('--conf', conf); }
      const out = runScriptQuiet('diagnose.js', args);
      return { success: true, action: 'diagnose', output: out };
    }

    case 'position': {
      const args = [];
      if (topic) { args.push('--topic', topic); }
      if (targetAudience) { args.push('--audience', targetAudience); }
      if (features) { args.push('--features', features); }
      const out = runScriptQuiet('position.js', args);
      return { success: true, action: 'position', output: out };
    }

    case 'help':
    default: {
      const out = runScript('diagnose.js', ['--help']);
      return {
        success: true,
        available_actions: ['topic', 'title', 'cover', 'plan', 'note', 'diagnose', 'position', 'help'],
        example: 'handle({ params: { action: "diagnose", stage: "刚起号", topic: "美妆" }})',
        help: out
      };
    }
  }
}

// ─── CLI 入口（仅直接运行时执行） ────────────────────────
if (require.main === module) {
  const cliArgs = process.argv.slice(2);
  const command = cliArgs[0];

  if (!command) {
    console.log(`
╔══════════════════════════════════════════════════════╗
║        小红书运营助手 v2.0.3                      ║
║  【小遇AI实验室荣誉出品】                          ║
╠══════════════════════════════════════════════════════╣
║  AI驱动版本 | 标题生成 · 笔记写作 · 博主诊断 · 账号定位 ║
╠══════════════════════════════════════════════════════╣
║  用法:                                            ║
║    node index.js topic --topic "选题"              ║
║    node index.js title --topic "选题"             ║
║    node index.js cover --topic "选题"             ║
║    node index.js plan --name "穿搭号" \\          ║
║                  --directions "种草,教程" \\        ║
║                  --weekly 5                        ║
║    node index.js note --title "标题" \\            ║
║                  --topic "选题"                    ║
║    node index.js diagnose --stage "刚起号" \\      ║
║                  --topic "美妆"                    ║
║    node index.js position --topic "美妆"          ║
║    node index.js llm-info                        ║
╚══════════════════════════════════════════════════════╝
    `);
    process.exit(0);
  }

  const subArgs = cliArgs.slice(1);

  switch (command) {
    case 'topic':
      console.log(runScript('topic_research.js', subArgs));
      break;
    case 'title':
      console.log(runScript('title_generator.js', subArgs));
      break;
    case 'cover':
      console.log(runScript('cover_generator.js', subArgs));
      break;
    case 'plan':
      console.log(runScript('content_planner.js', subArgs));
      break;
    case 'note':
      console.log(runScript('note_generator.js', subArgs));
      break;
    case 'diagnose':
      console.log(runScript('diagnose.js', subArgs));
      break;
    case 'position':
      console.log(runScript('position.js', subArgs));
      break;
    case 'llm-info':
      // 直接读取环境变量显示（不依赖 llm_client 初始化）
      console.log('\n🔍 LLM 配置信息：\n');
      const xhsKey = process.env.XHS_LLM_API_KEY ? '已设置 ✅' : '未设置';
      const xhsUrl = process.env.XHS_LLM_BASE_URL || '（使用默认）';
      const xhsModel = process.env.XHS_LLM_MODEL || '（使用默认）';
      const openaiKey = process.env.OPENAI_API_KEY ? '已设置 ✅' : '未设置';
      const minimaxKey = process.env.MINIMAX_API_KEY ? '已设置 ✅' : '未设置';
      const activeKey = process.env.XHS_LLM_API_KEY || process.env.OPENAI_API_KEY || process.env.MINIMAX_API_KEY || '无';
      const activeUrl = process.env.XHS_LLM_BASE_URL || process.env.OPENAI_BASE_URL || 'api.minimax.chat（默认）';
      const activeModel = process.env.XHS_LLM_MODEL || process.env.LLM_MODEL || 'minimax/MiniMax-M2.7-highspeed（默认）';
      console.log(`  XHS_LLM_API_KEY : ${xhsKey}`);
      console.log(`  XHS_LLM_BASE_URL : ${xhsUrl}`);
      console.log(`  XHS_LLM_MODEL   : ${xhsModel}`);
      console.log(`  OPENAI_API_KEY  : ${openaiKey}`);
      console.log(`  MINIMAX_API_KEY : ${minimaxKey}`);
      console.log('');
      console.log(`  当前生效配置：`);
      console.log(`  API_KEY : ${activeKey.replace(/^(.{6}).*(.{4})$/, '$1****$2')}`);
      console.log(`  BASE_URL: ${activeUrl}`);
      console.log(`  MODEL   : ${activeModel}`);
      console.log('\n  如需更换 LLM，请设置环境变量：');
      console.log('  export XHS_LLM_API_KEY=your_key');
      console.log('  export XHS_LLM_BASE_URL=https://your-endpoint.com');
      console.log('  export XHS_LLM_MODEL=your-model-name');
      console.log('');
      break;
    default:
      error(`未知命令: ${command}`);
      console.log('使用 node index.js 查看所有可用命令。');
      process.exit(1);
  }
}

module.exports = { handle };