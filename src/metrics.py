"""Performance metrics for DCA equity curves.

Notes on DCA-specific metric choices:
- Total return rate is profit / total_invested (simple, matches the article).
- Annualized return uses a money-weighted IRR (XIRR) on the daily cashflows,
  because capital is deployed gradually rather than as a lump sum.
- Daily portfolio returns exclude new contributions, so volatility and Sharpe
  reflect market moves on already-held shares, not cash inflows.
- Max drawdown is the peak-to-trough decline of the total portfolio value.
"""

import logging

import numpy as np
import pandas as pd
from scipy.optimize import brentq

logger = logging.getLogger("nasdaq_dca")

TRADING_DAYS = 252


def calculate_drawdown(series):
    """Return the running drawdown series (<= 0) of a value series."""
    running_max = series.cummax()
    return series / running_max - 1.0


def calculate_max_drawdown(series):
    """Return the maximum drawdown (a negative number) of a value series."""
    dd = calculate_drawdown(series)
    return float(dd.min()) if len(dd) else 0.0


def calculate_xirr(cashflows, dates, guess=0.1):
    """Money-weighted annualized return (XIRR) for dated cashflows.

    Args:
        cashflows: Sequence of cashflows. Contributions are negative, the final
            portfolio value is a positive terminal cashflow.
        dates: Matching sequence of datetimes.
        guess: Initial guess (unused by brentq but kept for clarity).

    Returns:
        float: Annualized rate, or np.nan if it cannot be solved.
    """
    dates = pd.to_datetime(list(dates))
    t0 = dates[0]
    years = np.array([(d - t0).days / 365.0 for d in dates])
    cf = np.array(cashflows, dtype=float)

    def npv(rate):
        return np.sum(cf / (1.0 + rate) ** years)

    try:
        # Bracket the root; returns are typically within (-0.99, 10).
        return float(brentq(npv, -0.9999, 10.0, maxiter=500))
    except (ValueError, RuntimeError):
        return float("nan")


def calculate_annualized_return(equity_curve):
    """Annualized money-weighted return based on deployed capital (XIRR)."""
    contribs = equity_curve["contribution"].values
    dates = list(equity_curve.index)
    final_value = float(equity_curve["portfolio_value"].iloc[-1])

    # Daily contributions as negative cashflows, terminal value as positive.
    cashflows = list(-contribs)
    cashflows[-1] += final_value
    return calculate_xirr(cashflows, dates)


def _daily_portfolio_returns(equity_curve):
    """Daily market-driven portfolio returns, excluding new contributions."""
    close = equity_curve["close"]
    prev_shares = equity_curve["cumulative_shares"].shift(1)
    prev_value = equity_curve["portfolio_value"].shift(1)
    pnl = prev_shares * (close - close.shift(1))
    ret = pnl / prev_value
    return ret.replace([np.inf, -np.inf], np.nan).dropna()


def calculate_sharpe(equity_curve, risk_free_rate=0.0):
    """Annualized Sharpe ratio of daily market-driven portfolio returns."""
    ret = _daily_portfolio_returns(equity_curve)
    if ret.std() == 0 or len(ret) < 2:
        return 0.0
    rf_daily = risk_free_rate / TRADING_DAYS
    excess = ret - rf_daily
    return float(excess.mean() / ret.std() * np.sqrt(TRADING_DAYS))


def calculate_volatility(equity_curve):
    """Annualized volatility of daily market-driven portfolio returns."""
    ret = _daily_portfolio_returns(equity_curve)
    if len(ret) < 2:
        return 0.0
    return float(ret.std() * np.sqrt(TRADING_DAYS))


