"""Download and prepare price data from yfinance.

We use auto-adjusted prices (yfinance auto_adjust=True), so the returned
"Close" column is already the adjusted close (dividends and splits handled).
This avoids look-ahead bias: each day only ever uses that day's own data.
"""

import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger("nasdaq_dca")


def download_yfinance_data(ticker, start_date, end_date=None):
    """Download daily OHLCV data for a ticker from yfinance.

    Args:
        ticker: Symbol, e.g. "^IXIC".
        start_date: Start date (str "YYYY-MM-DD" or datetime-like).
        end_date: Optional end date. None = latest available.

    Returns:
        pandas.DataFrame indexed by Date with columns
        [Open, High, Low, Close, Volume]. Close is the adjusted close.

    Raises:
        RuntimeError: If no data is returned.
    """
    logger.info("Downloading %s from yfinance (start=%s end=%s)",
                ticker, start_date, end_date)
    df = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        auto_adjust=True,
        progress=False,
    )
    if df is None or df.empty:
        raise RuntimeError(
            f"yfinance returned no data for ticker '{ticker}'. "
            "Check the symbol and your network connection."
        )

    # yfinance may return a MultiIndex column frame for a single ticker.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index.name = "Date"
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    return df[keep].copy()


def clean_price_data(df):
    """Clean raw price data.

    - Drops rows with missing Close.
    - Sorts by date and removes duplicate dates.
    - Adds a daily_return column (close-to-close).

    Args:
        df: Raw price DataFrame.

    Returns:
        Cleaned DataFrame with an added "daily_return" column.
    """
    df = df.copy()
    df = df[~df.index.duplicated(keep="first")]
    df = df.sort_index()
    df = df.dropna(subset=["Close"])
    df["daily_return"] = df["Close"].pct_change()
    return df


def get_period_data(df, years, end_date=None):
    """Slice the DataFrame to the trailing `years`-year window.

    The start date is computed by going back `years` calendar years from the
    final available date; the first available trading day on or after that
    calculated start date is used.

    Args:
        df: Cleaned price DataFrame (sorted by date).
        years: Lookback length in years.
        end_date: Optional explicit end date; defaults to last row.

    Returns:
        DataFrame for the period, with daily_return recomputed within the slice
        so the first day's return is NaN (no look-back across the boundary is
        needed because contributions treat NaN as the neutral 100 bucket).
    """
    if end_date is None:
        end = df.index.max()
    else:
        end = pd.Timestamp(end_date)

    start = end - pd.DateOffset(years=years)
    period = df.loc[(df.index >= start) & (df.index <= end)].copy()
    # Recompute daily_return inside the slice for a self-contained period.
    period["daily_return"] = period["Close"].pct_change()
    return period
