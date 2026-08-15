"""Read, validate and normalize market and portfolio CSV data."""

from __future__ import annotations

from pathlib import Path
from typing import IO, Union

import pandas as pd

from .config import MARKET_REQUIRED_COLUMNS, PORTFOLIO_REQUIRED_COLUMNS


CsvSource = Union[str, Path, IO[bytes], IO[str]]


def _require_columns(data: pd.DataFrame, required: set[str], dataset_name: str) -> None:
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"{dataset_name} is missing required columns: {sorted(missing)}")


def read_market_data(source: CsvSource) -> pd.DataFrame:
    """Read market data without silently dropping records."""

    data = pd.read_csv(source)
    _require_columns(data, MARKET_REQUIRED_COLUMNS, "Market data")
    data = data.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    data["market_price_eur_mwh"] = pd.to_numeric(
        data["market_price_eur_mwh"], errors="coerce"
    )
    return data


def read_portfolio_data(source: CsvSource) -> pd.DataFrame:
    """Read position data without silently dropping invalid records."""

    data = pd.read_csv(source)
    _require_columns(data, PORTFOLIO_REQUIRED_COLUMNS, "Portfolio data")
    data = data.copy()
    data["delivery_time"] = pd.to_datetime(data["delivery_time"], utc=True, errors="coerce")
    data["direction"] = data["direction"].astype("string").str.upper().str.strip()
    for column in ["volume_mwh", "trade_price_eur_mwh"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    return data


def prepare_market_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return calculation-ready market data after quality checks are recorded."""

    prepared = data.dropna(subset=["timestamp", "market_price_eur_mwh"]).copy()
    prepared = prepared.sort_values("timestamp").drop_duplicates(
        subset=["timestamp"], keep="last"
    )
    return prepared.reset_index(drop=True)


def prepare_portfolio_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return calculation-ready positions after quality checks are recorded."""

    prepared = data.dropna(
        subset=[
            "position_id",
            "delivery_time",
            "direction",
            "volume_mwh",
            "trade_price_eur_mwh",
        ]
    ).copy()
    prepared = prepared[
        prepared["direction"].isin(["BUY", "SELL"]) & (prepared["volume_mwh"] > 0)
    ]
    prepared = prepared.drop_duplicates(subset=["position_id"], keep="last")
    return prepared.sort_values("delivery_time").reset_index(drop=True)