def calculate_summary_metrics(equity_curve, base_amounts=(20, 50, 100, 200, 300),
                              risk_free_rate=0.0):
    """Compute the full summary metric dict for one strategy/period.

    Args:
        equity_curve: Output of run_dca_backtest.
        base_amounts: Contribution buckets to count.
        risk_free_rate: Annual risk-free rate for Sharpe.

    Returns:
        dict of metrics.
    """
    ec = equity_curve
    total_invested = float(ec["cumulative_invested"].iloc[-1])
    final_value = float(ec["portfolio_value"].iloc[-1])
    profit = final_value - total_invested
    total_return = profit / total_invested if total_invested > 0 else 0.0
    total_shares = float(ec["cumulative_shares"].iloc[-1])
    ending_price = float(ec["close"].iloc[-1])
    avg_cost = total_invested / total_shares if total_shares > 0 else 0.0

    contributions = ec["contribution"][ec["contribution"] > 0]

    metrics = {
        "trading_days": int(len(ec)),
        "total_invested": total_invested,
        "final_value": final_value,
        "profit": profit,
        "total_return": total_return,
        "total_shares": total_shares,
        "avg_cost_per_share": avg_cost,
        "ending_price": ending_price,
        "annualized_return": calculate_annualized_return(ec),
        "max_drawdown": calculate_max_drawdown(ec["portfolio_value"]),
        "volatility": calculate_volatility(ec),
        "sharpe": calculate_sharpe(ec, risk_free_rate),
        "avg_contribution": float(contributions.mean()) if len(contributions) else 0.0,
        "min_contribution": float(contributions.min()) if len(contributions) else 0.0,
        "max_contribution": float(contributions.max()) if len(contributions) else 0.0,
        "start_date": ec.index.min(),
        "end_date": ec.index.max(),
    }

    # Count how many days fell into each contribution bucket.
    counts = {}
    for amt in base_amounts:
        counts[int(amt)] = int((np.isclose(ec["contribution"], amt)).sum())
    metrics["contribution_counts"] = counts

    return metrics


def calculate_period_comparison(dynamic_metrics, fixed_metrics, years,
                                equalcap_metrics=None):
    """Compare dynamic vs fixed strategy for one period.

    Separates the return-rate advantage, the absolute profit advantage, and the
    extra capital the dynamic strategy deployed.

    If `equalcap_metrics` (the equal-capital benchmark: same total invested as
    dynamic, but spread evenly across all days) is provided, the dynamic
    strategy's extra profit over fixed-100 is decomposed into:
        extra_profit = timing_alpha + capital_effect
      - timing_alpha  = dynamic_profit - equalcap_profit
            (same capital, different *timing* -> pure dip-buying skill)
      - capital_effect = equalcap_profit - fixed_profit
            (pure effect of deploying more money, evenly)

    Returns:
        dict of comparison fields.
    """
    excess_return = dynamic_metrics["total_return"] - fixed_metrics["total_return"]
    extra_profit = dynamic_metrics["profit"] - fixed_metrics["profit"]
    extra_final = dynamic_metrics["final_value"] - fixed_metrics["final_value"]
    extra_invested = dynamic_metrics["total_invested"] - fixed_metrics["total_invested"]

    comp = {
        "years": years,
        "dynamic_total_return": dynamic_metrics["total_return"],
        "fixed_total_return": fixed_metrics["total_return"],
        "excess_return": excess_return,
        "dynamic_final_value": dynamic_metrics["final_value"],
        "fixed_final_value": fixed_metrics["final_value"],
        "dynamic_total_invested": dynamic_metrics["total_invested"],
        "fixed_total_invested": fixed_metrics["total_invested"],
        "dynamic_profit": dynamic_metrics["profit"],
        "fixed_profit": fixed_metrics["profit"],
        "extra_profit": extra_profit,
        "extra_final_value": extra_final,
        "extra_invested": extra_invested,
    }

    if equalcap_metrics is not None:
        timing_alpha = dynamic_metrics["profit"] - equalcap_metrics["profit"]
        capital_effect = equalcap_metrics["profit"] - fixed_metrics["profit"]
        comp.update({
            "equalcap_total_return": equalcap_metrics["total_return"],
            "equalcap_final_value": equalcap_metrics["final_value"],
            "equalcap_total_invested": equalcap_metrics["total_invested"],
            "equalcap_profit": equalcap_metrics["profit"],
            "timing_alpha": timing_alpha,
            "capital_effect": capital_effect,
            # Shares of the total extra profit (guard against divide-by-zero).
            "timing_alpha_share": (timing_alpha / extra_profit
                                   if extra_profit else 0.0),
            "capital_effect_share": (capital_effect / extra_profit
                                     if extra_profit else 0.0),
            # The equal-capital benchmark beats dynamic on rate iff timing < 0.
            "timing_excess_return": (dynamic_metrics["total_return"]
                                     - equalcap_metrics["total_return"]),
        })

    return comp
