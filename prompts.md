Build a Python backtesting project that duplicates the backtest shown in my screenshots, using fresh data from yfinance, and generates a final standalone HTML report with my own results, charts, and tables.

Project goal:
Backtest two daily dollar-cost averaging strategies on the Nasdaq index using yfinance data:

1. Fixed daily DCA:

* Invest a fixed amount every trading day.
* Default: 100 RMB/USD units per day.
* No market timing.
* No skipping days.
* Buy every trading day.

2. Dynamic return-based DCA:

* Invest a variable amount every trading day based on that day’s Nasdaq index return.
* The rule is: buy more when the index falls, buy less when the index rises.
* This is called “dynamic dip-buying DCA” or “return-adjusted DCA.”

Use yfinance data and generate a professional HTML report similar in structure to the screenshots, but using my own calculations and original wording.

Data:
Use yfinance.
Default signal/investment ticker:

* ^IXIC for Nasdaq Composite

Also make ticker configurable:

* ^IXIC
* QQQ
* SPY
* TQQQ

Use daily data.
Use adjusted close if available.
If yfinance returns auto-adjusted data, use the adjusted close equivalent.
Backtest end date should default to the latest available trading day.
Backtest periods:

* 3 years
* 5 years
* 10 years
* 20 years

For each period, calculate the start date by going backward from the final available date. Use the first available trading day on or after the calculated start date.

Initial capital:

* There is no lump-sum initial investment.
* Capital is deployed only through daily DCA contributions.

Currency:

* Use generic money units.
* The screenshots use RMB, but the math is identical. Label as “currency units” or make currency configurable.
* Default report label can be “元”.

Strategy 1: fixed daily DCA
Rule:

* Every trading day, invest exactly 100.
* Buy at that day’s adjusted close.
* Allow fractional shares.
* Hold all shares until the end.
* No selling.
* No transaction costs by default.

Strategy 2: dynamic daily DCA
Use same-day Nasdaq daily return to determine that day’s investment amount.

Daily return formula:
daily_return = close_today / close_yesterday - 1

Dynamic contribution rule from the screenshots:

1. If daily return is between -1% and +1%, invest 100.
2. If daily return is between -2% and -1%, invest 200.
3. If daily return is less than -2%, invest 300.
4. If daily return is between +1% and +2%, invest 50.
5. If daily return is greater than +2%, invest 20.

Clarify exact boundary handling in code:

* daily_return <= -2%: invest 300
* -2% < daily_return <= -1%: invest 200
* -1% < daily_return < +1%: invest 100
* +1% <= daily_return < +2%: invest 50
* daily_return >= +2%: invest 20

Make these thresholds and contribution amounts configurable in config.yaml.

Execution timing:
Default assumption:

* Signal uses same-day close-to-close return.
* Buy is executed at the same day’s adjusted close.
* This matches the screenshot-style simplified daily backtest.
* Add a config option for next_day_close execution to avoid same-day signal/execution concerns.
* Default should be same_day_close, but clearly mention this assumption in the report.

Important:
This strategy uses same-day return and same-day close execution. That is easy to reproduce but may not be executable in real life unless using near-close estimates. The HTML report must include a note explaining this.

Backtest output for each period:
For both strategies calculate:

* Total capital invested
* Final portfolio value
* Total profit = final value - total invested
* Total return rate = total profit / total invested
* Number of trading days
* Number of shares accumulated
* Average cost per share
* Ending price
* Annualized return based on invested capital
* Maximum drawdown of portfolio value
* Volatility of daily portfolio returns
* Sharpe ratio, risk-free rate default 0
* Daily contribution statistics:

  * Average daily contribution
  * Minimum contribution
  * Maximum contribution
  * Number of 20 contribution days
  * Number of 50 contribution days
  * Number of 100 contribution days
  * Number of 200 contribution days
  * Number of 300 contribution days

Comparison metrics:
For each period:

* Dynamic strategy total return rate
* Fixed 100 DCA total return rate
* Excess return rate = dynamic return rate - fixed return rate
* Dynamic final value
* Fixed final value
* Extra profit = dynamic profit - fixed profit
* Extra final value = dynamic final value - fixed final value
* Dynamic total invested - fixed total invested
* Difference caused by more capital deployed vs better timing

Important analytical point:
The report should separate:

1. Return-rate advantage
2. Absolute profit advantage
3. Extra money invested by dynamic strategy

The screenshots show that dynamic strategy may have only a small return-rate advantage, but much larger absolute profit because it invests more capital during declines.

Expected screenshot-style tables:
Create a summary table with rows:

* 3年
* 5年
* 10年
* 20年

Columns:

* 投资周期
* 动态定投总收益率
* 固定100定投总收益率
* 动态策略超额收益率
* 动态策略多赚金额
* 动态策略总投入
* 固定定投总投入
* 动态策略最终金额
* 固定定投最终金额

