# 纳斯达克动态跌幅加码定投 vs 每日固定100定投

复现某头条文章的定投回测逻辑，但使用 **yfinance 真实历史数据** 重新计算，并生成自己的
独立 HTML 报告（图表 + 表格 + 基于真实结果的文字分析）。

对比两种**每个交易日都买入**的日定投策略：

1. **每日固定100定投** —— 无论涨跌，每个交易日固定投入 100。
2. **动态跌幅加码定投** —— 根据当日涨跌幅调整投入：跌得越多买得越多，涨得越多买得越少。

## 动态投入规则

| 当日涨跌幅 | 当日投入 |
|---|---|
| 跌幅超过 2% | 300 |
| 跌幅 1%–2% | 200 |
| 涨跌幅 -1% 到 +1% | 100 |
| 涨幅 1%–2% | 50 |
| 涨幅超过 2% | 20 |

边界处理（见 `config.yaml`）：`r<=-2%→300`，`-2%<r<=-1%→200`，`-1%<r<1%→100`，
`1%<=r<2%→50`，`r>=2%→20`。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

运行后打开 `results/report.html` 查看完整报告。

## 配置（config.yaml）

| 参数 | 说明 |
|---|---|
| `ticker` | 标的，可选 `^IXIC` / `QQQ` / `SPY` / `TQQQ` |
| `end_date` | 回测截止日，`null` = 最新交易日 |
| `periods_years` | 回测周期列表，默认 `[3, 5, 10, 20]` |
| `base_daily_amount` | 固定策略每日投入，默认 100 |
| `execution_timing` | `same_day_close`（默认）或 `next_day_close` |
| `allow_fractional_shares` | 是否允许小数股 |
| `commission_bps` / `slippage_bps` | 佣金 / 滑点（基点），默认 0 |
| `risk_free_rate` | 夏普比率的无风险利率，默认 0 |
| `dynamic_dca_rules` | 动态投入的分档阈值与金额 |

## 重要假设

默认使用「**当日涨跌幅作为信号、并以当日收盘价成交**」。这便于复现文章，但真实交易中通常
需采用临近收盘估算价，或改用 `next_day_close`（次日收盘成交）以避免同日信号/成交的疑虑。
报告中对此有明确提示。

- 价格使用 yfinance 自动复权后的收盘价（等价调整收盘价），已处理分红与拆股。
- 无一次性本金，资金完全通过每日定投投入。
- 默认无税费、无佣金、无滑点。
- 若数据不足以覆盖某周期，会自动跳过并给出警告。

## 项目结构

```
config.yaml            # 全部可配置参数
main.py                # 端到端编排
requirements.txt
src/
  data_loader.py       # yfinance 下载、清洗、按周期切片
  strategies.py        # 两种每日投入规则
  backtest.py          # 日定投回测引擎
  metrics.py           # 指标：收益率、XIRR 年化、回撤、波动率、夏普
  plots.py             # 全部图表
  report.py            # Jinja2 HTML 报告
  utils.py             # 配置/日志/路径
data/                  # raw + processed（git 忽略）
results/
  charts/              # 所有 PNG 图表
  tables/              # 所有 CSV 表格
  report.html          # 最终报告
logs/
```

## 指标说明

- **总收益率** = 总收益 / 总投入（简单口径，与文章一致）。
- **年化收益率** 使用资金加权的 **XIRR**（按每日现金流求解），更适合逐步投入的定投。
- **最大回撤** 为组合价值的峰谷跌幅。
- **波动率 / 夏普** 基于「剔除新投入后」的每日市场收益，反映持仓的市场波动而非现金流入。

## 免责声明

本项目仅供研究与学习，不构成任何投资建议。回测结果依赖历史数据与简化假设，
不代表未来表现。
