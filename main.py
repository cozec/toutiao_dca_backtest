"""Orchestrate the Nasdaq dynamic DCA backtest end to end.

Run with:  python main.py

Downloads fresh yfinance data, backtests fixed-100 daily DCA vs dynamic
dip-buying DCA over the configured periods, writes CSV tables and charts, and
generates results/report.html.
"""

import logging
import os
import shutil
from datetime import datetime
from functools import partial

import pandas as pd
import yaml

from src import backtest, data_loader, metrics, plots, report
from src.strategies import dynamic_daily_dca_amount, fixed_daily_dca_amount
from src.utils import ensure_dirs, load_config, project_path, setup_logging

ARTICLE_URL = (
    "https://www.toutiao.com/article/7646398901649441314/"
    "?app=news_article&category_new=__all__&module_name=iOS_tt_others"
    "&req_id_new=202606140422425B466B585F97453348F2"
    "&share_did=MS4wLjACAAAA1iChiRlAp17J_0Afz1ZLL2QPOFf3to05sthA82a5zF4"
    "&share_token=f0d7ddf4-6765-11f1-b20b-00163e056d31"
    "&share_uid=MS4wLjABAAAATT9aCUOj3uCkHZKubrocEQ49I-HmhBgq3IKHchgr0o4"
    "&timestamp=1781382295&tt_from=sys_share&upstream_biz=iOS_others"
    "&utm_campaign=client_share&utm_medium=toutiao_ios&utm_source=sys_share"
    "&source=m_redirect"
)

TICKER_NAMES = {
    "^IXIC": "纳斯达克综合指数",
    "QQQ": "纳斯达克100 ETF",
    "SPY": "标普500 ETF",
    "TQQQ": "纳斯达克100三倍做多 ETF",
}


