---
name: stock-analyzer
description: 股票分析 MCP 服务，提供技术面/基本面分析、DCF估值、可比公司分析等能力。支持 A股和美股。当用户要求分析股票、查看股票指标、进行估值分析时使用此 skill。
---

# Stock Analyzer MCP

## Overview

股票分析 MCP 服务，通过本地 MCP Server 提供股票分析能力，包括技术指标、基本面指标、DCF 估值和可比公司分析。

## MCP 工具列表

| 工具 | 描述 | 参数 |
|------|------|------|
| `analyze_stock` | 综合分析股票（技术面+基本面） | symbol, include_qlib? |
| `get_stock_list` | 获取股票列表 | market?, refresh? |
| `search_stocks` | 搜索股票 | keyword, market? |
| `analyze_dcf` | DCF 估值分析 (仅美股) | symbol |
| `analyze_comps` | 可比公司分析 (仅美股) | symbol, sector? |

## When to Use

Use this skill when the user requests:

- 股票分析或分析报告
- 技术指标 (MA, MACD, RSI, KDJ 等)
- 基本面指标 (PE, PB, ROE 等)
- DCF 估值分析
- 可比公司分析
- 搜索股票或获取股票列表

**Example triggers:**

- "分析 AAPL"
- "搜索名称包含 Apple 的股票"
- "对 NVDA 进行 DCF 估值分析"
- "获取 A股 股票列表"
- "分析 600519 的技术面"

## 使用流程

### Step 1: 确认 MCP Server 已配置

检查 OpenClaw 配置中是否已添加 stock-analysis MCP Server。

### Step 2: 调用 MCP 工具

根据用户需求选择合适的工具：

| 用户需求 | 使用工具 |
|----------|----------|
| 分析某只股票 | `analyze_stock` |
| 搜索股票 | `search_stocks` |
| 获取股票列表 | `get_stock_list` |
| DCF 估值 | `analyze_dcf` (仅美股) |
| 可比公司分析 | `analyze_comps` (仅美股) |

### Step 3: 格式化输出

使用 `references/report_template.md` 中的模板格式化分析报告。

## 支持的股票格式

- **美股**: "AAPL", "NVDA", "TSLA"
- **A股**: "600519", "000001", "000858"

## 注意事项

- DCF 和 Comps 分析仅支持美股
- A股数据来源为 Tushare/AkShare，美股数据来源为 yfinance
- 部分指标可能因数据源限制而不可用

## Resources

### references/

- `report_template.md` - 股票分析报告模板