Also create an English version of the table if report language is set to English.

Charts to reproduce:

1. Total return rate comparison bar chart
   Title:
   “纳斯达克3/5/10/20年定投策略总收益率对比”
   X-axis:
   3年, 5年, 10年, 20年
   Y-axis:
   总收益率 (%)
   Bars:

* Dynamic return-adjusted DCA
* Fixed daily 100 DCA

Save:
results/charts/return_rate_comparison.png

2. Total profit amount comparison bar chart
   Title:
   “纳斯达克3/5/10/20年定投策略总收益金额对比”
   X-axis:
   3年, 5年, 10年, 20年
   Y-axis:
   收益金额
   Bars:

* Dynamic return-adjusted DCA profit
* Fixed daily 100 DCA profit

Save:
results/charts/profit_amount_comparison.png

3. Excess return rate line chart
   Title:
   “动态定投策略相对固定100定投的超额收益率变化”
   X-axis:
   3年, 5年, 10年, 20年
   Y-axis:
   超额收益率 (%)
   Line:

* Dynamic excess return over fixed DCA
  Horizontal dashed line at 0%

Save:
results/charts/excess_return_rate.png

4. Extra profit line chart
   Title:
   “动态定投策略相对固定100定投的多赚金额”
   X-axis:
   3年, 5年, 10年, 20年
   Y-axis:
   多赚金额

Save:
results/charts/extra_profit.png

5. Equity curve chart for each period
   For 3, 5, 10, and 20 years:

* Dynamic DCA portfolio value
* Fixed DCA portfolio value
* Optionally also plot cumulative invested capital

Save:
results/charts/equity_curve_3y.png
results/charts/equity_curve_5y.png
results/charts/equity_curve_10y.png
results/charts/equity_curve_20y.png

6. Contribution amount over time
   For each period:

* Plot daily dynamic contribution amount
* Show when it invests 20, 50, 100, 200, 300

Save:
results/charts/dynamic_contribution_3y.png
results/charts/dynamic_contribution_5y.png
results/charts/dynamic_contribution_10y.png
results/charts/dynamic_contribution_20y.png

7. Nasdaq price chart with contribution markers
   For 20-year period:

* Plot Nasdaq adjusted close
* Mark high contribution days, 200 and 300, in one color
* Mark low contribution days, 20 and 50, in another color

Save:
results/charts/nasdaq_price_with_dynamic_buy_markers_20y.png

8. Drawdown comparison
   For each period:

* Plot portfolio drawdown for dynamic DCA and fixed DCA

Save:
results/charts/drawdown_3y.png
results/charts/drawdown_5y.png
results/charts/drawdown_10y.png
results/charts/drawdown_20y.png

Backtesting engine:
Create clean modular Python code.

Suggested project structure:
nasdaq_dynamic_dca_backtest/
README.md
requirements.txt
config.yaml
main.py
src/
data_loader.py
strategies.py
backtest.py
metrics.py
plots.py
report.py
utils.py
data/
raw/
processed/
results/
charts/
tables/
report.html

requirements.txt:
pandas
numpy
yfinance
matplotlib
plotly
jinja2
pyyaml
scipy

Config file:
Create config.yaml with:

ticker: "^IXIC"
benchmark_ticker: "^IXIC"
end_date: null
periods_years: [3, 5, 10, 20]
base_daily_amount: 100
currency_label: "元"
execution_timing: "same_day_close"
allow_fractional_shares: true
commission_bps: 0
slippage_bps: 0
risk_free_rate: 0.0
report_language: "zh"

dynamic_dca_rules:

* min_return: null
  max_return: -0.02
  amount: 300
  label: "跌幅超过2%，定投300"
* min_return: -0.02
  max_return: -0.01
  amount: 200
  label: "跌幅1%-2%，定投200"
* min_return: -0.01
  max_return: 0.01
  amount: 100
  label: "涨跌幅-1%到1%，定投100"
* min_return: 0.01
  max_return: 0.02
  amount: 50
  label: "涨幅1%-2%，定投50"
* min_return: 0.02
  max_return: null
  amount: 20
  label: "涨幅超过2%，定投20"

Functions to implement:

data_loader.py:

* download_yfinance_data(ticker, start_date, end_date)
* clean_price_data(df)
* get_period_data(df, years, end_date)

strategies.py:

* fixed_daily_dca_amount(date, row, amount=100)
* dynamic_daily_dca_amount(daily_return, rules)

backtest.py:

* run_dca_backtest(price_data, contribution_function, execution_timing)
  Return:

  * equity_curve DataFrame
  * trade_log DataFrame
  * contribution_log DataFrame

Each daily row should track:

* date
* close
* daily_return
* contribution
* shares_bought
* cumulative_shares
* cumulative_invested
* cash
* portfolio_value
* profit
* return_on_invested_capital

metrics.py:

