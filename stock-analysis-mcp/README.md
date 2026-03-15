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

## 部署方式

### 方式 1: Docker (推荐)

```bash
# 拉取镜像
docker pull ryanpro1024/stock-analysis-api:latest

# 启动 MCP 容器
docker run -d -e MODE=mcp --name stock-analysis-mcp ryanpro1024/stock-analysis-api:latest
```

**OpenClaw 配置：**

```json
{
  "mcpServers": {
    "stock-analysis": {
      "command": "docker",
      "args": ["exec", "-i", "stock-analysis-mcp", "python", "-m", "src.mcp_server.server"]
    }
  }
}
```

### 方式 2: 本地运行

```bash
# 克隆仓库
git clone https://github.com/RyanProMax/stock-analysis-api.git
cd stock-analysis-api

# 安装 uv (如果没有)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate
uv pip install -e .

# 启动 MCP 服务
uv run mcp
```

**OpenClaw 配置：**

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

## 支持的股票格式

- **美股**: "AAPL", "NVDA", "TSLA"
- **A股**: "600519", "000001", "000858"

## 注意事项

- DCF 和 Comps 分析仅支持美股
- A股数据来源为 Tushare/AkShare，美股数据来源为 yfinance
