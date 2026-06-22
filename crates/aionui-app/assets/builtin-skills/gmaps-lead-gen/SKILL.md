---
name: gmaps-lead-gen
description: "Google Maps lead generation and business intelligence. Scrape local businesses from Google Maps by category and location, extract business emails, find phone numbers, analyze competitors, and generate cold outreach materials. Use when user needs to find potential clients, build prospect lists, analyze local competition, or export business data from Google Maps."
description_zh: "Google Maps 获客与商业情报。按品类和位置从 Google Maps 抓取本地商家，提取邮箱/电话，分析竞品，生成开发信素材。"
version: 1.0.0
metadata:
  requires:
    bins: ["node"]
allowed-tools: Bash
---

# Google Maps Lead Generation — 谷歌地图获客

基于 [gmaps-agent-skills](https://github.com/gmapsscraper/google-maps-agent-skills) 的 Claude Code 技能封装。

## 核心能力

| 技能 | 说明 |
|------|------|
| `google-maps-scraper` | 按品类+位置抓取商家列表 |
| `business-email-extractor` | 从商家网站提取联系邮箱 |
| `google-maps-leads` | 组合获客：搜索 → 提取邮箱 → 输出列表 |
| `cold-email-local-business` | 基于商家信息生成个性化开发信 |
| `competitor-analysis-local` | 区域内竞品分析 |
| `google-maps-reviews-scraper` | 抓取 Google 评价 |
| `local-business-finder` | 按区域发现本地商家 |
| `google-maps-export` | 导出为 CSV/JSON |

## 典型用法

```bash
# 搜索旧金山地区家居用品进口商
node google-maps-scraper --query "home goods importer" --location "San Francisco, CA"

# 提取邮箱
node business-email-extractor --input results.json

# 生成开发信
node cold-email-local-business --business "ABC Imports" --category "home goods" --tone professional
```

## 输出格式

```json
[
  {
    "name": "ABC Home Imports",
    "address": "123 Market St, San Francisco, CA",
    "phone": "+1-415-555-0123",
    "website": "https://abcimports.com",
    "email": "info@abcimports.com",
    "rating": 4.5,
    "reviews": 128
  }
]
```