def main():
    config = load_config()
    logger = setup_logging(project_path("logs", "backtest.log"))

    ticker = config["ticker"]
    currency = config["currency_label"]
    base_amount = config["base_daily_amount"]
    periods = sorted(config["periods_years"])
    rules = config["dynamic_dca_rules"]
    rf = config["risk_free_rate"]
    exec_timing = config["execution_timing"]
    allow_frac = config["allow_fractional_shares"]
    commission_bps = config["commission_bps"]
    slippage_bps = config["slippage_bps"]

    charts_dir = project_path("results", "charts")
    tables_dir = project_path("results", "tables")
    ensure_dirs(charts_dir, tables_dir, project_path("data", "raw"),
                project_path("data", "processed"))

    # --- 1. Download enough history to cover the longest period (+ buffer). ---
    max_years = max(periods)
    start_dl = (pd.Timestamp.today() - pd.DateOffset(years=max_years + 1)
                ).strftime("%Y-%m-%d")
    raw = data_loader.download_yfinance_data(ticker, start_dl, config["end_date"])
    raw.to_csv(project_path("data", "raw", f"{ticker.replace('^', '')}_raw.csv"))

    price = data_loader.clean_price_data(raw)
    price.to_csv(project_path("data", "processed", f"{ticker.replace('^', '')}_clean.csv"))

    end_date = price.index.max()
    earliest = price.index.min()
    logger.info("Data ready: %s rows, %s to %s",
                len(price), earliest.date(), end_date.date())

    # Drop periods we cannot cover and warn.
    available_periods = []
    for y in periods:
        need_start = end_date - pd.DateOffset(years=y)
        if need_start < earliest:
            logger.warning("Not enough data for %d-year period (need from %s, "
                           "have from %s) -- skipping.", y, need_start.date(),
                           earliest.date())
        else:
            available_periods.append(y)
    if not available_periods:
        raise RuntimeError("No requested period can be covered by the data.")
    periods = available_periods

    # --- 2. Backtest each period for both strategies. ---
    fixed_fn = partial(fixed_daily_dca_amount, amount=base_amount)
    dynamic_fn = partial(dynamic_daily_dca_amount, rules=rules)

    results = {}        # years -> {"dynamic", "fixed", "equalcap"} equity curves
    metrics_all = {}    # years -> {"dynamic", "fixed", "equalcap"} metric dicts
    comparisons = []

    for y in periods:
        pdata = data_loader.get_period_data(price, y, end_date)

        dyn_ec = backtest.run_dca_backtest(
            pdata, dynamic_fn, exec_timing, allow_frac, commission_bps, slippage_bps)
        fix_ec = backtest.run_dca_backtest(
            pdata, fixed_fn, exec_timing, allow_frac, commission_bps, slippage_bps)

        dyn_m = metrics.calculate_summary_metrics(dyn_ec, risk_free_rate=rf)
        fix_m = metrics.calculate_summary_metrics(fix_ec, risk_free_rate=rf)

        # Equal-capital benchmark: deploy the SAME total capital as the dynamic
        # strategy, but spread evenly over every contributing day. This isolates
        # pure timing alpha from the effect of simply investing more money.
        n_exec = int((dyn_ec["contribution"] > 0).sum())
        equalcap_amount = dyn_m["total_invested"] / n_exec if n_exec else base_amount
        equalcap_fn = partial(fixed_daily_dca_amount, amount=equalcap_amount)
        eq_ec = backtest.run_dca_backtest(
            pdata, equalcap_fn, exec_timing, allow_frac, commission_bps, slippage_bps)
        eq_m = metrics.calculate_summary_metrics(eq_ec, risk_free_rate=rf)

        comp = metrics.calculate_period_comparison(dyn_m, fix_m, y, equalcap_metrics=eq_m)

        results[y] = {"dynamic": dyn_ec, "fixed": fix_ec, "equalcap": eq_ec}
        metrics_all[y] = {"dynamic": dyn_m, "fixed": fix_m, "equalcap": eq_m}
        comparisons.append(comp)

        # Per-period trade logs.
        dyn_ec.to_csv(project_path("results", "tables", f"trade_log_dynamic_{y}y.csv"))
        fix_ec.to_csv(project_path("results", "tables", f"trade_log_fixed_{y}y.csv"))

    comparisons.sort(key=lambda c: c["years"])

    # --- 3. Write CSV tables. ---
    _write_csv_tables(results, metrics_all, comparisons, tables_dir)

    # --- 4. Charts. ---
    chart_paths = plots.generate_all_charts(results, comparisons, currency, charts_dir)

    # --- 5. HTML report. ---
    _build_and_write_report(config, ticker, currency, base_amount, end_date,
                            earliest, periods, rules, comparisons, results,
                            metrics_all, chart_paths, exec_timing,
                            commission_bps, slippage_bps)

    # --- 6. Publish a static page (docs/) for GitHub Pages. ---
    _publish_to_docs()

    # --- 7. Console summary. ---
    _print_console_summary(ticker, end_date, earliest, comparisons, currency)


def _publish_to_docs():
    """Copy the report + charts into docs/ as a static GitHub Pages site.

    GitHub Pages can serve from the /docs folder on the main branch. The report
    references charts via the relative path "charts/...", so copying report.html
    to docs/index.html and the charts to docs/charts/ keeps all images working.
    """
    docs = project_path("docs")
    docs_charts = project_path("docs", "charts")
    ensure_dirs(docs_charts)
    shutil.copyfile(project_path("results", "report.html"),
                    project_path("docs", "index.html"))
    for png in sorted(os.listdir(project_path("results", "charts"))):
        if png.endswith(".png"):
            shutil.copyfile(project_path("results", "charts", png),
                            os.path.join(docs_charts, png))
    logging.getLogger("nasdaq_dca").info("Published static site: %s", docs)


