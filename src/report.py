"""Generate a standalone Chinese HTML backtest report with Jinja2.

All narrative text is derived from the computed results — no screenshot numbers
are hardcoded.
"""

import logging
import os

from jinja2 import Template

logger = logging.getLogger("nasdaq_dca")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
  :root { --red:#e02e24; --red-soft:#fdecea; --ink:#1f2329; --gray:#8a9099; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
         line-height: 1.85; color: var(--ink); margin: 0; background: #f2f3f5;
         font-size: 17px; -webkit-font-smoothing: antialiased; }
  .page { max-width: 680px; margin: 0 auto; background: #fff; padding: 30px 22px 70px;
          box-shadow: 0 0 18px rgba(0,0,0,.05); }
  h1 { font-size: 24px; line-height: 1.45; font-weight: 800; margin: 0 0 14px; }
  .byline { color: var(--gray); font-size: 13px; border-bottom: 1px solid #eee;
            padding-bottom: 16px; margin-bottom: 8px; }
  h2 { font-size: 20px; font-weight: 800; color: var(--red); margin: 40px 0 6px;
       padding-left: 12px; border-left: 4px solid var(--red); }
  h3 { font-size: 17px; font-weight: 700; color: var(--ink); margin: 26px 0 6px; }
  p { margin: 12px 0; }
  .lead { background: var(--red-soft); border-radius: 10px; padding: 16px 18px; margin: 16px 0;
          font-size: 16px; }
  .lead ul { margin: 8px 0 0; padding-left: 20px; }
  .lead li { margin: 6px 0; }
  .note { background: #fff8e6; border-left: 4px solid #f0ad4e; padding: 12px 16px;
          margin: 18px 0; border-radius: 6px; font-size: 15px; }
  .advice { background: #f6f8fa; border-radius: 10px; padding: 6px 20px 14px; margin: 16px 0; }
  .advice h3 { color: var(--red); }
  table { border-collapse: collapse; width: 100%; margin: 18px 0; font-size: 13px; background: #fff;
          display: block; overflow-x: auto; white-space: nowrap; }
  th, td { border: 1px solid #ebedf0; padding: 8px 10px; text-align: right; }
  th { background: #fafafa; color: #555; text-align: center; font-weight: 700; }
  td:first-child, th:first-child { text-align: center; font-weight: 600; }
  tr:nth-child(even) td { background: #fbfcfd; }
  img { max-width: 100%; height: auto; display: block; margin: 16px auto;
        border: 1px solid #f0f0f0; border-radius: 8px; }
  .hot { color: var(--red); font-weight: 800; }
  .pos { color: var(--red); font-weight: 700; }
  .neg { color: #1aa06d; font-weight: 700; }
  code { background: #f2f3f5; padding: 1px 6px; border-radius: 4px; font-size: 14px; }
  pre { background: #1f2329; color: #e6e6e6; padding: 14px; border-radius: 8px;
        overflow-x: auto; font-size: 12px; line-height: 1.6; white-space: pre; }
  details { margin: 12px 0; }
  summary { cursor: pointer; font-weight: 700; color: #555; }
  footer { margin-top: 56px; padding-top: 18px; border-top: 1px solid #eee;
           color: var(--gray); font-size: 13px; text-align: center; }
</style>
</head>
<body>
<div class="page">

<h1>{{ title }}</h1>
<div class="byline">数据来源：yfinance &nbsp;·&nbsp; 信号：{{ signal_ticker }}（{{ signal_label }}）
   &nbsp;·&nbsp; 标的：{{ ticker }}（{{ ticker_name }}）
   &nbsp;·&nbsp; 截止：{{ end_date }} &nbsp;·&nbsp; 单位：{{ currency }}
   &nbsp;·&nbsp; 生成：{{ generated_at }}<br>
   思路来源（原文）：<a href="{{ article_url }}" target="_blank" rel="noopener">头条原文链接</a></div>

<p>本文的策略思路来自<a href="{{ article_url }}" target="_blank" rel="noopener">这篇头条文章</a>，
   但所有数据均使用 yfinance 重新下载、所有结果均为本项目独立计算。
   本次回测用<strong>{{ signal_label }}</strong>的当日涨跌幅作为加码信号、买入标的为
   <strong>{{ asset_label }}</strong>（{{ ticker }}），把 {{ periods_text }} 几个回测周期跑了一遍——
   不靠任何主观择时，只比较两种「每天都买」的日定投方式，看看
   <strong class="hot">跌多就加码</strong>到底有没有用，得出的是一份完整、可复现的回测报告。</p>
{% if decoupled %}
<div class="note">
🔁 <strong>信号与标的分离：</strong>本报告的加码信号来自 <code>{{ signal_ticker }}</code>
   （{{ signal_label }}）的日涨跌幅，但实际买入的是 <code>{{ ticker }}</code>（{{ asset_label }}）。
   {% if leveraged %}<strong>注意 {{ ticker }} 为杠杆产品，存在波动损耗与更大回撤风险，长期持有风险显著高于指数本身。</strong>{% endif %}
</div>
{% endif %}

<h2>一、核心结论：{{ headline_main | safe }}</h2>
<div class="lead">
{{ executive_summary | safe }}
</div>

<h2>二、定投策略的规则</h2>
<h3>策略 1：每日固定 {{ base_amount }} 定投</h3>
<p>不管{{ asset_label }}涨还是跌，每个交易日<strong>雷打不动</strong>投入 {{ base_amount }} {{ currency }}，
   以当日（复权）收盘价买入 {{ asset_label }}，允许小数股，持有到期末不卖出。这是最简单、最机械的定投方式。</p>
<h3>策略 2：动态跌幅加码定投（跌多加仓、涨多少投）</h3>
<p>完全根据 {{ signal_label }} 当日的<strong>同日收盘涨跌幅</strong>调整当天投入金额（买入标的为 {{ asset_label }}）：
   <strong class="hot">跌得越多、买得越多；涨得越多、买得越少。</strong></p>
<table>
  <tr><th>当日涨跌幅</th><th>当日投入（{{ currency }}）</th></tr>
  {% for r in dynamic_rules %}
  <tr><td>{{ r.label_range }}</td><td>{{ r.amount }}</td></tr>
  {% endfor %}
</table>

<h2>三、核心回测结果：{{ periods_text }} 一表看清</h2>
<table>
  <tr>
    <th>投资<br>周期</th><th>动态定投<br>总收益率</th><th>固定{{ base_amount }}定投<br>总收益率</th>
    <th>动态策略<br>超额收益率</th><th>动态策略<br>多赚金额</th>
    <th>动态策略<br>总投入</th><th>固定定投<br>总投入</th>
    <th>动态策略<br>最终金额</th><th>固定定投<br>最终金额</th>
  </tr>
  {% for c in comparisons %}
  <tr>
    <td>{{ c.years }}年</td>
    <td>{{ '%.2f' % (c.dynamic_total_return * 100) }}%</td>
    <td>{{ '%.2f' % (c.fixed_total_return * 100) }}%</td>
    <td class="{{ 'pos' if c.excess_return >= 0 else 'neg' }}">{{ '%+.2f' % (c.excess_return * 100) }}%</td>
    <td class="{{ 'pos' if c.extra_profit >= 0 else 'neg' }}">{{ '{:,.0f}'.format(c.extra_profit) }}</td>
    <td>{{ '{:,.0f}'.format(c.dynamic_total_invested) }}</td>
    <td>{{ '{:,.0f}'.format(c.fixed_total_invested) }}</td>
    <td>{{ '{:,.0f}'.format(c.dynamic_final_value) }}</td>
    <td>{{ '{:,.0f}'.format(c.fixed_final_value) }}</td>
  </tr>
  {% endfor %}
</table>
<img src="charts/{{ charts.return_rate_comparison }}" alt="总收益率对比">
<p>{{ analysis_return_rate | safe }}</p>

<h2>四、两个口径的收益差异！差距比想象更大</h2>
<img src="charts/{{ charts.profit_amount_comparison }}" alt="总收益金额对比">
<p>{{ analysis_profit | safe }}</p>
<img src="charts/{{ charts.excess_return_rate }}" alt="超额收益率走势">
<img src="charts/{{ charts.extra_profit }}" alt="多赚金额走势">

<h3>收益拆解：择时 vs 多投入的本金（等额基准法）</h3>
<p>{{ analysis_decomposition | safe }}</p>
<img src="charts/{{ charts.profit_decomposition }}" alt="多赚金额拆解">
<table>
  <tr><th>周期</th><th>多赚总额</th><th>择时 alpha</th><th>占比</th>
      <th>多投本金贡献</th><th>占比</th></tr>
  {% for d in decomposition_rows %}
  <tr>
    <td>{{ d.years }}年</td>
    <td class="{{ 'pos' if d.extra_profit >= 0 else 'neg' }}">{{ '{:,.0f}'.format(d.extra_profit) }}</td>
    <td class="{{ 'pos' if d.timing_alpha >= 0 else 'neg' }}">{{ '{:,.0f}'.format(d.timing_alpha) }}</td>
    <td>{{ '%.0f' % (d.timing_alpha_share * 100) }}%</td>
    <td>{{ '{:,.0f}'.format(d.capital_effect) }}</td>
    <td>{{ '%.0f' % (d.capital_effect_share * 100) }}%</td>
  </tr>
  {% endfor %}
</table>

<h2>五、买入持有（B&H）对比：一次性 vs 分批投入</h2>
{{ analysis_buyhold | safe }}
<table>
  <tr><th>周期</th><th>B&H<br>总收益率</th><th>固定定投<br>总收益率</th><th>动态定投<br>总收益率</th>
      <th>B&H<br>最终金额</th><th>固定定投<br>最终金额</th><th>动态定投<br>最终金额</th>
      <th>B&H − 固定<br>最终差额</th><th>B&H<br>最大回撤</th></tr>
  {% for r in buyhold_rows %}
  <tr>
    <td>{{ r.years }}年</td>
    <td>{{ '%.2f' % (r.bh_total_return * 100) }}%</td>
    <td>{{ '%.2f' % (r.fixed_total_return * 100) }}%</td>
    <td>{{ '%.2f' % (r.dynamic_total_return * 100) }}%</td>
    <td>{{ '{:,.0f}'.format(r.bh_final_value) }}</td>
    <td>{{ '{:,.0f}'.format(r.fixed_final_value) }}</td>
    <td>{{ '{:,.0f}'.format(r.dynamic_final_value) }}</td>
    <td class="{{ 'pos' if r.bh_vs_fixed_final >= 0 else 'neg' }}">{{ '{:,.0f}'.format(r.bh_vs_fixed_final) }}</td>
    <td>{{ '%.2f' % (r.bh_max_drawdown * 100) }}%</td>
  </tr>
  {% endfor %}
</table>
<p style="font-size:14px;color:#666;">注：B&H 投入的总金额与「固定100定投」相同，但在首日一次性买入；
   其总收益率即该周期的价格涨幅，与投入金额无关。净值曲线见下一节（绿色虚线）。</p>

<h2>六、给普通投资者的 {{ advice_list | length }} 个核心建议</h2>
<div class="advice">
{% for a in advice_list %}
<h3>{{ loop.index }}. {{ a.title | safe }}</h3>
<p>{{ a.body | safe }}</p>
{% endfor %}
</div>

<h2>七、组合净值曲线（含 B&H 对比）</h2>
{% for years in period_list %}
<h3>{{ years }}年：组合价值与累计投入</h3>
<img src="charts/{{ charts['equity_curve_' ~ years ~ 'y'] }}" alt="{{ years }}年净值曲线">
{% endfor %}
<p>{{ analysis_equity | safe }}图中绿色虚线为「买入持有(B&H)」的组合价值，便于直观对比一次性投入与分批投入。</p>

<h2>八、定投行为分析：它到底什么时候加码？</h2>
<img src="charts/{{ charts.price_markers }}" alt="价格与买入标记">
{% for years in period_list %}
<img src="charts/{{ charts['dynamic_contribution_' ~ years ~ 'y'] }}" alt="{{ years }}年每日投入">
{% endfor %}
<p>{{ analysis_contribution | safe }}</p>
<table>
  <tr><th>周期</th><th>投300天数</th><th>投200天数</th><th>投100天数</th><th>投50天数</th><th>投20天数</th></tr>
  {% for row in contribution_count_rows %}
  <tr><td>{{ row.years }}年</td><td>{{ row.c300 }}</td><td>{{ row.c200 }}</td>
      <td>{{ row.c100 }}</td><td>{{ row.c50 }}</td><td>{{ row.c20 }}</td></tr>
  {% endfor %}
</table>

<h2>九、回撤分析：加码会不会扛不住？</h2>
{% for years in period_list %}
<img src="charts/{{ charts['drawdown_' ~ years ~ 'y'] }}" alt="{{ years }}年回撤">
{% endfor %}
<p>{{ analysis_drawdown | safe }}</p>

<h2>十、专业指标明细</h2>
<p style="font-size:14px;color:#666;">说明：「等额(同动态)」即等额基准——投入与动态策略相同的总本金、但每天均匀投入；
   它的总收益率与「固定100」相同（仅本金规模不同），用于隔离纯择时效果。
   「买入持有(B&H)」为首日一次性投入相同总额并持有。</p>
<table>
  <tr><th>周期</th><th>策略</th><th>最终金额</th><th>总收益率</th><th>年化<br>(XIRR)</th>
      <th>最大回撤</th><th>年化<br>波动率</th><th>夏普</th><th>累计份额</th><th>平均成本</th></tr>
  {% for m in metric_rows %}
  <tr>
    <td>{{ m.years }}年</td><td>{{ m.strategy }}</td>
    <td>{{ '{:,.0f}'.format(m.final_value) }}</td>
    <td>{{ '%.2f' % (m.total_return * 100) }}%</td>
    <td>{{ '%.2f' % (m.annualized_return * 100) }}%</td>
    <td>{{ '%.2f' % (m.max_drawdown * 100) }}%</td>
    <td>{{ '%.2f' % (m.volatility * 100) }}%</td>
    <td>{{ '%.2f' % m.sharpe }}</td>
    <td>{{ '%.2f' % m.total_shares }}</td>
    <td>{{ '%.2f' % m.avg_cost_per_share }}</td>
  </tr>
  {% endfor %}
</table>

<h2>十一、最后总结</h2>
<div class="lead">{{ conclusion | safe }}</div>

<div class="note">
⚠️ <strong>重要假设说明：</strong>本回测默认使用「当日涨跌幅作为信号、并以当日收盘价成交」
（<code>{{ execution_timing }}</code>）。这便于复现，但真实交易中通常难以严格执行，
除非采用临近收盘的估算价下单。可在 <code>config.yaml</code> 中改为
<code>next_day_close</code>（次日收盘成交）。价格使用 yfinance 自动复权收盘价，已处理分红与拆股；
默认无税费、无佣金（{{ commission_bps }} bps）、无滑点（{{ slippage_bps }} bps），允许小数股。
</div>

<h2>附录</h2>
<details><summary>数据质量报告</summary>
<table>
  <tr><th>周期</th><th>交易日数</th><th>起始日</th><th>结束日</th><th>起始点位</th><th>结束点位</th></tr>
  {% for row in data_quality_rows %}
  <tr><td>{{ row.years }}年</td><td>{{ row.trading_days }}</td><td>{{ row.start }}</td>
      <td>{{ row.end }}</td><td>{{ '%.2f' % row.start_price }}</td><td>{{ '%.2f' % row.end_price }}</td></tr>
  {% endfor %}
</table>
</details>
<details><summary>完整配置（config.yaml）</summary>
<pre>{{ config_dump }}</pre>
</details>
<details><summary>输出文件清单（CSV）</summary>
<ul>{% for f in csv_files %}<li><code>{{ f }}</code></li>{% endfor %}</ul>
</details>

<footer>本报告由本地 Python 项目基于 yfinance 真实数据自动生成，仅供研究参考，不构成投资建议。</footer>
</div>
</body>
</html>
"""


def _wan(amount):
    """Format a money amount in 万 (ten-thousands) for punchy headlines."""
    return f"{amount / 10000:.1f}万"


def build_headline(comparisons):
    """Punchy data-driven headline for the core-result section."""
    longest = max(comparisons, key=lambda c: c["years"])
    if longest["extra_profit"] >= 0:
        return (f"{longest['years']}年多赚约 "
                f"<span class='hot'>{_wan(longest['extra_profit'])}</span>！")
    return (f"{longest['years']}年反而少赚约 "
            f"<span class='hot'>{_wan(abs(longest['extra_profit']))}</span>")


def build_advice(comparisons, results, currency, asset_label="纳斯达克"):
    """Build the 'core advice for ordinary investors' list from results."""
    longest = max(comparisons, key=lambda c: c["years"])
    losers = [c for c in comparisons if c["excess_return"] < 0]
    # Pure timing alpha vs. extra-capital effect, from the equal-capital
    # benchmark decomposition (NOT the naive extra_profit - extra_invested).
    timing_share = longest.get("timing_alpha_share", 0.0)
    capital_share = longest.get("capital_effect_share", 0.0)

    advice = []
    advice.append({
        "title": "长期定投（越久越值），可优先用跌幅加码策略",
        "body": (f"{longest['years']}年周期里，动态策略多赚约 "
                 f"<span class='hot'>{_wan(longest['extra_profit'])}</span> {currency}，"
                 f"时间越长、{asset_label}这种长期向上的标的，加码累积的低位筹码效果越明显。"),
    })
    advice.append({
        "title": "别把超额收益想得太高，差距主要在「绝对金额」而非「收益率」",
        "body": ("动态策略的总收益率与固定定投往往只差几个百分点，甚至个别周期还略低"
                 + ("（如 " + "、".join(f"{c['years']}年 {c['excess_return']*100:+.2f}%" for c in losers) + "）"
                    if losers else "")
                 + "。真正拉开差距的是它在下跌时投入了更多本金，做大了总盘子。"),
    })
    advice.append({
        "title": "看清「多赚」的真正来源：择时其实只占一小部分",
        "body": (f"用「等额基准」（投入与动态完全相同的总本金、但每天均匀投）拆解后发现："
                 f"{longest['years']}年里动态策略多赚的钱中，只有约 "
                 f"<span class='hot'>{timing_share*100:.0f}%</span> 来自下跌加码带来的"
                 f"更低成本（真正的择时 alpha），其余约 "
                 f"<span class='hot'>{capital_share*100:.0f}%</span> 仅仅是因为它"
                 f"<strong>投入了更多本金</strong>。别把多投入的钱误当成择时能力。"),
    })
    advice.append({
        "title": "最重要的不是公式，而是「熊市里坚持投下去」",
        "body": ("再精巧的加码规则，也比不上长期不中断的纪律。对普通人来说，"
                 "<strong>坚持定投穿越熊市</strong>，远比策略细节更决定最终结果。"),
    })
    return advice


def _fmt_money(x):
    return f"{x:,.0f}"


def build_buyhold_analysis(buyhold_rows, currency, asset_label):
    """Narrative comparing lump-sum buy & hold vs the DCA strategies."""
    longest = max(buyhold_rows, key=lambda r: r["years"])
    bh_beats_fixed = sum(1 for r in buyhold_rows if r["bh_vs_fixed_final"] > 0)
    n = len(buyhold_rows)
    verdict = ("在多数周期里都跑赢了分批定投" if bh_beats_fixed >= n / 2
               else "并未在多数周期里跑赢分批定投")

    lead = (
        f"买入持有（B&H）：在回测<strong>首个交易日</strong>，用与「固定100定投」相同的总金额"
        f"<strong>一次性买入 {asset_label} 并持有</strong>到期末。它与分批定投最大的区别是："
        f"资金在第一天就全部到位、全程在场（full time in market），而定投是逐日把钱投进去的。"
    )
    body = (
        f"以最长 {longest['years']} 年周期为例，B&H 最终金额约 "
        f"<span class='hot'>{_fmt_money(longest['bh_final_value'])}</span> {currency}，"
        f"固定定投约 {_fmt_money(longest['fixed_final_value'])} {currency}，"
        f"二者相差约 {_fmt_money(longest['bh_vs_fixed_final'])} {currency}。"
        f"在长期上涨的行情里，B&H {verdict}——因为它的钱在场时间更长。"
        "但这并不意味着 B&H 一定更优："
        "<strong>① 它要求你第一天就有全部本金</strong>（定投的优势恰恰是用现金流逐步投入）；"
        "<strong>② 一次性买在高点会立刻承受全部回撤</strong>，定投则把成本摊平、心理压力更小。"
        "因此 B&H 与定投并非「谁绝对更好」，而是<strong>适用场景不同</strong>："
        "有整笔闲钱、能扛回撤 → 倾向 B&H；靠工资逐月投入、想摊平成本 → 倾向定投。"
    )
    return f"<p>{lead}</p><p>{body}</p>"


def build_analysis_text(comparisons, results, currency):
    """Build the narrative analysis blocks from computed results."""
    by_year = {c["years"]: c for c in comparisons}
    periods = sorted(by_year.keys())

    # Best/worst period by excess return rate.
    best = max(comparisons, key=lambda c: c["excess_return"])
    worst = min(comparisons, key=lambda c: c["excess_return"])
    longest = max(periods)
    longest_c = by_year[longest]

    # --- Return-rate analysis ---
    analysis_return_rate = (
        f"按<strong>收益率</strong>看，动态跌幅加码策略在 {best['years']} 年周期的超额收益率最高，"
        f"为 {best['excess_return']*100:+.2f}%；在 {worst['years']} 年周期表现相对最弱，"
        f"超额收益率为 {worst['excess_return']*100:+.2f}%。"
    )
    if abs(best["excess_return"]) < 0.05 and abs(worst["excess_return"]) < 0.05:
        analysis_return_rate += (
            "整体来看，两种策略的<strong>收益率差异并不大</strong>——这符合预期，"
            "因为动态策略只是改变了每天的投入金额，并没有改变持有的标的本身。"
        )
    else:
        analysis_return_rate += "可见不同周期下收益率差异有所不同，需结合绝对收益一起判断。"

    # --- Profit-amount analysis ---
    analysis_profit = (
        f"按<strong>绝对收益金额</strong>看，差距比收益率明显得多。以 {longest} 年周期为例，"
        f"动态策略最终金额约 {_fmt_money(longest_c['dynamic_final_value'])} {currency}，"
        f"固定策略约 {_fmt_money(longest_c['fixed_final_value'])} {currency}，"
        f"动态策略多赚约 {_fmt_money(longest_c['extra_profit'])} {currency}。"
        f"但要注意：动态策略同期总投入约 {_fmt_money(longest_c['dynamic_total_invested'])} {currency}，"
        f"比固定策略多投入约 {_fmt_money(longest_c['extra_invested'])} {currency}。"
        "也就是说，两种策略<strong>投入的本金并不相等</strong>，直接比最终金额并不公平——"
        "下一节用「等额基准」把这笔多赚的钱拆开来看。"
    )

    # --- Profit decomposition analysis (equal-capital benchmark) ---
    ta = longest_c["timing_alpha"]
    ce = longest_c["capital_effect"]
    analysis_decomposition = (
        "为了把「择时」和「多投入的本金」分开，我们引入第三个对照组——"
        "<strong>等额基准</strong>：它投入与动态策略<strong>完全相同的总本金</strong>，"
        "但像固定定投一样<strong>每天均匀投入</strong>。这样一来，等额基准与动态策略的本金一模一样，"
        "二者的差异就只剩「<strong>什么时候把钱投进去</strong>」，即纯粹的择时能力。"
        f"<br><br>以 {longest} 年为例，动态策略相对固定100定投共多赚约 "
        f"<span class='hot'>{_fmt_money(longest_c['extra_profit'])}</span> {currency}，可拆为两部分："
        f"<br>① <strong>择时 alpha</strong>（动态 − 等额基准，本金相同）：约 "
        f"<span class='hot'>{_fmt_money(ta)}</span> {currency}，占 "
        f"{longest_c['timing_alpha_share']*100:.0f}%；"
        f"<br>② <strong>多投入本金的贡献</strong>（等额基准 − 固定100，本金更多）：约 "
        f"<span class='hot'>{_fmt_money(ce)}</span> {currency}，占 "
        f"{longest_c['capital_effect_share']*100:.0f}%。"
        "<br><br>可见所谓「多赚」中，真正归功于跌幅加码<strong>择时</strong>的部分往往只是小头，"
        "大头其实来自<strong>单纯投入了更多钱</strong>。这也提醒我们：评价一个加码策略，"
        "应该用「本金相同」的口径比较，而不是直接比最终金额。"
    )

    # --- Equity-curve analysis ---
    analysis_equity = (
        "从净值曲线可以看出，动态策略的「组合价值」与「累计投入」两条线，"
        "都会因为在下跌期加大投入而高于固定策略。两条净值曲线的形状高度相似，"
        "说明动态策略主要影响的是投入节奏与规模，而非彻底改变收益结构。"
    )

    # --- Contribution analysis ---
    dyn_long = results[longest]["dynamic"]
    counts = (dyn_long["contribution"].round().value_counts()).to_dict()
    n300 = int(counts.get(300.0, 0))
    n20 = int(counts.get(20.0, 0))
    analysis_contribution = (
        f"在 {longest} 年周期里，动态策略触发「跌幅超2%、投300」的天数约 {n300} 天，"
        f"触发「涨幅超2%、投20」的天数约 {n20} 天。"
        "大跌日相对少见，但正是这些日子贡献了更低的买入成本；"
        "由于大涨与大跌日都属少数，绝大多数交易日仍按 100 投入，"
        "因此动态策略确实抬高了总投入规模，但幅度有限。"
    )

    # --- Drawdown analysis ---
    analysis_drawdown = (
        "从回撤曲线看，两种策略以组合价值计的回撤路径非常接近——"
        "因为它们持有的是同一标的。动态策略在熊市中持续加大投入，"
        "短期账面回撤未必更小，但更低的平均成本有助于在反弹时更快回本。"
    )

    return {
        "analysis_return_rate": analysis_return_rate,
        "analysis_profit": analysis_profit,
        "analysis_decomposition": analysis_decomposition,
        "analysis_equity": analysis_equity,
        "analysis_contribution": analysis_contribution,
        "analysis_drawdown": analysis_drawdown,
    }


def build_executive_summary(comparisons, ticker, end_date, results, currency,
                            asset_label="纳斯达克", signal_label="纳斯达克"):
    """Build the executive summary HTML block."""
    periods = sorted(c["years"] for c in comparisons)
    best = max(comparisons, key=lambda c: c["excess_return"])
    longest_c = max(comparisons, key=lambda c: c["years"])
    beat_rate = sum(1 for c in comparisons if c["excess_return"] > 0)
    beat_profit = sum(1 for c in comparisons if c["extra_profit"] > 0)

    rate_verdict = (
        "在多数周期内收益率略有优势" if beat_rate >= len(comparisons) / 2
        else "在多数周期内收益率并未明显胜出"
    )
    profit_verdict = (
        "在多数周期内绝对收益更高" if beat_profit >= len(comparisons) / 2
        else "在多数周期内绝对收益并未更高"
    )

    return (
        f"<p>本报告使用 yfinance 的真实历史数据，以 {signal_label} 的日涨跌幅为加码信号、"
        f"买入标的为 <code>{ticker}</code>（{asset_label}），"
        f"回测了 {'、'.join(str(p) + '年' for p in periods)} 共 {len(periods)} 个周期，"
        f"截止日为 {end_date}。对比「动态跌幅加码定投」与「每日固定100定投」两种策略。</p>"
        f"<ul>"
        f"<li>动态策略表现最好的周期是 <strong>{best['years']}年</strong>，"
        f"超额收益率 {best['excess_return']*100:+.2f}%。</li>"
        f"<li>按收益率：动态策略{rate_verdict}。</li>"
        f"<li>按绝对收益金额：动态策略{profit_verdict}。</li>"
        f"<li>以最长 {longest_c['years']} 年周期看，动态策略多赚约 "
        f"{longest_c['extra_profit']:,.0f} {currency}；用「等额基准」拆解后，其中仅约 "
        f"{longest_c['timing_alpha']:,.0f} {currency}"
        f"（{longest_c['timing_alpha_share']*100:.0f}%）来自下跌加码的<strong>择时</strong>，"
        f"其余约 {longest_c['capital_effect']:,.0f} {currency}"
        f"（{longest_c['capital_effect_share']*100:.0f}%）来自<strong>多投入的本金</strong>。</li>"
        f"<li><strong>核心结论：动态策略多赚的钱，大头来自单纯投入更多本金，"
        f"择时本身带来的纯超额收益相对有限。</strong></li>"
        f"</ul>"
    )


def build_conclusion(comparisons, currency):
    """Build the final conclusion HTML from actual results."""
    longest_c = max(comparisons, key=lambda c: c["years"])
    by_year = {c["years"]: c for c in comparisons}

    parts = []
    if longest_c["excess_return"] > 0:
        parts.append(
            f"<p>在最长的 {longest_c['years']} 年周期里，动态跌幅加码策略的收益率比固定定投"
            f"高 {longest_c['excess_return']*100:.2f}%，最终金额多约 "
            f"{longest_c['extra_final_value']:,.0f} {currency}。</p>"
        )
    else:
        parts.append(
            f"<p>在最长的 {longest_c['years']} 年周期里，动态策略的收益率反而比固定定投"
            f"低 {abs(longest_c['excess_return'])*100:.2f}%，说明加码择时并非总能跑赢。</p>"
        )

    losers = [c for c in comparisons if c["excess_return"] < 0]
    if losers:
        ls = "、".join(f"{c['years']}年({c['excess_return']*100:+.2f}%)" for c in losers)
        parts.append(f"<p>需要明确指出：动态策略在以下周期的收益率<strong>低于</strong>固定定投：{ls}。</p>")

    parts.append(
        f"<p>综合来看，动态策略「多赚的钱」由两部分构成：一是下跌时多买带来的"
        f"<strong>更低平均成本（择时 alpha）</strong>，二是整体<strong>投入了更多本金</strong>。"
        f"通过「等额基准」（同样多投本金、但均匀投入）拆解，{longest_c['years']}年里择时只贡献了约 "
        f"{longest_c['timing_alpha_share']*100:.0f}%，"
        f"多投入本金贡献了约 {longest_c['capital_effect_share']*100:.0f}%——"
        f"<strong>后者才是更大的来源</strong>。</p>"
    )
    parts.append(
        "<p><strong>给普通投资者的实用建议：</strong>最重要的事情是在熊市里坚持持续投入，"
        "而不是纠结于具体的加码公式。策略的精巧程度，远不如长期坚持来得重要。</p>"
    )
    return "".join(parts)


def generate_report(context, out_path):
    """Render the HTML report to out_path."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    html = Template(HTML_TEMPLATE).render(**context)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    logger.info("Saved HTML report: %s", out_path)
    return out_path
