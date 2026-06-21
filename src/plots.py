"""Chart generation for the backtest report.

All charts are saved as PNG files under results/charts/. Chinese labels are
used to match the article; a CJK-capable font is selected automatically.
"""

import logging
import os

import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

from . import metrics as metrics_mod

logger = logging.getLogger("nasdaq_dca")

# Colors: dynamic = warm/red (buy-the-dip), fixed = cool/blue.
DYNAMIC_COLOR = "#d9534f"
FIXED_COLOR = "#337ab7"
INVESTED_COLOR = "#7f8c8d"

# Asset display label used in chart titles. Set per-run via generate_all_charts.
ASSET_LABEL = "纳斯达克"


def _setup_cjk_font():
    """Pick a CJK-capable font available on the system for matplotlib."""
    candidates = [
        "Arial Unicode MS", "PingFang SC", "Heiti SC", "Heiti TC",
        "STHeiti", "Songti SC", "Hiragino Sans GB", "Microsoft YaHei",
        "Noto Sans CJK SC", "SimHei",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    else:
        logger.warning("No CJK font found; Chinese characters may not render.")
    plt.rcParams["axes.unicode_minus"] = False


_setup_cjk_font()


def _save(fig, path):
    """Save a figure and close it."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved chart: %s", path)


def _period_labels(periods):
    return [f"{y}年" for y in periods]


def _periods_str(comparisons):
    """e.g. '3/5/10/20' from the available comparison periods."""
    return "/".join(str(c["years"]) for c in comparisons)


def plot_return_rate_comparison(comparisons, out_path):
    """Grouped bar chart of total return rate, dynamic vs fixed."""
    periods = [c["years"] for c in comparisons]
    labels = _period_labels(periods)
    dyn = [c["dynamic_total_return"] * 100 for c in comparisons]
    fix = [c["fixed_total_return"] * 100 for c in comparisons]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = range(len(labels))
    w = 0.38
    b1 = ax.bar([i - w / 2 for i in x], dyn, w, label="动态跌幅加码定投", color=DYNAMIC_COLOR)
    b2 = ax.bar([i + w / 2 for i in x], fix, w, label="每日固定100定投", color=FIXED_COLOR)
    ax.set_title(f"{ASSET_LABEL}{_periods_str(comparisons)}年定投策略总收益率对比", fontsize=14)
    ax.set_xlabel("投资周期")
    ax.set_ylabel("总收益率 (%)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.legend()
    for bars in (b1, b2):
        for r in bars:
            ax.annotate(f"{r.get_height():.1f}%", (r.get_x() + r.get_width() / 2, r.get_height()),
                        ha="center", va="bottom", fontsize=9)
    _save(fig, out_path)


def plot_profit_amount_comparison(comparisons, currency, out_path):
    """Grouped bar chart of total profit amount: dynamic vs equal-capital vs fixed.

    The equal-capital benchmark (same total invested as dynamic, spread evenly)
    sits between the two: fixed->equal-capital is the pure capital effect, and
    equal-capital->dynamic is the pure timing alpha.
    """
    periods = [c["years"] for c in comparisons]
    labels = _period_labels(periods)
    dyn = [c["dynamic_profit"] for c in comparisons]
    eq = [c.get("equalcap_profit", 0) for c in comparisons]
    fix = [c["fixed_profit"] for c in comparisons]

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    x = range(len(labels))
    w = 0.27
    b1 = ax.bar([i - w for i in x], dyn, w, label="动态跌幅加码定投", color=DYNAMIC_COLOR)
    b2 = ax.bar(list(x), eq, w, label="等额基准(同动态总本金,均匀投)", color="#e8a33d")
    b3 = ax.bar([i + w for i in x], fix, w, label="每日固定100定投", color=FIXED_COLOR)
    ax.set_title(f"{ASSET_LABEL}{_periods_str(comparisons)}年定投策略总收益金额对比", fontsize=14)
    ax.set_xlabel("投资周期")
    ax.set_ylabel(f"收益金额 ({currency})")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.legend(fontsize=8)
    for bars in (b1, b2, b3):
        for r in bars:
            ax.annotate(f"{r.get_height():,.0f}", (r.get_x() + r.get_width() / 2, r.get_height()),
                        ha="center", va="bottom", fontsize=7)
    _save(fig, out_path)


def plot_profit_decomposition(comparisons, currency, out_path):
    """Stacked bar: extra profit split into timing alpha + capital effect."""
    periods = [c["years"] for c in comparisons]
    labels = _period_labels(periods)
    timing = [c.get("timing_alpha", 0) for c in comparisons]
    capital = [c.get("capital_effect", 0) for c in comparisons]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = range(len(labels))
    b1 = ax.bar(list(x), capital, 0.5, label="多投入本金的贡献", color="#e8a33d")
    b2 = ax.bar(list(x), timing, 0.5, bottom=capital, label="择时 alpha（下跌加码）", color=DYNAMIC_COLOR)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_title("动态策略「多赚金额」拆解：择时 vs 多投入本金", fontsize=14)
    ax.set_xlabel("投资周期")
    ax.set_ylabel(f"多赚金额 ({currency})")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.legend(fontsize=9)
    for c, cap, tim in zip(comparisons, capital, timing):
        total = cap + tim
        ax.annotate(f"{total:,.0f}", (periods.index(c["years"]), total),
                    ha="center", va="bottom", fontsize=8, fontweight="bold")
    _save(fig, out_path)


def plot_excess_return_rate(comparisons, out_path):
    """Line chart of excess return rate (dynamic - fixed)."""
    periods = [c["years"] for c in comparisons]
    labels = _period_labels(periods)
    excess = [c["excess_return"] * 100 for c in comparisons]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(labels, excess, marker="o", color=DYNAMIC_COLOR, linewidth=2)
    ax.axhline(0, linestyle="--", color="gray")
    ax.set_title("动态定投策略相对固定100定投的超额收益率变化", fontsize=14)
    ax.set_xlabel("投资周期")
    ax.set_ylabel("超额收益率 (%)")
    for xi, yi in zip(labels, excess):
        ax.annotate(f"{yi:+.2f}%", (xi, yi), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9)
    _save(fig, out_path)


def plot_extra_profit(comparisons, currency, out_path):
    """Line chart of extra profit (dynamic profit - fixed profit)."""
    periods = [c["years"] for c in comparisons]
    labels = _period_labels(periods)
    extra = [c["extra_profit"] for c in comparisons]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(labels, extra, marker="s", color="#9b59b6", linewidth=2)
    ax.axhline(0, linestyle="--", color="gray")
    ax.set_title("动态定投策略相对固定100定投的多赚金额", fontsize=14)
    ax.set_xlabel("投资周期")
    ax.set_ylabel(f"多赚金额 ({currency})")
    for xi, yi in zip(labels, extra):
        ax.annotate(f"{yi:,.0f}", (xi, yi), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9)
    _save(fig, out_path)


def plot_equity_curve(dyn_ec, fix_ec, years, currency, out_path):
    """Equity curves plus cumulative invested capital for one period."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(dyn_ec.index, dyn_ec["portfolio_value"], color=DYNAMIC_COLOR,
            label="动态定投 组合价值", linewidth=1.6)
    ax.plot(fix_ec.index, fix_ec["portfolio_value"], color=FIXED_COLOR,
            label="固定100定投 组合价值", linewidth=1.6)
    ax.plot(dyn_ec.index, dyn_ec["cumulative_invested"], color=DYNAMIC_COLOR,
            label="动态定投 累计投入", linestyle="--", linewidth=1.1, alpha=0.7)
    ax.plot(fix_ec.index, fix_ec["cumulative_invested"], color=FIXED_COLOR,
            label="固定定投 累计投入", linestyle="--", linewidth=1.1, alpha=0.7)
    ax.set_title(f"{ASSET_LABEL}{years}年定投组合价值与累计投入", fontsize=14)
    ax.set_xlabel("日期")
    ax.set_ylabel(f"金额 ({currency})")
    ax.legend(loc="upper left", fontsize=9)
    _save(fig, out_path)