def _write_csv_tables(results, metrics_all, comparisons, tables_dir):
    """Write summary, per-strategy metrics, data-quality, and equity-curve CSVs."""
    # Summary comparison.
    pd.DataFrame(comparisons).to_csv(
        project_path("results", "tables", "summary_comparison.csv"), index=False)

    # Per-strategy metrics (one row per period).
    for strat in ("dynamic", "fixed", "equalcap"):
        rows = []
        for y, m in metrics_all.items():
            row = {k: v for k, v in m[strat].items() if k != "contribution_counts"}
            row["years"] = y
            row.update({f"days_{amt}": cnt
                        for amt, cnt in m[strat]["contribution_counts"].items()})
            rows.append(row)
        pd.DataFrame(rows).sort_values("years").to_csv(
            project_path("results", "tables", f"metrics_{strat}.csv"), index=False)

    # Data quality report.
    dq = []
    for y, res in results.items():
        ec = res["dynamic"]
        dq.append({
            "years": y, "trading_days": len(ec),
            "start": ec.index.min().date(), "end": ec.index.max().date(),
            "start_price": ec["close"].iloc[0], "end_price": ec["close"].iloc[-1],
            "missing_days": int(ec["close"].isna().sum()),
        })
    pd.DataFrame(dq).sort_values("years").to_csv(
        project_path("results", "tables", "data_quality_report.csv"), index=False)

    # Combined equity curves (long format).
    for strat in ("dynamic", "fixed", "equalcap"):
        frames = []
        for y, res in results.items():
            f = res[strat][["portfolio_value", "cumulative_invested", "profit"]].copy()
            f["years"] = y
            frames.append(f)
        pd.concat(frames).to_csv(project_path("results", f"equity_curves_{strat}.csv"))


