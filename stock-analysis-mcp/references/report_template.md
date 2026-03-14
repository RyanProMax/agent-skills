# Stock Analysis Report Template

Use this template to generate formatted stock analysis reports.

## Report Structure

```markdown
# {stock_name} ({symbol}) 分析报告

## 基本信息

| 指标 | 数值 |
|------|------|
| 当前价格 | ${price} |
| 贪恐指数 | {fear_greed.index} ({fear_greed.label}) |
| 数据来源 | {data_source} |

## 技术面分析

### 关键指标状态

| 指标 | 状态 | 看涨信号 | 看跌信号 |
|------|------|----------|----------|
| MA均线 | {status} | {bullish} | {bearish} |
| MACD | {status} | {bullish} | {bearish} |
| RSI | {status} | {bullish} | {bearish} |
| KDJ | {status} | {bullish} | {bearish} |
| 布林带 | {status} | {bullish} | {bearish} |
| WR威廉 | {status} | {bullish} | {bearish} |
| 成交量比率 | {status} | {bullish} | {bearish} |

### 技术面信号汇总

**看涨信号:**
- {list all bullish signals from technical.factors}

**看跌信号:**
- {list all bearish signals from technical.factors}

## 基本面分析

### 估值指标

| 指标 | 数值 |
|------|------|
| 市盈率(TTM) | {trailingPE} |
| 远期市盈率 | {forwardPE} |
| 市净率 | {priceToBook} |
| 市销率 | {priceToSalesTrailing12Months} |
| EV/EBITDA | {enterpriseToEbitda} |
| 市值 | {marketCap} |

### 财务健康度

| 指标 | 数值 |
|------|------|
| 毛利率 | {grossMargins} |
| 营业利润率 | {operatingMargins} |
| 净利润率 | {profitMargins} |
| ROA | {returnOnAssets} |
| ROE | {returnOnEquity} |

### 成长性

| 指标 | 数值 |
|------|------|
| 营收增长率 | {revenueGrowth} |
| 盈利增长率 | {earningsGrowth} |
| 季度盈利增长 | {earningsQuarterlyGrowth} |

### 偿债能力

| 指标 | 数值 |
|------|------|
| 流动比率 | {currentRatio} |
| 速动比率 | {quickRatio} |
| 负债权益比 | {debtToEquity} |

## 综合分析

[Generate a comprehensive analysis paragraph based on all the above data. Consider:
1. Overall market sentiment from fear/greed index
2. Technical trend direction and strength
3. Fundamental valuation and financial health
4. Growth potential and risks
5. Investment recommendation with reasoning]
```

## Notes for Report Generation

1. **Signal Extraction**: Loop through `technical.factors` and `fundamental.factors` arrays to extract signals
2. **Data Formatting**: Format percentages and large numbers appropriately (e.g., 4.31万亿 for market cap)
3. **Missing Data**: If a field is missing, display "-" instead of leaving blank
4. **Multiple Stocks**: For batch analysis, repeat the template for each stock with a separator line `---`
5. **Language**: Use Chinese for labels, keep numbers and symbols as-is

## Example Output

```markdown
# NVIDIA Corporation Common Stock (NVDA) 分析报告

## 基本信息

| 指标 | 数值 |
|------|------|
| 当前价格 | $177.19 |
| 贪恐指数 | 26.4 (😨 恐慌) |
| 数据来源 | US_yfinance |

## 技术面分析

### 关键指标状态

| 指标 | 状态 | 看涨信号 | 看跌信号 |
|------|------|----------|----------|
| MA均线 | 震荡/不明确 | - | 价格跌破 MA5 |
| MACD | MACD 柱线走弱 | - | MACD 柱线走弱 |
| RSI | RSI 正常 (40.3) | - | - |
| KDJ | KDJ 空头形态 | - | KDJ 空头形态，J 下穿 |
| 布林带 | 布林带宽度正常 | 布林带宽度处于健康波动区间, 价格贴近布林下轨存在支撑 | - |
| WR威廉 | WR 进入底部区域 | WR 进入底部区域 (-96.2) | - |
| 成交量比率 | 量能正常 (1.22x) | 短期均量高于中期均量 | - |

### 技术面信号汇总

**看涨信号:**
- WR 进入底部区域 (-96.2)
- 布林带宽度处于健康波动区间
- 价格贴近布林下轨，存在支撑
- 短期均量高于中期均量，资金净流入

**看跌信号:**
- 价格跌破 MA5
- MACD 柱线走弱，动能衰减
- KDJ 空头形态，J 下穿

## 基本面分析

### 估值指标

| 指标 | 数值 |
|------|------|
| 市盈率(TTM) | 36.09 |
| 远期市盈率 | 16.62 |
| 市净率 | 27.38 |
| 市销率 | 19.94 |
| EV/EBITDA | 31.93 |
| 市值 | 4.31万亿 |

### 财务健康度

| 指标 | 数值 |
|------|------|
| 毛利率 | 71.07% |
| 营业利润率 | 65.02% |
| 净利润率 | 55.60% |
| ROA | 51.19% |
| ROE | 101.48% |

### 成长性

| 指标 | 数值 |
|------|------|
| 营收增长率 | 73.20% |
| 盈利增长率 | 95.60% |
| 季度盈利增长 | 94.50% |

### 偿债能力

| 指标 | 数值 |
|------|------|
| 流动比率 | 3.90 |
| 速动比率 | 3.14 |
| 负债权益比 | 7.25 |

## 综合分析

NVIDIA 目前处于技术调整阶段，价格跌破短期均线，MACD 动能减弱，KDJ 呈空头形态，
市场情绪偏向恐慌（贪恐指数 26.4）。然而，WR 指标进入底部区域，价格接近布林带下轨，
可能存在短期反弹机会。

基本面方面，公司财务状况极佳：毛利率 71%，ROE 超过 100%，营收和盈利增长率均在 70% 以上，
显示强劲的成长动力。远期市盈率 16.62 显著低于当前市盈率，表明市场预期盈利持续增长。

**建议**: 短期技术面偏弱，建议等待技术指标修复后再考虑入场。长期投资者可关注回调机会，
公司基本面优秀，成长性突出。支撑位关注 $173（布林下轨），压力位 $188（MA5）。
```
