/**
 * 统一 LLM 客户端
 * 支持任意 OpenAI 兼容 API 端点（OpenAI/MiniMax/Groq/Gemini/Claude 等）
 * 优先级：显式参数 > XHS_LLM_* 环境变量 > OPENAI_* / MINIMAX_* 环境变量
 * 不可用时降级到演示数据
 */

const https = require('https');
const http = require('http');

// ─── 配置读取 ────────────────────────────────────────
// 专用配置（最高优先级）
const XHS_API_KEY = process.env.XHS_LLM_API_KEY || '';
const XHS_BASE_URL = process.env.XHS_LLM_BASE_URL || '';
const XHS_MODEL = process.env.XHS_LLM_MODEL || '';

// 兼容旧配置
const OPENAI_API_KEY = process.env.OPENAI_API_KEY || '';
const MINIMAX_API_KEY = process.env.MINIMAX_API_KEY || '';
const OPENAI_BASE_URL = process.env.OPENAI_BASE_URL || '';

// 最终配置
const API_KEY = XHS_API_KEY || OPENAI_API_KEY || MINIMAX_API_KEY || '';
const BASE_URL = XHS_BASE_URL || OPENAI_BASE_URL || 'https://api.minimax.chat';
const MODEL = XHS_MODEL || process.env.LLM_MODEL || 'minimax/MiniMax-M2.7-highspeed';

/**
 * 获取当前 LLM 配置信息（用于调试提示）
 */
function getLLMInfo() {
  if (XHS_API_KEY) return `XHS_LLM (${XHS_BASE_URL || BASE_URL})`;
  if (OPENAI_API_KEY) return `OpenAI (${OPENAI_BASE_URL || 'api.openai.com'})`;
  if (MINIMAX_API_KEY) return `MiniMax (api.minimax.chat)`;
  return null;
}

/**
 * 调用 LLM（OpenAI 兼容格式）
 */
async function chat(messages, options = {}) {
  const {
    model = MODEL,
    temperature = 0.8,
    max_tokens = 2048,
    fallback = null,
    timeout = 30000  // 默认30秒超时
  } = options;

  // 无 API Key 时降级
  if (!API_KEY) {
    if (!options._silent) console.log('（无 LLM API Key，使用演示数据）');
    if (fallback) return fallback;
    return '【演示数据】API Key 未配置，请设置 XHS_LLM_API_KEY 或 OPENAI_API_KEY 或 MINIMAX_API_KEY';
  }

  const llmInfo = getLLMInfo();
  if (!options._silent) console.log(`（使用 ${llmInfo}）`);

  const url = BASE_URL.includes('v1')
    ? `${BASE_URL}/chat/completions`
    : `${BASE_URL}/v1/chat/completions`;

  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ model, messages, temperature, max_tokens });

    const urlObj = new URL(url);
    const isHttps = urlObj.protocol === 'https:';
    const lib = isHttps ? https : http;

    const req = lib.request({
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Length': Buffer.byteLength(body)
      },
      timeout  // 设置超时
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.choices && json.choices[0]) {
            resolve(json.choices[0].message.content);
          } else if (json.error) {
            const errMsg = `API 错误: ${json.error.message}`;
            console.error(`[LLM] ${errMsg}`);
            reject(new Error(errMsg));  // 改为 reject，让调用方知道出错了
          } else {
            resolve(data);
          }
        } catch {
          resolve(fallback || data);
        }
      });
    });

    req.on('timeout', () => {
      req.destroy();
      const errMsg = 'LLM 请求超时（30秒）';
      console.error(`[LLM] ${errMsg}`);
      reject(new Error(errMsg));  // 超时也 reject
    });

    req.on('error', (e) => {
      console.error(`[LLM] 请求失败: ${e.message}`);
      reject(e);  // 网络错误也 reject
    });

    req.write(body);
    req.end();
  });
}

/**
 * 生成标题（LLM 版本）
 */
async function generateTitles(topic, targetAudience = null) {
  const audiencePart = targetAudience ? `\n目标受众：${targetAudience}` : '';
  
  const messages = [
    {
      role: 'system',
      content: `你是一个专业的小红书运营专家，擅长生成爆款标题。
要求：
1. 生成12个不同角度的标题
2. 必须覆盖至少4种情绪类型：痛点型/效果型/悬念型/情感型
3. 每个标题后面用 | 分隔，说明这个标题为什么能爆
4. 标题要符合小红书风格：emoji可用、口语化、有冲击力
5. 同一选题生成5次，每次标题要有明显差异（不同角度/切入点），差异度>60%

输出格式：
【类型】标题 | 爆款原因`
    },
    {
      role: 'user', 
      content: `选题：${topic}${audiencePart}

请生成12个爆款标题，覆盖痛点型、效果型、悬念型、情感型等多种类型。`
    }
  ];

  // 5次生成，取差异最大的版本（无API时只生成1次，避免重复提示）
  const results = [];
  const callCount = API_KEY ? 5 : 1;
  for (let i = 0; i < callCount; i++) {
    const result = await chat(messages, { temperature: 0.7 + Math.random() * 0.5, _silent: i > 0 });
    results.push(result);
  }

  // 返回第一次结果
  return results[0];
}