def _build_and_write_report(config, ticker, currency, base_amount, end_date,
                            earliest, periods, rules, comparisons, results,
                            metrics_all, chart_paths, exec_timing,
                            commission_bps, slippage_bps):
    """Assemble the Jinja2 context and render the HTML report."""
    # Dynamic rule table rows (human-readable ranges).
    rule_rows = []
    for r in rules:
        lo, hi = r.get("min_return"), r.get("max_return")
        if lo is None:
            rng = f"跌幅超过 {abs(hi)*100:.0f}%"
        elif hi is None:
            rng = f"涨幅超过 {lo*100:.0f}%"
        elif lo < 0 and hi <= 0:
            rng = f"跌幅 {abs(hi)*100:.0f}%–{abs(lo)*100:.0f}%"
        elif lo < 0 <= hi:
            rng = f"涨跌幅 {lo*100:.0f}% 到 +{hi*100:.0f}%"
        else:
            rng = f"涨幅 {lo*100:.0f}%–{hi*100:.0f}%"
        rule_rows.append({"label_range": rng, "amount": r["amount"]})

    # Detailed metric rows.
    metric_rows = []
    for y in periods:
        for strat, name in (("dynamic", "动态"), ("fixed", "固定100"),
                            ("equalcap", "等额(同动态)")):
            m = metrics_all[y][strat]
            metric_rows.append({
                "years": y, "strategy": name,
                "final_value": m["final_value"], "total_return": m["total_return"],
                "annualized_return": m["annualized_return"],
                "max_drawdown": m["max_drawdown"], "volatility": m["volatility"],
                "sharpe": m["sharpe"], "total_shares": m["total_shares"],
                "avg_cost_per_share": m["avg_cost_per_share"],
            })

    # Profit-decomposition rows: extra profit = timing alpha + capital effect.
    decomposition_rows = []
    for c in comparisons:
        decomposition_rows.append({
            "years": c["years"],
            "extra_profit": c["extra_profit"],
            "timing_alpha": c["timing_alpha"],
            "capital_effect": c["capital_effect"],
            "timing_alpha_share": c["timing_alpha_share"],
            "capital_effect_share": c["capital_effect_share"],
        })

    # Contribution count rows (dynamic strategy).
    contribution_count_rows = []
    for y in periods:
        c = metrics_all[y]["dynamic"]["contribution_counts"]
        contribution_count_rows.append({
            "years": y, "c300": c.get(300, 0), "c200": c.get(200, 0),
            "c100": c.get(100, 0), "c50": c.get(50, 0), "c20": c.get(20, 0),
        })

    # Data quality rows.
    data_quality_rows = []
    for y in periods:
        ec = results[y]["dynamic"]
        data_quality_rows.append({
            "years": y, "trading_days": len(ec),
            "start": ec.index.min().date(), "end": ec.index.max().date(),
            "start_price": ec["close"].iloc[0], "end_price": ec["close"].iloc[-1],
        })

    analysis = report.build_analysis_text(comparisons, results, currency)
    exec_summary = report.build_executive_summary(
        comparisons, ticker, end_date.date(), results, currency)
    conclusion = report.build_conclusion(comparisons, currency)
    headline_main = report.build_headline(comparisons)
    advice_list = report.build_advice(comparisons, results, currency)

    csv_files = [
        "results/tables/summary_comparison.csv",
        "results/tables/metrics_dynamic.csv",
        "results/tables/metrics_fixed.csv",
        "results/tables/data_quality_report.csv",
        "results/equity_curves_dynamic.csv",
        "results/equity_curves_fixed.csv",
    ] + [f"results/tables/trade_log_{s}_{y}y.csv"
         for y in periods for s in ("dynamic", "fixed")]

    context = {
        "title": "纳斯达克动态跌幅加码定投 vs 每日固定100定投：yfinance真实数据回测报告",
        "article_url": ARTICLE_URL,
        "ticker": ticker, "ticker_name": TICKER_NAMES.get(ticker, ticker),
        "currency": currency, "base_amount": base_amount,
        "end_date": end_date.date(), "overall_start": earliest.date(),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "periods_text": "/".join(f"{y}" for y in periods) + "年",
        "period_list": periods,
        "dynamic_rules": rule_rows,
        "comparisons": comparisons,
        "metric_rows": metric_rows,
        "decomposition_rows": decomposition_rows,
        "contribution_count_rows": contribution_count_rows,
        "data_quality_rows": data_quality_rows,
        "charts": chart_paths,
        "execution_timing": exec_timing,
        "commission_bps": commission_bps, "slippage_bps": slippage_bps,
        "config_dump": yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        "csv_files": csv_files,
        **analysis,
        "executive_summary": exec_summary,
        "conclusion": conclusion,
        "headline_main": headline_main,
        "advice_list": advice_list,
    }
    report.generate_report(context, project_path("results", "report.html"))


def _print_console_summary(ticker, end_date, earliest, comparisons, currency):
    """Print a concise per-period summary to the console."""
    line = "=" * 72
    print(f"\n{line}")
    print("回测完成 | Data source: yfinance")
    print(f"Ticker: {ticker} | 数据范围: {earliest.date()} -> {end_date.date()}")
    print(line)
    for c in comparisons:
        print(f"\n[{c['years']}年]")
        print(f"  动态总投入: {c['dynamic_total_invested']:>12,.0f} {currency}   "
              f"固定总投入: {c['fixed_total_invested']:>12,.0f} {currency}")
        print(f"  动态最终值: {c['dynamic_final_value']:>12,.0f} {currency}   "
              f"固定最终值: {c['fixed_final_value']:>12,.0f} {currency}")
        print(f"  动态收益率: {c['dynamic_total_return']*100:>11.2f}%   "
              f"固定收益率: {c['fixed_total_return']*100:>11.2f}%")
        print(f"  超额收益率: {c['excess_return']*100:>+11.2f}%   "
              f"多赚金额:   {c['extra_profit']:>+12,.0f} {currency}")
    print(f"\n{line}")
    print(f"报告已保存: {project_path('results', 'report.html')}")
    print(line)


if __name__ == "__main__":
    main()
