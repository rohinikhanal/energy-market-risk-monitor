"""Portfolio valuation and P&L calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def value_positions(positions: pd.DataFrame, market_data: pd.DataFrame) -> pd.DataFrame:
    """Match positions to market prices and calculate mark-to-market P&L.

    BUY positions have positive signed volume; SELL positions have negative
    signed volume. P&L is signed volume multiplied by market minus trade price.
    """

    valued = positions.merge(
        market_data[["timestamp", "market_price_eur_mwh"]],
        how="left",
        left_on="delivery_time",
        right_on="timestamp",
        validate="many_to_one",
    )
    valued["signed_volume_mwh"] = np.where(
        valued["direction"].eq("BUY"), valued["volume_mwh"], -valued["volume_mwh"]
    )
    valued["market_value_eur"] = (
        valued["signed_volume_mwh"] * valued["market_price_eur_mwh"]
    )
    valued["trade_value_eur"] = (
        valued["signed_volume_mwh"] * valued["trade_price_eur_mwh"]
    )
    valued["pnl_eur"] = valued["market_value_eur"] - valued["trade_value_eur"]
    valued["gross_exposure_eur"] = (
        valued["volume_mwh"] * valued["market_price_eur_mwh"].abs()
    )
    return valued


def calculate_daily_pnl(valued_positions: pd.DataFrame) -> pd.Series:
    """Aggregate matched position P&L by UTC delivery date."""

    matched = valued_positions.dropna(subset=["delivery_time", "pnl_eur"]).copy()
    if matched.empty:
        return pd.Series(dtype="float64", name="daily_pnl_eur")
    matched["delivery_date"] = matched["delivery_time"].dt.floor("D")
    daily = matched.groupby("delivery_date")["pnl_eur"].sum().sort_index()
    daily.name = "daily_pnl_eur"
    return daily


def portfolio_summary(valued_positions: pd.DataFrame) -> dict[str, float]:
    """Return portfolio-level exposure, P&L and matching metrics."""

    total_positions = len(valued_positions)
    matched_positions = int(valued_positions["market_price_eur_mwh"].notna().sum())
    coverage = 100 * matched_positions / total_positions if total_positions else 0.0
    return {
        "position_count": float(total_positions),
        "matched_positions": float(matched_positions),
        "price_coverage_pct": float(coverage),
        "net_volume_mwh": float(valued_positions["signed_volume_mwh"].sum()),
        "gross_exposure_eur": float(valued_positions["gross_exposure_eur"].sum()),
        "portfolio_pnl_eur": float(valued_positions["pnl_eur"].sum()),
    }

