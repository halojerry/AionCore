# pounding-ozon Skill

1688 → Ozon 全链路跨境电商铺货助手。跟卖、新上架、变体合并、翻新、智能选品、AI 制图。

## 安装

```bash
# 1. 安装 Python 依赖
pip install pounding-ozon-cloud>=0.2.0

# 2. 可选：安装浏览器自动化支持（1688 商品详情采集）
pip install playwright>=1.40
playwright install chromium

# 3. 配置分发包凭据（Skill 附带的 mxou API key）
mkdir -p ~/.pounding
cat > ~/.pounding/config.json << 'EOF'
{
  "api": {"key": "<你的 mxou API key>", "base_url": "https://api.mxou.cn"}
}
EOF

# 4. 安装 Skill 到你的 AI 客户端
# Claude Code:
cp -r pounding-ozon-hybrid ~/.claude/skills/pounding-ozon/

# OpenClaw:
openclaw skills install ./pounding-ozon-hybrid

# Hermes:
hermes skills install ./pounding-ozon-hybrid
```

## 配置

首次使用时，AI 助手会引导你配置以下凭证（自动写入 `.env` 持久化）：

| 凭据 | 说明 |
|------|------|
| `ALI_1688_AK` | 1688 账号 AK（搜索/选品用） |
| `OZON_CLIENT_ID` | Ozon 商家 Client ID |
| `OZON_API_KEY` | Ozon 商家 API Key |

`MXOU_TOKEN` 和 `MXOU_IMAGE_TOKEN` 已在 `~/.pounding/config.json` 的 `api.key` 中配置，无需单独设置。

## 使用

直接在 AI 客户端中自然语言沟通：

- **新上架**："帮我把这个 1688 商品上架到 Ozon https://detail.1688.com/offer/xxx.html"
- **跟卖**："跟卖这个 Ozon 商品 https://www.ozon.ru/product/xxx/"
- **翻新**："翻新产品 12345"
- **智能选品**："帮我找一些蓝海产品上架到我店铺"
- **查看配置**："查看配置"

AI 助手会自动匹配对应的 Worker 并按步骤执行，每步都有进度汇报。

## 架构

```
本地 Skill (AI 客户端)          Cloud Pipeline (n8n + worker.mxou.cn)
─────────────────────          ─────────────────────────────────────
1688 选品/CDP 采集              COS 图片上传/镜像
类目匹配 (Supabase→Ozon 回退)   mxou AI 制图
属性解析                         Ozon 商品上架
信封构建 → POST n8n webhook →   Supabase 结果写入
```

## 版本

- Skill 版本：0.1.0
- Cloud 依赖：pounding-ozon-cloud >= 0.2.0