/**
 * 生成笔记正文（LLM 版本）
 */
async function generateNote(title, topic, style = '种草') {
  const styleDescs = {
    '种草': '种草安利型：真实体验分享，突出使用效果，语气亲切热情',
    '教程': '教程攻略型：步骤清晰，干货满满，适合收藏',
    '日常': '日常分享型：生活化叙事，有代入感',
    '测评': '测评对比型：客观分析优缺点，帮助决策',
    '合集': '合集整理型：信息密度高，实用性强'
  };

  const messages = [
    {
      role: 'system',
      content: `你是一个专业的小红书笔记写手，擅长写小红书风格的种草笔记。
要求：
1. 500-800字，emoji密集
2. 短句为主，每段不超过3行
3. 口语化，像在跟朋友说话
4. 收藏驱动的写作逻辑（让用户觉得"这篇要收藏"）
5. 结尾有明确的互动引导（收藏/评论/关注）
6. 标签：#小红书 #种草 #笔记（自动加，不要写出来）

笔记结构：
- 开头钩子（强吸引）
- 核心内容（分点展开）
- 个人体验/评价
- 结尾CTA（收藏引导）`
    },
    {
      role: 'user',
      content: `标题：${title}
选题：${topic}
风格：${styleDescs[style] || styleDescs['种草']}

请生成一篇小红书笔记正文。`
    }
  ];

  return await chat(messages, { temperature: 0.85, max_tokens: 2048 });
}

/**
 * 博主诊断（LLM 版本）
 */
async function diagnoseBlogger(stage, topic,粉丝数, 当前困惑) {
  const messages = [
    {
      role: 'system',
      content: `你是一个专业的小红书运营顾问，帮助博主诊断当前阶段的核心任务和优先级。
要求：
1. 分析博主当前阶段
2. 给出3个核心任务（按优先级排序）
3. 指出2-3个常见误区/避坑点
4. 建议1-2个立即可执行的行动
5. 语言简洁专业，但有温度

输出格式：
## 📍 当前阶段诊断
## 🎯 核心任务（Top 3）
## ⚠️ 避坑指南
## 🚀 立即行动`
    },
    {
      role: 'user',
      content: `账号阶段：${stage}
内容方向：${topic}
${粉丝数 ? `粉丝量：${粉丝数}` : ''}
当前困惑：${当前困惑 || '还不确定怎么做'}

请给出运营建议。`
    }
  ];

  return await chat(messages, { temperature: 0.7, max_tokens: 2048 });
}

/**
 * 账号定位（LLM 版本）
 */
async function positionBlogger(topic, 目标用户, 个人特点) {
  const messages = [
    {
      role: 'system',
      content: `你是一个专业的小红书账号定位顾问，帮助新人找到自己的独特定位。
要求：
1. 给出昵称方向建议（3-5个可选）
2. 给出简介框架（3行公式）
3. 给出视觉风格建议（封面风格/色调/排版方向）
4. 给出内容方向建议（最适合起步的3个内容类型）
5. 语言简洁，有洞察，能让人眼前一亮

输出格式：
## 🎯 昵称方向
## 📝 简介框架
## 🎨 视觉风格
## 📋 内容方向建议`
    },
    {
      role: 'user',
      content: `内容方向：${topic}
目标用户：${目标用户 || '还没想清楚'}
个人特点：${个人特点 || '还没想清楚'}

请给出账号定位建议。`
    }
  ];

  return await chat(messages, { temperature: 0.8, max_tokens: 2048 });
}

/**
 * 翻译英文为中文（用于搜索结果）
 */
async function translateToChinese(text) {
  if (!text || !/[a-zA-Z]/.test(text)) return text;
  
  const messages = [
    {
      role: 'system',
      content: '你是一个翻译专家，将英文翻译成中文。保持原意简洁准确。'
    },
    {
      role: 'user',
      content: `翻译为中文：${text}`
    }
  ];

  return await chat(messages, { temperature: 0.3, max_tokens: 1024 });
}

module.exports = { chat, generateTitles, generateNote, diagnoseBlogger, positionBlogger, translateToChinese };