def plot_dynamic_contribution(dyn_ec, years, currency, out_path):
    """Daily dynamic contribution amount over time for one period."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.scatter(dyn_ec.index, dyn_ec["contribution"], s=6, color=DYNAMIC_COLOR, alpha=0.6)
    ax.set_title(f"{ASSET_LABEL}{years}年动态定投每日投入金额", fontsize=14)
    ax.set_xlabel("日期")
    ax.set_ylabel(f"每日投入 ({currency})")
    _save(fig, out_path)


def plot_price_with_markers(dyn_ec, years, out_path):
    """Nasdaq price with high- vs low-contribution day markers."""
    high = dyn_ec[dyn_ec["contribution"] >= 200]
    low = dyn_ec[dyn_ec["contribution"] <= 50]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(dyn_ec.index, dyn_ec["close"], color="#34495e", linewidth=1.0, label=f"{ASSET_LABEL}收盘价")
    ax.scatter(high.index, high["close"], s=14, color=DYNAMIC_COLOR,
               label="高投入日 (200/300)", alpha=0.7, zorder=3)
    ax.scatter(low.index, low["close"], s=10, color=FIXED_COLOR,
               label="低投入日 (20/50)", alpha=0.5, zorder=2)
    ax.set_title(f"{ASSET_LABEL}{years}年价格与动态定投买入标记", fontsize=14)
    ax.set_xlabel("日期")
    ax.set_ylabel("指数点位")
    ax.legend(loc="upper left", fontsize=9)
    _save(fig, out_path)


def plot_drawdown(dyn_ec, fix_ec, years, out_path):
    """Portfolio-value drawdown comparison for one period."""
    dyn_dd = metrics_mod.calculate_drawdown(dyn_ec["portfolio_value"]) * 100
    fix_dd = metrics_mod.calculate_drawdown(fix_ec["portfolio_value"]) * 100

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dyn_dd.index, dyn_dd, color=DYNAMIC_COLOR, label="动态定投回撤", linewidth=1.4)
    ax.plot(fix_dd.index, fix_dd, color=FIXED_COLOR, label="固定100定投回撤", linewidth=1.4)
    ax.fill_between(dyn_dd.index, dyn_dd, 0, color=DYNAMIC_COLOR, alpha=0.12)
    ax.set_title(f"{ASSET_LABEL}{years}年定投组合回撤对比", fontsize=14)
    ax.set_xlabel("日期")
    ax.set_ylabel("回撤 (%)")
    ax.legend(loc="lower left", fontsize=9)
    _save(fig, out_path)


def generate_all_charts(results, comparisons, currency, charts_dir, asset="纳斯达克"):
    """Generate every chart and return a dict of relative filenames.

    Args:
        results: dict keyed by years -> {"dynamic": ec, "fixed": ec}.
        comparisons: list of comparison dicts (ordered by period).
        currency: currency label.
        charts_dir: output directory for charts.
        asset: display label of the invested asset, used in chart titles.

    Returns:
        dict mapping logical chart name to filename (basename).
    """
    global ASSET_LABEL
    ASSET_LABEL = asset
    paths = {}

    def p(name):
        return os.path.join(charts_dir, name)

    plot_return_rate_comparison(comparisons, p("return_rate_comparison.png"))
    paths["return_rate_comparison"] = "return_rate_comparison.png"

    plot_profit_amount_comparison(comparisons, currency, p("profit_amount_comparison.png"))
    paths["profit_amount_comparison"] = "profit_amount_comparison.png"

    plot_profit_decomposition(comparisons, currency, p("profit_decomposition.png"))
    paths["profit_decomposition"] = "profit_decomposition.png"

    plot_excess_return_rate(comparisons, p("excess_return_rate.png"))
    paths["excess_return_rate"] = "excess_return_rate.png"

    plot_extra_profit(comparisons, currency, p("extra_profit.png"))
    paths["extra_profit"] = "extra_profit.png"

    for years, res in results.items():
        dyn_ec, fix_ec = res["dynamic"], res["fixed"]

        fn = f"equity_curve_{years}y.png"
        plot_equity_curve(dyn_ec, fix_ec, years, currency, p(fn))
        paths[f"equity_curve_{years}y"] = fn

        fn = f"dynamic_contribution_{years}y.png"
        plot_dynamic_contribution(dyn_ec, years, currency, p(fn))
        paths[f"dynamic_contribution_{years}y"] = fn

        fn = f"drawdown_{years}y.png"
        plot_drawdown(dyn_ec, fix_ec, years, p(fn))
        paths[f"drawdown_{years}y"] = fn

    # Price-with-markers chart for the longest available period.
    longest = max(results.keys())
    fn = f"nasdaq_price_with_dynamic_buy_markers_{longest}y.png"
    plot_price_with_markers(results[longest]["dynamic"], longest, p(fn))
    paths["price_markers"] = fn
    paths["price_markers_years"] = longest

    return paths
