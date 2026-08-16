"""Generate a portable Markdown management report."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd


def _money(value: float) -> str:
    return f"-EUR {abs(value):,.2f}" if value < 0 else f"EUR {value:,.2f}"


def build_markdown_report(
    portfolio_metrics: dict[str, float],
    risk_metrics: dict[str, float],
    quality_results: pd.DataFrame,
    quality_score_value: float,
    quality_status: str,
    stress_results: pd.DataFrame,
    confidence: float,
) -> str:
    """Return a concise risk report suitable for download from the app."""

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    failed_checks = quality_results[quality_results["status"].eq("FAIL")]
    worst_stress = (
        stress_results.sort_values("change_vs_base_eur").iloc[0]
        if not stress_results.empty
        else None
    )

    exception_lines = (
        "\n".join(
            f"- {row.category} / {row.check}: {row.details}"
            for row in failed_checks.itertuples()
        )
        if not failed_checks.empty
        else "- No failed controls."
    )
    worst_stress_line = (
        f"{worst_stress['scenario']} ({_money(worst_stress['change_vs_base_eur'])} versus base, "
        "full portfolio delivery horizon)"
        if worst_stress is not None
        else "Not available"
    )
    lookback = int(risk_metrics.get("var_lookback_days", 90))
    backtest_observations = int(risk_metrics.get("backtest_observations", 0))
    breach_rate = risk_metrics.get("breach_rate_pct", float("nan"))
    breach_rate_text = f"{breach_rate:.2f}%" if pd.notna(breach_rate) else "Not available"

    return f"""# Energy Market Risk Report

Generated: {generated_at}

## Executive summary

- Portfolio P&L: {_money(portfolio_metrics['portfolio_pnl_eur'])}
- Gross exposure: {_money(portfolio_metrics['gross_exposure_eur'])}
- Price coverage: {portfolio_metrics['price_coverage_pct']:.1f}%
- Historical VaR ({confidence:.0%}, 1-day): {_money(risk_metrics['historical_var_eur'])}
- Expected Shortfall ({confidence:.0%}, 1-day): {_money(risk_metrics['expected_shortfall_eur'])}
- VaR estimation window: previous {lookback} daily P&L observations
- Rolling out-of-sample backtest: {int(risk_metrics['breach_count'])} breaches across {backtest_observations} test days ({breach_rate_text})
- Data-quality status: {quality_status} ({quality_score_value:.1f}/100)
- Most adverse stress (full delivery horizon): {worst_stress_line}

## Failed controls

{exception_lines}

## Methodology and limitations

VaR and Expected Shortfall are one-day estimates calculated from the latest {lookback}
daily P&L observations. The breach statistics use a rolling out-of-sample backtest:
each day's forecast is estimated only from the preceding window before that day's P&L
is observed. Stress tests apply deterministic price shocks to every matched position
across the full portfolio delivery horizon. The one-day VaR and full-horizon stress
loss are therefore not directly comparable. The demonstration portfolio and bundled
market data are synthetic and must not be used for trading or investment decisions.
Results depend on data coverage and model assumptions.
"""
