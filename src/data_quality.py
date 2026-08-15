"""Finance-oriented data-quality and reconciliation controls."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .config import MARKET_REQUIRED_COLUMNS, PORTFOLIO_REQUIRED_COLUMNS


@dataclass(frozen=True)
class CheckResult:
    category: str
    check: str
    status: str
    failed_records: int
    details: str


def _result(
    category: str,
    check: str,
    failed_records: int,
    details: str,
    warning_only: bool = False,
) -> CheckResult:
    if failed_records == 0:
        status = "PASS"
    elif warning_only:
        status = "WARN"
    else:
        status = "FAIL"
    return CheckResult(category, check, status, int(failed_records), details)


def _missing_columns_result(
    dataset_name: str,
    columns: set[str],
    required: set[str],
) -> CheckResult:
    missing = sorted(required - columns)
    return _result(
        dataset_name,
        "Required columns",
        len(missing),
        "All required columns are present."
        if not missing
        else f"Missing columns: {', '.join(missing)}",
    )


def market_quality_checks(
    market_data: pd.DataFrame,
    expected_frequency: str = "15min",
) -> list[CheckResult]:
    """Run schema, completeness, duplication and plausibility checks."""

    results = [
        _missing_columns_result(
            "Market data", set(market_data.columns), MARKET_REQUIRED_COLUMNS
        )
    ]
    if not MARKET_REQUIRED_COLUMNS.issubset(market_data.columns):
        return results

    invalid_rows = int(
        market_data["timestamp"].isna().sum()
        + market_data["market_price_eur_mwh"].isna().sum()
    )
    results.append(
        _result(
            "Market data",
            "Valid timestamps and prices",
            invalid_rows,
            f"Found {invalid_rows} missing or invalid timestamp/price values.",
        )
    )

    duplicate_count = int(
        (
            market_data["timestamp"].notna()
            & market_data["timestamp"].duplicated(keep=False)
        ).sum()
    )
    results.append(
        _result(
            "Market data",
            "Unique timestamps",
            duplicate_count,
            f"Found {duplicate_count} rows belonging to duplicate timestamps.",
        )
    )

    valid_timestamps = market_data["timestamp"].dropna().drop_duplicates().sort_values()
    missing_intervals = 0
    if len(valid_timestamps) > 1:
        expected = pd.date_range(
            valid_timestamps.iloc[0],
            valid_timestamps.iloc[-1],
            freq=expected_frequency,
            tz="UTC",
        )
        missing_intervals = int(len(expected.difference(pd.DatetimeIndex(valid_timestamps))))
    results.append(
        _result(
            "Market data",
            f"Complete {expected_frequency} time series",
            missing_intervals,
            f"Found {missing_intervals} missing delivery intervals.",
        )
    )

    price_series = market_data.sort_values("timestamp")["market_price_eur_mwh"]
    extreme_prices = int((price_series.abs() > 1_000).sum())
    results.append(
        _result(
            "Market data",
            "Price plausibility",
            extreme_prices,
            f"Found {extreme_prices} prices outside +/-1,000 EUR/MWh.",
            warning_only=True,
        )
    )

    jumps = price_series.diff().abs()
    unusual_jumps = int((jumps > 250).sum())
    results.append(
        _result(
            "Market data",
            "Interval price-change monitoring",
            unusual_jumps,
            f"Found {unusual_jumps} interval changes above 250 EUR/MWh.",
            warning_only=True,
        )
    )
    return results


def portfolio_quality_checks(portfolio: pd.DataFrame) -> list[CheckResult]:
    """Run schema, domain and economic-value checks on positions."""

    results = [
        _missing_columns_result(
            "Portfolio", set(portfolio.columns), PORTFOLIO_REQUIRED_COLUMNS
        )
    ]
    if not PORTFOLIO_REQUIRED_COLUMNS.issubset(portfolio.columns):
        return results

    missing_values = int(portfolio[list(PORTFOLIO_REQUIRED_COLUMNS)].isna().sum().sum())
    results.append(
        _result(
            "Portfolio",
            "Complete required values",
            missing_values,
            f"Found {missing_values} missing required values.",
        )
    )

    duplicate_ids = int(portfolio["position_id"].duplicated(keep=False).sum())
    results.append(
        _result(
            "Portfolio",
            "Unique position identifiers",
            duplicate_ids,
            f"Found {duplicate_ids} rows belonging to duplicate position IDs.",
        )
    )

    invalid_directions = int((~portfolio["direction"].isin(["BUY", "SELL"])).sum())
    results.append(
        _result(
            "Portfolio",
            "Valid trade direction",
            invalid_directions,
            f"Found {invalid_directions} positions outside BUY/SELL.",
        )
    )

    invalid_volumes = int(
        (portfolio["volume_mwh"].isna() | (portfolio["volume_mwh"] <= 0)).sum()
    )
    results.append(
        _result(
            "Portfolio",
            "Positive position volume",
            invalid_volumes,
            f"Found {invalid_volumes} missing, zero or negative volumes.",
        )
    )
    return results


def reconciliation_checks(
    portfolio: pd.DataFrame,
    market_data: pd.DataFrame,
) -> list[CheckResult]:
    """Identify positions that do not have exactly matching market timestamps."""

    if "delivery_time" not in portfolio or "timestamp" not in market_data:
        return []
    market_times = set(market_data["timestamp"].dropna())
    unmatched = int((~portfolio["delivery_time"].isin(market_times)).sum())
    return [
        _result(
            "Reconciliation",
            "Positions matched to market prices",
            unmatched,
            f"Found {unmatched} positions without a matching market-price timestamp.",
        )
    ]


def run_data_quality_checks(
    market_data: pd.DataFrame,
    portfolio: pd.DataFrame,
    expected_frequency: str = "15min",
) -> pd.DataFrame:
    """Run all controls and return one management-friendly result table."""

    checks = market_quality_checks(market_data, expected_frequency)
    checks.extend(portfolio_quality_checks(portfolio))
    checks.extend(reconciliation_checks(portfolio, market_data))
    return pd.DataFrame([asdict(check) for check in checks])


def quality_score(check_results: pd.DataFrame) -> float:
    """Return a transparent 0-100 score: PASS=1, WARN=0.5, FAIL=0."""

    if check_results.empty:
        return 0.0
    weights = check_results["status"].map({"PASS": 1.0, "WARN": 0.5, "FAIL": 0.0})
    return float(np.round(100 * weights.fillna(0).mean(), 1))


def overall_quality_status(check_results: pd.DataFrame) -> str:
    """Return FAIL, WARN or PASS using the most severe individual result."""

    statuses = set(check_results.get("status", pd.Series(dtype=str)))
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"
