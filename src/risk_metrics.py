"""Transparent historical risk calculations for a P&L series."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clean_pnl(pnl: pd.Series) -> pd.Series:
    return pd.to_numeric(pnl, errors="coerce").dropna().astype(float)


def historical_var(pnl: pd.Series, confidence: float = 0.95) -> float:
    """Return positive Value at Risk from an observed P&L distribution."""

    if not 0 < confidence < 1:
        raise ValueError("Confidence must be between 0 and 1.")
    clean = _clean_pnl(pnl)
    if clean.empty:
        return float("nan")
    losses = -clean
    return float(max(0.0, np.quantile(losses, confidence)))


def expected_shortfall(pnl: pd.Series, confidence: float = 0.95) -> float:
    """Return average loss at or beyond historical VaR."""

    clean = _clean_pnl(pnl)
    if clean.empty:
        return float("nan")
    var_value = historical_var(clean, confidence)
    losses = -clean
    tail_losses = losses[losses >= var_value]
    if tail_losses.empty:
        return var_value
    return float(max(0.0, tail_losses.mean()))


def var_breaches(pnl: pd.Series, var_value: float) -> pd.DataFrame:
    """Apply one fixed VaR threshold to a dated P&L series.

    This helper is useful for threshold inspection, but it is not an
    out-of-sample backtest. Use :func:`rolling_var_backtest` for backtesting.
    """

    clean = _clean_pnl(pnl)
    result = clean.rename("pnl_eur").to_frame()
    result["var_limit_eur"] = -abs(var_value)
    result["breach"] = result["pnl_eur"] < result["var_limit_eur"]
    return result


def rolling_var_backtest(
    pnl: pd.Series,
    confidence: float = 0.95,
    lookback: int = 90,
) -> pd.DataFrame:
    """Backtest one-day historical VaR using only information available at the time.

    For each test day, VaR and Expected Shortfall are estimated from the
    immediately preceding ``lookback`` daily P&L observations. The realized P&L
    for the test day is never included in its own risk estimate.
    """

    if not 0 < confidence < 1:
        raise ValueError("Confidence must be between 0 and 1.")
    if not isinstance(lookback, int) or isinstance(lookback, bool) or lookback < 2:
        raise ValueError("Lookback must be an integer of at least 2 observations.")

    clean = _clean_pnl(pnl).sort_index()
    columns = [
        "pnl_eur",
        "var_eur",
        "var_limit_eur",
        "expected_shortfall_eur",
        "es_limit_eur",
        "breach",
    ]
    if len(clean) <= lookback:
        return pd.DataFrame(columns=columns, index=clean.index[:0])

    records: list[dict[str, float | bool]] = []
    test_index = []
    for position in range(lookback, len(clean)):
        estimation_window = clean.iloc[position - lookback : position]
        var_value = historical_var(estimation_window, confidence)
        es_value = expected_shortfall(estimation_window, confidence)
        realized_pnl = float(clean.iloc[position])
        records.append(
            {
                "pnl_eur": realized_pnl,
                "var_eur": var_value,
                "var_limit_eur": -var_value,
                "expected_shortfall_eur": es_value,
                "es_limit_eur": -es_value,
                "breach": realized_pnl < -var_value,
            }
        )
        test_index.append(clean.index[position])

    return pd.DataFrame(records, index=pd.Index(test_index, name=clean.index.name))[columns]


def risk_summary(
    pnl: pd.Series,
    confidence: float = 0.95,
    lookback: int = 90,
) -> dict[str, float]:
    """Return current one-day risk estimates and out-of-sample breach statistics."""

    clean = _clean_pnl(pnl).sort_index()
    backtest = rolling_var_backtest(clean, confidence, lookback)
    estimation_window = clean.iloc[-lookback:]
    var_value = historical_var(estimation_window, confidence)
    es_value = expected_shortfall(estimation_window, confidence)
    return {
        "observations": float(len(clean)),
        "estimation_observations": float(len(estimation_window)),
        "var_lookback_days": float(lookback),
        "mean_pnl_eur": (
            float(estimation_window.mean()) if not estimation_window.empty else float("nan")
        ),
        "volatility_eur": (
            float(estimation_window.std(ddof=1)) if len(estimation_window) > 1 else 0.0
        ),
        "historical_var_eur": var_value,
        "expected_shortfall_eur": es_value,
        "backtest_observations": float(len(backtest)),
        "breach_count": float(backtest["breach"].sum()) if not backtest.empty else 0.0,
        "breach_rate_pct": (
            float(100 * backtest["breach"].mean()) if not backtest.empty else float("nan")
        ),
        "expected_breach_rate_pct": float(100 * (1 - confidence)),
    }