* calculate_summary_metrics(equity_curve, trade_log)
* calculate_drawdown(series)
* calculate_annualized_return()
* calculate_sharpe()
* calculate_period_comparison(dynamic_result, fixed_result)

plots.py:
Generate all charts listed above.

report.py:
Generate a standalone HTML report:
results/report.html

HTML report requirements:

* Use Jinja2.
* Include simple CSS.
* Make it readable like a blog article.
* Include chart images.
* Include tables.
* Include original analysis text based on computed results.
* Do not hardcode screenshot numbers.
* Use the actual backtest numbers.
* The report should be in Chinese by default.

HTML report structure:

1. Title
   “纳斯达克动态跌幅加码定投 vs 每日固定100定投：yfinance真实数据回测报告”

2. Executive summary
   Summarize:

* Data source: yfinance
* Ticker used
* Backtest end date
* Periods tested
* Best period for dynamic DCA
* Whether dynamic DCA beat fixed DCA by return rate
* Whether dynamic DCA beat fixed DCA by absolute profit
* Whether extra profit mainly came from higher capital deployment

3. Strategy rules
   Include:

* Strategy 1: 每日固定100定投
* Strategy 2: 动态跌幅加码定投
* Show the dynamic contribution table:

  * 跌幅超过2%：300
  * 跌幅1%-2%：200
  * 涨跌幅-1%到1%：100
  * 涨幅1%-2%：50
  * 涨幅超过2%：20

4. Data and assumptions
   Include:

* Ticker
* Date range
* Adjusted close usage
* Fractional shares
* No tax
* No fees by default
* Same-day signal and same-day close execution assumption
* Warning that real trading may require next-day execution

5. Core results table
   Embed the 3/5/10/20-year comparison table.

6. Return-rate comparison
   Embed return_rate_comparison.png.
   Write an interpretation:

* Which period had the highest excess return rate?
* Which period underperformed, if any?
* Was the return-rate difference large or small?

7. Profit amount comparison
   Embed profit_amount_comparison.png.
   Explain:

* Dynamic DCA may earn more absolute money because it contributes more during down days.
* Separate timing alpha from additional invested capital.

8. Excess return-rate trend
   Embed excess_return_rate.png.

9. Equity curve analysis
   Embed equity curves for 3/5/10/20 years.
   Discuss whether the strategies differ meaningfully over time.

10. Contribution behavior
    Embed contribution amount charts.
    Discuss:

* How often the strategy buys 300
* How often it buys 20
* Whether the dynamic strategy materially increases total invested capital

11. Drawdown analysis
    Embed drawdown charts.
    Discuss whether dynamic DCA reduces or increases drawdown.

12. Final conclusion
    The conclusion should be generated from actual results:

* If dynamic DCA beats fixed DCA in 20 years, say by how much.
* If fixed DCA beats dynamic DCA in any period, mention it clearly.
* Explain whether the advantage comes from smarter timing, more invested capital, or both.
* Include a practical note:
  “For ordinary investors, the most important factor is continuing to invest through bear markets. Strategy details are secondary to persistence.”

13. Appendix
    Include:

* Full config
* Data quality report
* Trade logs
* CSV output list

Output CSV files:
results/tables/summary_comparison.csv
results/tables/metrics_dynamic.csv
results/tables/metrics_fixed.csv
results/tables/trade_log_dynamic_3y.csv
results/tables/trade_log_dynamic_5y.csv
results/tables/trade_log_dynamic_10y.csv
results/tables/trade_log_dynamic_20y.csv
results/tables/trade_log_fixed_3y.csv
results/tables/trade_log_fixed_5y.csv
results/tables/trade_log_fixed_10y.csv
results/tables/trade_log_fixed_20y.csv
results/tables/data_quality_report.csv
results/equity_curves_dynamic.csv
results/equity_curves_fixed.csv

Console output after running:
Print:

* Data source
* Ticker
* Actual start date and end date
* For each period:

  * Dynamic total invested
  * Fixed total invested
  * Dynamic final value
  * Fixed final value
  * Dynamic total return rate
  * Fixed total return rate
  * Excess return rate
  * Extra profit
* Report saved path

Code quality:

* Modular functions.
* Clean comments.
* No lookahead bias except the clearly documented same-day close signal assumption.
* Make all parameters configurable.
* If data download fails, show a clear error.
* If 20 years of data is unavailable, run the shorter available periods and warn.

Important correctness check:
The screenshot-style rule says both strategies invest every trading day. The dynamic strategy does not wait for drawdown from all-time high. It adjusts the daily contribution based only on the index’s same-day daily return.

After coding, run:
python main.py

Final deliverable:
A complete runnable Python project that downloads yfinance data, backtests fixed daily DCA versus dynamic return-based DCA over 3/5/10/20 years, produces all CSV tables and charts, and creates results/report.html as a polished Chinese HTML backtest report using my own data.
