"""Create deterministic demonstration data with no confidential information."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATA_DIR, DEFAULT_MARKET_PATH, DEFAULT_PORTFOLIO_PATH


def create_demo_market_data(seed: int = 42) -> pd.DataFrame:
    """Return six months of synthetic quarter-hourly German power prices.

    The series contains seasonality, volatility clusters, positive spikes and
    occasional negative prices. It is designed for demonstration and testing;
    it is not an official SMARD or ENTSO-E dataset.
    """

    rng = np.random.default_rng(seed)
    timestamps = pd.date_range(
        "2025-10-01 00:00:00",
        "2026-03-31 23:45:00",
        freq="15min",
        tz="UTC",
    )
    n_rows = len(timestamps)
    quarter_hour = np.arange(n_rows)
    hour = timestamps.hour.to_numpy() + timestamps.minute.to_numpy() / 60
    weekday = timestamps.dayofweek.to_numpy()

    daily_shape = 20 * np.sin(2 * np.pi * (hour - 7) / 24)
    evening_peak = 27 * np.exp(-0.5 * ((hour - 18.5) / 2.0) ** 2)
    weekend_discount = np.where(weekday >= 5, -11.0, 0.0)
    slow_seasonality = 13 * np.sin(2 * np.pi * quarter_hour / (96 * 75))
    noise = rng.normal(0, 9, n_rows)

    prices = 72 + daily_shape + evening_peak + weekend_discount + slow_seasonality + noise

    spike_indices = rng.choice(n_rows, size=32, replace=False)
    prices[spike_indices] += rng.uniform(110, 330, len(spike_indices))

    negative_indices = rng.choice(n_rows, size=45, replace=False)
    prices[negative_indices] -= rng.uniform(90, 160, len(negative_indices))

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "market_price_eur_mwh": np.round(prices, 2),
        }
    )


def create_demo_portfolio(
    market_data: pd.DataFrame,
    seed: int = 7,
    number_of_positions: int = 900,
) -> pd.DataFrame:
    """Create a synthetic portfolio aligned with the supplied delivery periods."""

    rng = np.random.default_rng(seed)
    if market_data.empty:
        raise ValueError("Market data is required to create a demo portfolio.")

    sample_size = min(number_of_positions, len(market_data))
    sampled = market_data.sample(n=sample_size, random_state=seed).sort_values("timestamp")
    directions = rng.choice(["BUY", "SELL"], size=sample_size, p=[0.54, 0.46])
    volumes = np.round(rng.uniform(5, 85, sample_size), 2)
    trade_noise = rng.normal(0, 12, sample_size)
    trade_prices = sampled["market_price_eur_mwh"].to_numpy() + trade_noise

    return pd.DataFrame(
        {
            "position_id": [f"POS-{index:05d}" for index in range(1, sample_size + 1)],
            "delivery_time": sampled["timestamp"].to_numpy(),
            "direction": directions,
            "volume_mwh": volumes,
            "trade_price_eur_mwh": np.round(trade_prices, 2),
        }
    )


def write_demo_data(
    market_path: Path = DEFAULT_MARKET_PATH,
    portfolio_path: Path = DEFAULT_PORTFOLIO_PATH,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Write deterministic demonstration CSV files and return their paths."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not overwrite and market_path.exists() and portfolio_path.exists():
        return market_path, portfolio_path

    market_data = create_demo_market_data()
    portfolio = create_demo_portfolio(market_data)
    market_data.to_csv(market_path, index=False)
    portfolio.to_csv(portfolio_path, index=False)
    return market_path, portfolio_path


def inject_quality_issues(
    market_data: pd.DataFrame,
    portfolio: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return copies containing controlled errors for demonstrating monitoring."""

    market = market_data.copy()
    positions = portfolio.copy()

    if len(market) > 20:
        market = market.drop(index=market.index[10]).reset_index(drop=True)
        market = pd.concat([market, market.iloc[[5]]], ignore_index=True)
        market.loc[15, "market_price_eur_mwh"] = np.nan

    if len(positions) > 10:
        positions.loc[3, "volume_mwh"] = -5
        positions.loc[6, "direction"] = "HOLD"
        positions.loc[9, "delivery_time"] = pd.Timestamp("2030-01-01", tz="UTC")

    return market, positions

