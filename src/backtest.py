"""Daily DCA backtesting engine.

Both strategies invest every trading day. The engine is agnostic to the
contribution rule: it takes a `contribution_function(daily_return) -> amount`.

Execution timing:
  - "same_day_close": the signal (that day's return) and the buy both use the
    same day's close. Easy to reproduce but assumes a near-close estimate in
    real life. This is the default and is flagged in the report.
  - "next_day_close": the signal uses day t's return, but the buy executes at
    day t+1's close. The final day's signal is therefore not executed.

Portfolio value is marked-to-market at each day's close.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("nasdaq_dca")


def run_dca_backtest(price_data, contribution_function,
                     execution_timing="same_day_close",
                     allow_fractional_shares=True,
                     commission_bps=0.0, slippage_bps=0.0):
    """Run a daily DCA backtest.

    Args:
        price_data: DataFrame indexed by Date with "Close" and "daily_return".
        contribution_function: Callable(daily_return) -> contribution amount.
        execution_timing: "same_day_close" or "next_day_close".
        allow_fractional_shares: If False, shares are floored to whole units.
        commission_bps: Commission in basis points of each contribution.
        slippage_bps: Slippage in basis points added to the execution price.

    Returns:
        equity_curve: DataFrame (one row per trading day) with the columns
            date, close, daily_return, contribution, exec_price, shares_bought,
            cumulative_shares, cumulative_invested, cash, portfolio_value,
            profit, return_on_invested_capital.
    """
    closes = price_data["Close"].values
    returns = price_data["daily_return"].values
    dates = price_data.index
    n = len(price_data)

    rows = []
    cumulative_shares = 0.0
    cumulative_invested = 0.0
    commission_rate = commission_bps / 10000.0
    slippage_rate = slippage_bps / 10000.0

    for i in range(n):
        daily_return = returns[i]
        contribution = float(contribution_function(daily_return))

        # Determine execution price index.
        if execution_timing == "next_day_close":
            exec_idx = i + 1 if i + 1 < n else None
        else:  # same_day_close
            exec_idx = i

        shares_bought = 0.0
        exec_price = np.nan
        if exec_idx is not None and contribution > 0:
            exec_price = closes[exec_idx] * (1.0 + slippage_rate)
            net_to_invest = contribution * (1.0 - commission_rate)
            shares_bought = net_to_invest / exec_price
            if not allow_fractional_shares:
                shares_bought = float(np.floor(shares_bought))
            cumulative_shares += shares_bought
            cumulative_invested += contribution

        # Mark-to-market at today's close.
        portfolio_value = cumulative_shares * closes[i]
        profit = portfolio_value - cumulative_invested
        roic = profit / cumulative_invested if cumulative_invested > 0 else 0.0

        rows.append({
            "date": dates[i],
            "close": closes[i],
            "daily_return": daily_return,
            "contribution": contribution if exec_idx is not None else 0.0,
            "exec_price": exec_price,
            "shares_bought": shares_bought,
            "cumulative_shares": cumulative_shares,
            "cumulative_invested": cumulative_invested,
            "cash": 0.0,  # fully deployed each day; no idle cash held
            "portfolio_value": portfolio_value,
            "profit": profit,
            "return_on_invested_capital": roic,
        })

    equity_curve = pd.DataFrame(rows).set_index("date")
    return equity_curve
