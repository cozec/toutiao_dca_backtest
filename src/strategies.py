"""Contribution rules for the two DCA strategies.

Both strategies invest every trading day. They differ only in *how much* is
invested on a given day.
"""

import math


def fixed_daily_dca_amount(daily_return, amount=100):
    """Fixed daily contribution: always invest `amount`, every trading day.

    Args:
        daily_return: That day's return (ignored; kept for a uniform signature).
        amount: The fixed daily contribution.

    Returns:
        float: The contribution amount.
    """
    return float(amount)


def dynamic_daily_dca_amount(daily_return, rules):
    """Return-adjusted ("dip-buying") daily contribution.

    Buy more when the index falls, less when it rises, using the configured
    rule buckets.

    Boundary handling: a rule matches when
        (min_return is None or daily_return > min_return) and
        (max_return is None or daily_return <= max_return)

    The first trading day of a period has a NaN return; it is treated as the
    neutral middle bucket (the 100 bucket in the default config).

    Args:
        daily_return: That day's close-to-close return (may be NaN).
        rules: List of dicts with keys min_return, max_return, amount, label.

    Returns:
        float: The contribution amount for the day.
    """
    if daily_return is None or (isinstance(daily_return, float) and math.isnan(daily_return)):
        # Neutral day: use the bucket that contains a 0% return.
        return float(_neutral_amount(rules))

    for rule in rules:
        lo = rule.get("min_return")
        hi = rule.get("max_return")
        if (lo is None or daily_return > lo) and (hi is None or daily_return <= hi):
            return float(rule["amount"])

    # Fallback (should not happen with a well-formed config): neutral bucket.
    return float(_neutral_amount(rules))


def _neutral_amount(rules):
    """Find the contribution for a 0% return day (the neutral bucket)."""
    for rule in rules:
        lo = rule.get("min_return")
        hi = rule.get("max_return")
        if (lo is None or 0.0 > lo) and (hi is None or 0.0 <= hi):
            return rule["amount"]
    return rules[0]["amount"]
