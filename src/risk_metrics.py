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
    """Return a dated P&L series with a VaR-breach indicator."""

    clean = _clean_pnl(pnl)
    result = clean.rename("pnl_eur").to_frame()
    result["var_limit_eur"] = -abs(var_value)
    result["breach"] = result["pnl_eur"] < result["var_limit_eur"]
    return result


def risk_summary(pnl: pd.Series, confidence: float = 0.95) -> dict[str, float]:
    """Return a concise collection of distribution and breach statistics."""

    clean = _clean_pnl(pnl)
    var_value = historical_var(clean, confidence)
    es_value = expected_shortfall(clean, confidence)
    breaches = var_breaches(clean, var_value) if not clean.empty else pd.DataFrame()
    return {
        "observations": float(len(clean)),
        "mean_pnl_eur": float(clean.mean()) if not clean.empty else float("nan"),
        "volatility_eur": float(clean.std(ddof=1)) if len(clean) > 1 else 0.0,
        "historical_var_eur": var_value,
        "expected_shortfall_eur": es_value,
        "breach_count": float(breaches["breach"].sum()) if not breaches.empty else 0.0,
        "breach_rate_pct": (
            float(100 * breaches["breach"].mean()) if not breaches.empty else 0.0
        ),
    }

