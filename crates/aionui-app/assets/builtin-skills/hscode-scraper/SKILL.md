---
name: hscode-scraper
description: "HS code lookup, tariff comparison, and customs requirements search for international trade. Query HS codes by product name, brand, or code. Compare import duties across US, China, UAE, and EU. Look up China customs/CIQ requirements. Use when user asks about HS codes, tariff rates, customs duties, product classification for import/export, or trade compliance requirements."
description_zh: "HS 编码查询、关税对比和海关要求搜索。按产品名/品牌/编码查询 HS 码，对比中美/阿联酋/欧盟关税，查询中国海关/CIQ 要求。"
version: 1.0.0
metadata:
  requires:
    bins: ["node"]
allowed-tools: Bash
---

# HS Code Scraper — 海关编码查询与关税对比

基于 [hscode-scraper](https://github.com/mmourani/hscode-scraper) 开源项目封装的 Node.js 命令行工具。支持产品名/品牌/编码查询 HS 码，并对比多国关税。

## 核心能力

1. **产品 → HS 编码** — 输入产品名称或品牌，返回最匹配的 HS 编码
2. **编码 → 详情** — 输入 HS 编码，返回描述、关税、CIQ 要求
3. **跨国关税对比** — US vs China vs UAE vs EU 关税对比
4. **品牌智能识别** — 自动识别苹果/三星/华为等品牌，映射到原产国

## 命令

### 查找 HS 编码

```bash
node lookup_hscode.js --query "bluetooth earphone"
node lookup_hscode.js --query "LED lighting" --max 10
node lookup_hscode.js --code "8526.91"
```

### 跨国关税对比

```bash
node compare_hscode_cli.js --query "iphone 15" --country china
node compare_hscode_cli.js --query "solar panel" --compare us,china,eu
```

### 品牌搜索（带品牌智能识别）

```bash
node compare_hscode_cli.js --query "sony playstation 5"
# 自动识别 Sony=日本，PlayStation=游戏主机，匹配对应 HS 码
```

## 输出示例

```
Query: bluetooth earphone
┌──────────────────────────────────────────────────────────────┐
│ HS Code     │ Description                    │ Duty (CN→US)  │
├──────────────────────────────────────────────────────────────┤
│ 8518.30.20  │ Headphones, earphones,         │ 0% (Section   │
│             │ combined with microphone       │ 301 tariff    │
│             │                                │ exclusion)    │
└──────────────────────────────────────────────────────────────┘
```

## 注意事项

- 中国 HS 码数据需要先运行爬虫填充（`scrape-hscodes.js`），首次使用可能需要初始化数据库
- 关税数据为参考值，实际以各国海关最新公告为准
- 品牌数据库为静态映射（`brand_products.json`），未覆盖的品牌按通用产品名搜索
