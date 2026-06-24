---
name: cold-email-automation
description: "AI-powered cold email outreach automation. Find prospects, generate personalized emails with AI, send via SMTP/Gmail/Zoho, and manage follow-up sequences. Use when user needs to send cold outreach emails, build email campaigns, or automate prospect communication for sales/BD."
description_zh: "AI 冷邮件自动化。发现潜在客户 → AI 生成个性化邮件 → SMTP/Gmail/Zoho 发送 → 跟进序列管理。"
version: 1.0.0
metadata:
  requires:
    bins: ["python3"]
allowed-tools: Bash
---

# Cold Email Automation — 冷邮件自动化

基于 [free_outbound_agent](https://github.com/Dumebii/free_outbound_agent) 开源项目。

## 核心能力

1. **客户发现** — 从 GitHub/Dev.to 等平台自动发现潜在客户
2. **AI 写作** — 用 Claude/GPT-4 生成个性化冷邮件
3. **多渠道发送** — SMTP/Gmail API/Zoho 支持
4. **跟进序列** — 自动管理多轮跟进
5. **追踪分析** — 打开率/回复率统计

## 配置

编辑 `config.yaml`：

```yaml
email:
  provider: smtp  # smtp | gmail | zoho
  smtp_host: smtp.gmail.com
  smtp_port: 587
  username: ${SMTP_USER}
  password: ${SMTP_PASS}

ai:
  provider: claude  # claude | openai
  model: claude-sonnet-4-20250514

follow_up:
  max_rounds: 3
  interval_days: 3
```

## 发送邮件

```bash
# 批量发送
python3 pipeline.py --source linkedin --template outreach

# 单封发送
python3 send/send_email.py --to "prospect@company.com" --template intro
```

## 模板变量

```
{first_name} {company} {industry} {pain_point} {value_prop}
```

## 合规要求

- 确保邮件列表已获得收件人同意（opt-in）
- 遵守 CAN-SPAM 法规（提供退订链接）
- 不发送垃圾邮件
