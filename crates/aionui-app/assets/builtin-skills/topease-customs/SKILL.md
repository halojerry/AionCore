---
name: topease-customs
description: "Global customs trade data MCP server covering 238 countries. Query import/export data by company name, product keyword, HS code, trade dates, trade type, and country. Use when user needs customs trade statistics, competitor trade volume analysis, or market entry research for any country."
description_zh: "全球海关贸易数据 MCP 服务（238 国）。按公司名/产品关键词/HS 码/日期/贸易类型/国家查询进出口数据。"
version: 1.0.0
metadata:
  requires:
    mcp: ["topease-customs"]
allowed-tools: Bash
---

# Topease Customs — 全球海关贸易数据

基于 [topease-customs-mcp](https://github.com/topease020/topease-customs-mcp-server) 的 MCP 服务，覆盖 238 国海关贸易数据。

## 前置条件

1. 注册获取 API Key：https://tradee.topease.net/
2. 配置 MCP Server：

```json
{
  "mcpServers": {
    "topease-customs": {
      "command": "uvx",
      "args": ["topease-mcp"],
      "env": { "TOPEASE_API_KEY": "your-key" }
    }
  }
}
```

安装：`pip install topease-mcp` 或 `uvx topease-mcp`

## 核心能力

| 查询维度 | 说明 |
|---------|------|
| 公司名 | 查特定进出口商的贸易记录 |
| 产品关键词 | 某产品品类的进出口趋势 |
| HS 编码 | 精确编码的国际流向分析 |
| 贸易日期 | 时间范围筛选 |
| 贸易类型 | 进口/出口/转口 |
| 国家 | 按贸易伙伴国筛选 |

## 典型查询

- 「查苹果公司近一年从中国进口的数据」
- 「蓝牙耳机（HS 8518.30）主要出口到哪些国家」
- 「2024 年中国光伏组件出口趋势」

## 注意事项

- 需要付费 API Key（商业数据源）
- 数据为权威海关统计，时效性取决于各国海关更新频率
- 部分小国数据可能不完整
