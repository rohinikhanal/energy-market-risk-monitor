"""Deterministic price-stress scenarios for the valued portfolio."""

from __future__ import annotations

import pandas as pd


def run_price_stress_tests(
    valued_positions: pd.DataFrame,
    proportional_shock: float = 0.30,
) -> pd.DataFrame:
    """Calculate portfolio P&L under transparent market-price scenarios."""

    matched = valued_positions.dropna(
        subset=["market_price_eur_mwh", "trade_price_eur_mwh", "signed_volume_mwh"]
    ).copy()
    if matched.empty:
        return pd.DataFrame(
            columns=["scenario", "portfolio_pnl_eur", "change_vs_base_eur"]
        )

    base_prices = matched["market_price_eur_mwh"]
    scenarios = {
        "Base market": base_prices,
        f"Prices +{proportional_shock:.0%}": base_prices * (1 + proportional_shock),
        f"Prices -{proportional_shock:.0%}": base_prices * (1 - proportional_shock),
        "Parallel +100 EUR/MWh": base_prices + 100,
        "Parallel -100 EUR/MWh": base_prices - 100,
        "Negative-price event (-50 EUR/MWh)": pd.Series(
            -50.0, index=matched.index, dtype=float
        ),
    }

    scenario_rows = []
    base_pnl = float(matched["pnl_eur"].sum())
    for scenario_name, stressed_prices in scenarios.items():
        scenario_pnl = float(
            (
                matched["signed_volume_mwh"]
                * (stressed_prices - matched["trade_price_eur_mwh"])
            ).sum()
        )
        scenario_rows.append(
            {
                "scenario": scenario_name,
                "portfolio_pnl_eur": scenario_pnl,
                "change_vs_base_eur": scenario_pnl - base_pnl,
            }
        )

    return pd.DataFrame(scenario_rows)

