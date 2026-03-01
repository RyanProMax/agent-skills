---
name: stock-analyzer
description: Fetches stock analysis data from external API and generates formatted text analysis reports. Use this skill when the user asks to analyze stocks, get stock analysis reports, or check stock indicators. Supports batch analysis of multiple stocks (e.g., "Analyze NVDA and AAPL", "Give me a report on TSLA"). Handles API cold start with automatic retry mechanism.
---

# Stock Analyzer

## Overview

Fetch stock analysis data from external API and generate formatted text analysis reports with technical indicators, fundamental metrics, and market sentiment.

## When to Use

Use this skill when the user requests:
- Stock analysis or analysis reports
- Technical indicators (MA, MACD, RSI, KDJ, etc.)
- Fundamental metrics (PE, PB, ROE, etc.)
- Market sentiment (fear/greed index)
- Batch analysis of multiple stocks

**Example triggers:**
- "Analyze NVDA"
- "Give me a stock report on AAPL and MSFT"
- "What's the technical analysis for TSLA?"
- "Check the indicators for 600519"

## Workflow

### Step 1: Parse Stock Symbols

Extract stock symbols from user input. Support formats:
- Single stock: "NVDA", "AAPL"
- Multiple stocks: "NVDA, AAPL, MSFT"
- Chinese stocks: "600519", "000001"

### Step 2: Call External API

Use the API client script to fetch stock data:

```bash
python ~/.claude/skills/stock-analyzer/scripts/fetch_stock_data.py "NVDA,AAPL"
```

The script handles:
- API request with proper headers
- Automatic retry (3 attempts with exponential backoff)
- Timeout handling (30 seconds per request)
- Error reporting

### Step 3: Generate Report

After receiving API response, generate a formatted report using the template in `references/report_template.md`:

1. Read the report template
2. Fill in the data for each stock
3. Use LLM to generate comprehensive analysis based on the indicators
4. Format output in markdown

### Step 4: Present Results

Present the analysis report to the user in a clear, structured format.

## API Details

**Endpoint**: `https://stock-analyzer-service-55638944338.us-central1.run.app/stock/analyze`

**Method**: POST

**Request Body**:
```json
{
  "symbols": ["NVDA", "AAPL"]
}
```

**Response Structure**:
```json
{
  "status_code": 200,
  "data": [
    {
      "symbol": "NVDA",
      "stock_name": "NVIDIA Corporation",
      "price": 177.19,
      "fear_greed": { "index": 26.4, "label": "恐慌" },
      "technical": { "factors": [...] },
      "fundamental": { "factors": [...] }
    }
  ]
}
```

## Error Handling

- **API Timeout**: Retry up to 3 times with exponential backoff
- **Invalid Symbol**: Report which symbol failed
- **API Error**: Display error message and suggest retry

## Resources

### scripts/
- `fetch_stock_data.py` - API client with retry mechanism

### references/
- `report_template.md` - Fixed report template structure
