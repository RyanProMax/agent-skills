# Stock Analysis MCP

股票分析 MCP 服务，为 OpenClaw Agent 提供股票分析能力。

## 仓库地址

[https://github.com/RyanProMax/stock-analysis-api](https://github.com/RyanProMax/stock-analysis-api)

## MCP 工具列表

| 工具 | 描述 | 参数 |
|------|------|------|
| `analyze_stock` | 综合分析股票（技术面+基本面） | symbol, include_qlib? |
| `get_stock_list` | 获取股票列表 | market?, refresh? |
| `search_stocks` | 搜索股票 | keyword, market? |
| `analyze_dcf` | DCF 估值分析 (仅美股) | symbol |
| `analyze_comps` | 可比公司分析 (仅美股) | symbol, sector? |

## OpenClaw 配置

在 OpenClaw 的 `.openclaw/` 配置目录中添加 MCP Server：

```json
{
  "mcpServers": {
    "stock-analysis": {
      "command": "python",
      "args": ["-m", "src.mcp_server.server"],
      "cwd": "/path/to/stock-analysis-api"
    }
  }
}
```

## 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/RyanProMax/stock-analysis-api.git
cd stock-analysis-api
```

2. 安装依赖

```bash
poetry install
```

3. 配置 OpenClaw

将上述 MCP Server 配置添加到 OpenClaw 配置文件中。

## 支持的股票格式

- **美股**: "AAPL", "NVDA", "TSLA"
- **A股**: "600519", "000001", "000858"

## 注意事项

- DCF 和 Comps 分析仅支持美股
- A股数据来源为 Tushare/AkShare，美股数据来源为 yfinance
